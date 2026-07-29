"""Flask web UI for the `starter_v0` research agent.

Serves an OpenClaw-style chat interface that exposes the *whole* ReAct chain
for every turn: streamed assistant thoughts, each tool call with its params,
each tool response, per-step latency, and a running in/out token counter for
the session.

The agent loop mirrors `starter_v0/chat.py` (same message conventions, same
clarification/pause semantics, same transcript format) so the web UI and the
CLI produce comparable runs. The only difference is that this module streams
the model call instead of waiting for the full completion.

Run:
    python main.py --provider openrouter --version v0
    python main.py --provider openrouter --model openai/gpt-4o-mini --port 8000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterator

ROOT = Path(__file__).resolve().parent
STARTER = ROOT / "starter_v0"
if str(STARTER) not in sys.path:
    sys.path.insert(0, str(STARTER))

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

# Reuse the lab's own building blocks so the web UI stays in sync with the CLI.
from chat import (  # noqa: E402  (path juggling above is intentional)
    assistant_tool_message,
    execute_tool_call,
    now_iso,
    safe_slug,
    tool_results_message,
    trim_history,
    write_transcript,
)
from env_loader import load_lab_env  # noqa: E402
from providers import make_provider  # noqa: E402
from providers.base import ToolCall  # noqa: E402
from tools import load_tool_declarations, to_openai_tools  # noqa: E402
from versioning import artifact_version_dict, build_artifact_version  # noqa: E402

load_lab_env(STARTER)

ARTIFACTS_DIR = STARTER / "artifacts"
TRANSCRIPTS_DIR = STARTER / "transcripts"

app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static"))

# Filled in by main(); defaults let `flask run`/`python main.py` work with no args.
APP_CONFIG: dict[str, Any] = {
    "provider": "openrouter",
    "model": None,
    "version": "web",
    "system_prompt_path": ARTIFACTS_DIR / "system_prompt.md",
    "tools_path": ARTIFACTS_DIR / "tools.yaml",
    "transcripts_dir": TRANSCRIPTS_DIR,
    "max_tool_rounds": 4,
    "history_window": 5,
    "temperature": 0.0,
    "stream_delay_ms": 0,
}

SESSIONS: dict[str, dict[str, Any]] = {}
SESSIONS_LOCK = threading.Lock()


# --------------------------------------------------------------------------- #
# Token accounting
# --------------------------------------------------------------------------- #

def estimate_tokens(text: str | None) -> int:
    """Cheap fallback when the provider does not return a usage block."""
    if not text:
        return 0
    return max(1, round(len(text) / 4))


def usage_from_response(usage: Any, messages: list[dict[str, str]], output_text: str) -> dict[str, Any]:
    """Normalize a provider usage object; fall back to a ~4 chars/token guess."""
    if usage is not None:
        prompt = getattr(usage, "prompt_tokens", None)
        completion = getattr(usage, "completion_tokens", None)
        if prompt is None and isinstance(usage, dict):
            prompt = usage.get("prompt_tokens")
            completion = usage.get("completion_tokens")
        if prompt is not None or completion is not None:
            return {
                "input": int(prompt or 0),
                "output": int(completion or 0),
                "estimated": False,
            }
    prompt_text = "\n".join(str(m.get("content", "")) for m in messages)
    return {
        "input": estimate_tokens(prompt_text),
        "output": estimate_tokens(output_text),
        "estimated": True,
    }


# --------------------------------------------------------------------------- #
# Streaming model calls
# --------------------------------------------------------------------------- #

def _openai_client(provider: Any):
    from openai import OpenAI

    api_key = os.getenv(provider.api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing API key env var: {provider.api_key_env}")
    return OpenAI(api_key=api_key, base_url=provider.base_url)


def _supports_streaming(provider: Any) -> bool:
    """OpenAI-compatible providers (openai, openrouter) expose these attrs."""
    return hasattr(provider, "api_key_env") and hasattr(provider, "base_url")


def _finish_tool_calls(fragments: dict[int, dict[str, str]]) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for _, frag in sorted(fragments.items()):
        name = frag.get("name") or ""
        if not name:
            continue
        raw_args = frag.get("args") or "{}"
        try:
            args = json.loads(raw_args or "{}")
        except json.JSONDecodeError:
            args = {"_unparsed_arguments": raw_args}
        if not isinstance(args, dict):
            args = {"value": args}
        calls.append(ToolCall(name=name, args=args))
    return calls


def stream_model_call(
    *,
    provider: Any,
    messages: list[dict[str, str]],
    tools: list[dict[str, Any]],
    model: str | None,
    temperature: float,
    round_index: int,
    stream_delay_ms: int,
) -> Iterator[dict[str, Any]]:
    """Run one model call, yielding SSE-ready delta events.

    Returns (via StopIteration.value / `yield from`) a dict with the assembled
    text, tool calls, usage and timing for the round.
    """
    started = time.perf_counter()
    first_token_at: float | None = None
    text_parts: list[str] = []
    reasoning_parts: list[str] = []
    usage_obj: Any = None
    fragments: dict[int, dict[str, str]] = {}
    calls: list[ToolCall] = []

    def pace() -> None:
        if stream_delay_ms > 0:
            time.sleep(stream_delay_ms / 1000.0)

    if _supports_streaming(provider):
        client = _openai_client(provider)
        kwargs: dict[str, Any] = {
            "model": model or provider.default_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        try:
            stream = client.chat.completions.create(**kwargs, stream_options={"include_usage": True})
        except Exception:
            # Some OpenAI-compatible gateways reject `stream_options`.
            stream = client.chat.completions.create(**kwargs)

        for chunk in stream:
            chunk_usage = getattr(chunk, "usage", None)
            if chunk_usage is not None:
                usage_obj = chunk_usage
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue

            reasoning = getattr(delta, "reasoning", None) or getattr(delta, "reasoning_content", None)
            if reasoning:
                if first_token_at is None:
                    first_token_at = time.perf_counter()
                reasoning_parts.append(reasoning)
                yield {"type": "reasoning_delta", "round": round_index, "text": reasoning}
                pace()

            content = getattr(delta, "content", None)
            if content:
                if first_token_at is None:
                    first_token_at = time.perf_counter()
                text_parts.append(content)
                yield {"type": "text_delta", "round": round_index, "text": content}
                pace()

            for tool_delta in getattr(delta, "tool_calls", None) or []:
                if first_token_at is None:
                    first_token_at = time.perf_counter()
                index = getattr(tool_delta, "index", None)
                if index is None:
                    index = len(fragments)
                slot = fragments.setdefault(index, {"name": "", "args": ""})
                func = getattr(tool_delta, "function", None)
                if func is not None:
                    if getattr(func, "name", None):
                        slot["name"] = func.name
                    if getattr(func, "arguments", None):
                        slot["args"] += func.arguments
                        yield {
                            "type": "tool_call_delta",
                            "round": round_index,
                            "index": index,
                            "name": slot["name"],
                            "args_fragment": func.arguments,
                        }
        calls = _finish_tool_calls(fragments)
    else:
        # anthropic / gemini providers in this lab are request/response only.
        response = provider.complete(messages, tools, model=model, temperature=temperature)
        calls = list(response.tool_calls)
        usage_obj = getattr(getattr(response, "raw", None), "usage", None)
        body = response.text or ""
        for i in range(0, len(body), 24):
            if first_token_at is None:
                first_token_at = time.perf_counter()
            piece = body[i:i + 24]
            text_parts.append(piece)
            yield {"type": "text_delta", "round": round_index, "text": piece}
            time.sleep(max(stream_delay_ms, 12) / 1000.0)

    text = "".join(text_parts)
    ended = time.perf_counter()
    usage = usage_from_response(usage_obj, messages, text + "".join(reasoning_parts))
    return {
        "text": text,
        "reasoning": "".join(reasoning_parts),
        "tool_calls": calls,
        "usage": usage,
        "latency_ms": round((ended - started) * 1000),
        "ttft_ms": round(((first_token_at or ended) - started) * 1000),
    }


# --------------------------------------------------------------------------- #
# Session management
# --------------------------------------------------------------------------- #

def create_session(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    overrides = overrides or {}
    config = {
        "provider": overrides.get("provider") or APP_CONFIG["provider"],
        "model": overrides.get("model") or APP_CONFIG["model"],
        "version": overrides.get("version") or APP_CONFIG["version"],
        "max_tool_rounds": int(overrides.get("max_tool_rounds") or APP_CONFIG["max_tool_rounds"]),
        "history_window": int(overrides.get("history_window") or APP_CONFIG["history_window"]),
        "temperature": float(overrides.get("temperature", APP_CONFIG["temperature"])),
        "stream_delay_ms": int(overrides.get("stream_delay_ms", APP_CONFIG["stream_delay_ms"])),
    }

    system_prompt_path: Path = APP_CONFIG["system_prompt_path"]
    tools_path: Path = APP_CONFIG["tools_path"]
    system_prompt = system_prompt_path.read_text(encoding="utf-8")
    declarations = load_tool_declarations(tools_path)
    openai_tools = to_openai_tools(declarations)

    provider = make_provider(config["provider"])
    config["model"] = config["model"] or getattr(provider, "default_model", None)
    artifact_version = build_artifact_version(config["version"], system_prompt_path, tools_path)

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([safe_slug(config["version"]), safe_slug(config["provider"]), "web", timestamp])
    transcript_path = Path(APP_CONFIG["transcripts_dir"]) / f"{transcript_id}.transcript.json"

    session_id = uuid.uuid4().hex[:16]
    session = {
        "id": session_id,
        "config": config,
        "provider": provider,
        "system_prompt": system_prompt,
        "declarations": declarations,
        "openai_tools": openai_tools,
        "artifact_version": artifact_version,
        "history": [],
        "turns": 0,
        "tool_calls": 0,
        "tokens": {"input": 0, "output": 0, "estimated": False},
        "latency_ms_total": 0,
        "transcript_path": transcript_path,
        "transcript": {
            "transcript_id": transcript_id,
            **artifact_version_dict(artifact_version),
            "interface": "flask_web",
            "provider": config["provider"],
            "model": config["model"],
            "system_prompt": str(system_prompt_path),
            "tools": str(tools_path),
            "history_window": config["history_window"],
            "max_tool_rounds": config["max_tool_rounds"],
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "turns": [],
        },
        "lock": threading.Lock(),
    }
    with SESSIONS_LOCK:
        SESSIONS[session_id] = session
    return session


def session_public(session: dict[str, Any]) -> dict[str, Any]:
    tokens = session["tokens"]
    turns = session["turns"]
    return {
        "session_id": session["id"],
        "provider": session["config"]["provider"],
        "model": session["config"]["model"],
        "artifact_version": session["artifact_version"].artifact_version,
        "version": session["config"]["version"],
        "max_tool_rounds": session["config"]["max_tool_rounds"],
        "history_window": session["config"]["history_window"],
        "stream_delay_ms": session["config"]["stream_delay_ms"],
        "tools": [
            {"name": d.get("name"), "description": d.get("description", "")}
            for d in session["declarations"]
        ],
        "stats": {
            "turns": turns,
            "tool_calls": session["tool_calls"],
            "tokens_in": tokens["input"],
            "tokens_out": tokens["output"],
            "tokens_total": tokens["input"] + tokens["output"],
            "tokens_estimated": tokens["estimated"],
            "latency_ms_total": session["latency_ms_total"],
            "latency_ms_avg": round(session["latency_ms_total"] / turns) if turns else 0,
        },
        "transcript_path": str(session["transcript_path"]),
    }


def get_session(session_id: str | None) -> dict[str, Any] | None:
    if not session_id:
        return None
    with SESSIONS_LOCK:
        return SESSIONS.get(session_id)


# --------------------------------------------------------------------------- #
# The ReAct turn — same loop as chat.run_model_tool_loop, but streamed
# --------------------------------------------------------------------------- #

def run_turn(session: dict[str, Any], user_text: str) -> Iterator[dict[str, Any]]:
    config = session["config"]
    provider = session["provider"]
    max_rounds = config["max_tool_rounds"]

    working_messages: list[dict[str, str]] = [
        {"role": "system", "content": session["system_prompt"]},
        *trim_history(session["history"], config["history_window"]),
        {"role": "user", "content": user_text},
    ]

    turn_index = session["turns"] + 1
    turn_started = time.perf_counter()
    turn_tokens = {"input": 0, "output": 0, "estimated": False}
    rounds_record: list[dict[str, Any]] = []
    all_tool_events: list[dict[str, Any]] = []

    turn_record: dict[str, Any] = {
        "turn_index": turn_index,
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": rounds_record,
        "tool_events": all_tool_events,
    }

    yield {"type": "turn_start", "turn": turn_index, "max_tool_rounds": max_rounds}

    status = "max_tool_rounds"
    assistant_text = f"Stopped after {max_rounds} tool rounds. Inspect the trace above for details."

    for round_index in range(1, max_rounds + 1):
        yield {"type": "round_start", "round": round_index, "turn": turn_index}

        result = yield from stream_model_call(
            provider=provider,
            messages=working_messages,
            tools=session["openai_tools"],
            model=config["model"],
            temperature=config["temperature"],
            round_index=round_index,
            stream_delay_ms=config["stream_delay_ms"],
        )

        calls: list[ToolCall] = result["tool_calls"]
        usage = result["usage"]
        turn_tokens["input"] += usage["input"]
        turn_tokens["output"] += usage["output"]
        turn_tokens["estimated"] = turn_tokens["estimated"] or usage["estimated"]

        round_record: dict[str, Any] = {
            "round": round_index,
            "assistant_text": result["text"],
            "reasoning": result["reasoning"] or None,
            "latency_ms": result["latency_ms"],
            "ttft_ms": result["ttft_ms"],
            "usage": usage,
            "tool_calls": [{"name": c.name, "args": c.args} for c in calls],
            "tool_results": [],
        }
        rounds_record.append(round_record)

        yield {
            "type": "round_end",
            "round": round_index,
            "turn": turn_index,
            "has_tool_calls": bool(calls),
            "latency_ms": result["latency_ms"],
            "ttft_ms": result["ttft_ms"],
            "usage": usage,
        }

        if not calls:
            status = "answered"
            assistant_text = result["text"] or ""
            break

        working_messages.append(assistant_tool_message(result["text"], calls))
        non_clarification_events: list[dict[str, Any]] = []
        paused = False

        for position, call in enumerate(calls):
            call_id = f"t{turn_index}-r{round_index}-c{position}"
            yield {
                "type": "tool_call",
                "id": call_id,
                "round": round_index,
                "turn": turn_index,
                "name": call.name,
                "args": call.args,
            }

            tool_started = time.perf_counter()
            event = execute_tool_call(call)
            tool_latency = round((time.perf_counter() - tool_started) * 1000)

            tool_result = event.get("result")
            ok = not (isinstance(tool_result, dict) and tool_result.get("error"))
            event["latency_ms"] = tool_latency
            round_record["tool_results"].append(event)
            all_tool_events.append(event)
            session["tool_calls"] += 1

            yield {
                "type": "tool_result",
                "id": call_id,
                "round": round_index,
                "turn": turn_index,
                "name": call.name,
                "ok": ok,
                "result": tool_result,
                "latency_ms": tool_latency,
            }

            # The clarification/pause tool is detected by its output flag
            # (rename-proof), exactly like starter_v0/chat.py does.
            if isinstance(tool_result, dict) and tool_result.get("awaiting_user"):
                status = "waiting_for_user"
                assistant_text = (
                    tool_result.get("question")
                    or call.args.get("question")
                    or "Bạn bổ sung thêm thông tin nhé."
                )
                paused = True
                break

            non_clarification_events.append(event)

        if paused:
            break

        working_messages.append(tool_results_message(non_clarification_events))

    turn_latency = round((time.perf_counter() - turn_started) * 1000)

    session["history"].append({"role": "user", "content": user_text})
    session["history"].append({"role": "assistant", "content": assistant_text})
    session["turns"] = turn_index
    session["tokens"]["input"] += turn_tokens["input"]
    session["tokens"]["output"] += turn_tokens["output"]
    session["tokens"]["estimated"] = session["tokens"]["estimated"] or turn_tokens["estimated"]
    session["latency_ms_total"] += turn_latency

    turn_record.update({
        "status": status,
        "assistant_text": assistant_text,
        "latency_ms": turn_latency,
        "usage": turn_tokens,
        "ended_at": now_iso(),
    })
    session["transcript"]["turns"].append(turn_record)
    write_transcript(session["transcript_path"], session["transcript"])

    yield {
        "type": "final",
        "turn": turn_index,
        "status": status,
        "text": assistant_text,
        "latency_ms": turn_latency,
        "usage": turn_tokens,
        "rounds": len(rounds_record),
        "session": session_public(session),
    }


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

def sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.get("/api/defaults")
def api_defaults() -> Any:
    return jsonify({
        "provider": APP_CONFIG["provider"],
        "model": APP_CONFIG["model"],
        "version": APP_CONFIG["version"],
        "max_tool_rounds": APP_CONFIG["max_tool_rounds"],
        "history_window": APP_CONFIG["history_window"],
        "stream_delay_ms": APP_CONFIG["stream_delay_ms"],
        "providers": ["openrouter", "openai", "anthropic", "gemini"],
    })


@app.post("/api/session")
def api_create_session() -> Any:
    payload = request.get_json(silent=True) or {}
    try:
        session = create_session(payload)
    except Exception as exc:
        return jsonify({"error": f"{type(exc).__name__}: {exc}"}), 400
    return jsonify(session_public(session))


@app.get("/api/session/<session_id>")
def api_get_session(session_id: str) -> Any:
    session = get_session(session_id)
    if session is None:
        return jsonify({"error": "unknown_session"}), 404
    return jsonify(session_public(session))


@app.post("/api/session/<session_id>/reset")
def api_reset_session(session_id: str) -> Any:
    session = get_session(session_id)
    if session is None:
        return jsonify({"error": "unknown_session"}), 404
    with SESSIONS_LOCK:
        SESSIONS.pop(session_id, None)
    fresh = create_session(session["config"])
    return jsonify(session_public(fresh))


@app.post("/api/chat")
def api_chat() -> Any:
    payload = request.get_json(silent=True) or {}
    session = get_session(payload.get("session_id"))
    message = (payload.get("message") or "").strip()

    if session is None:
        return jsonify({"error": "unknown_session"}), 404
    if not message:
        return jsonify({"error": "empty_message"}), 400

    def generate() -> Iterator[str]:
        # One turn at a time per session keeps history/transcript consistent.
        if not session["lock"].acquire(blocking=False):
            yield sse({"type": "error", "message": "This session is already generating a reply."})
            return
        try:
            for event in run_turn(session, message):
                yield sse(event)
        except Exception as exc:
            yield sse({
                "type": "error",
                "message": f"{type(exc).__name__}: {exc}",
                "session": session_public(session),
            })
        finally:
            session["lock"].release()

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(description="Flask web chat UI for the starter_v0 research agent.")
    parser.add_argument("--provider", choices=["openrouter", "openai", "anthropic", "gemini"], default="openrouter")
    parser.add_argument("--model", default=None)
    parser.add_argument("--version", default="web", help="Artifact version label, e.g. v0, v1, v2.")
    parser.add_argument("--system-prompt", type=Path, default=ARTIFACTS_DIR / "system_prompt.md")
    parser.add_argument("--tools", type=Path, default=ARTIFACTS_DIR / "tools.yaml")
    parser.add_argument("--transcripts-dir", type=Path, default=TRANSCRIPTS_DIR)
    parser.add_argument("--history-window", type=int, default=5)
    parser.add_argument("--max-tool-rounds", type=int, default=4)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--stream-delay-ms", type=int, default=0,
                        help="Artificial per-chunk typing delay for demos (0 = provider speed).")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    APP_CONFIG.update({
        "provider": args.provider,
        "model": args.model,
        "version": args.version,
        "system_prompt_path": args.system_prompt,
        "tools_path": args.tools,
        "transcripts_dir": args.transcripts_dir,
        "max_tool_rounds": args.max_tool_rounds,
        "history_window": args.history_window,
        "temperature": args.temperature,
        "stream_delay_ms": args.stream_delay_ms,
    })

    print(f"Research Agent web UI  ->  http://{args.host}:{args.port}")
    print(f"provider={args.provider} model={args.model or 'provider default'} version={args.version}")
    print(f"transcripts -> {args.transcripts_dir}")
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)


if __name__ == "__main__":
    main()
