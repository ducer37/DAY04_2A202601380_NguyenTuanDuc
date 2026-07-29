from __future__ import annotations

import csv
import json
import mimetypes
import sys
import time
import traceback
from dataclasses import asdict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
STARTER_DIR = ROOT / "starter_v0"
TRANSCRIPTS_DIR = APP_DIR / "transcripts"

sys.path.insert(0, str(STARTER_DIR))

from env_loader import load_lab_env  # noqa: E402
from providers import make_provider  # noqa: E402
from providers.base import ToolCall  # noqa: E402
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools  # noqa: E402
from versioning import artifact_version_dict, build_artifact_version  # noqa: E402


load_lab_env(STARTER_DIR)

SYSTEM_PROMPT_PATH = STARTER_DIR / "artifacts" / "system_prompt.md"
TOOLS_PATH = STARTER_DIR / "artifacts" / "tools.yaml"
VERSION_LOG_PATH = STARTER_DIR / "artifacts" / "version_log.csv"
RUNS_DIR = STARTER_DIR / "runs"
GROUP_EVAL_PATH = STARTER_DIR / "data" / "eval_group.json"

MODEL_PRICES_PER_1M: dict[str, tuple[float, float]] = {
    "gpt-5-nano": (0.05, 0.40),
    "gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4o-mini": (0.15, 0.60),
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def json_safe(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False, default=str)
        return value
    except Exception:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def sse_event(event: str, data: Any) -> bytes:
    payload = json.dumps(json_safe(data), ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


def extract_usage(raw: Any) -> dict[str, int]:
    usage = getattr(raw, "usage", None)
    if usage is None and isinstance(raw, dict):
        usage = raw.get("usage")
    if usage is None:
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    def get(name: str, alt: str | None = None) -> int:
        if isinstance(usage, dict):
            return int(usage.get(name) or (usage.get(alt) if alt else 0) or 0)
        return int(getattr(usage, name, None) or (getattr(usage, alt, None) if alt else 0) or 0)

    input_tokens = get("prompt_tokens", "input_tokens")
    output_tokens = get("completion_tokens", "output_tokens")
    total_tokens = get("total_tokens") or input_tokens + output_tokens
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def estimate_cost(model: str | None, usage: dict[str, int]) -> float:
    if not model:
        return 0.0
    in_price, out_price = MODEL_PRICES_PER_1M.get(model, (0.0, 0.0))
    return (usage["input_tokens"] * in_price + usage["output_tokens"] * out_price) / 1_000_000


def run_summaries() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not RUNS_DIR.exists():
        return rows
    for path in sorted(RUNS_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime):
        data = read_json(path, {})
        summary = data.get("summary") or {}
        rows.append({
            "file": str(path.relative_to(STARTER_DIR)).replace("\\", "/"),
            "name": path.name,
            "version": data.get("version"),
            "suite": data.get("suite"),
            "provider": data.get("provider"),
            "model": data.get("model"),
            "artifact_version": data.get("artifact_version"),
            "generated_at": data.get("generated_at"),
            "case_accuracy": summary.get("case_accuracy"),
            "routing_accuracy": summary.get("tool_routing_accuracy"),
            "argument_accuracy": summary.get("argument_accuracy"),
            "multiturn_accuracy": summary.get("multiturn_accuracy"),
            "passed_cases": summary.get("passed_cases"),
            "total_cases": summary.get("total_cases"),
            "provider_error_cases": summary.get("provider_error_cases"),
        })
    return rows


def version_log_rows() -> list[dict[str, Any]]:
    if not VERSION_LOG_PATH.exists():
        return []
    with VERSION_LOG_PATH.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def tool_docs() -> list[dict[str, Any]]:
    declarations = load_tool_declarations(TOOLS_PATH)
    implemented = set(TOOL_FUNCTIONS)
    return [
        {
            "name": item["name"],
            "description": item.get("description", ""),
            "implemented": item["name"] in implemented,
            "required": item.get("parameters", {}).get("required", []),
        }
        for item in declarations
    ]


def group_cases() -> list[dict[str, Any]]:
    data = read_json(GROUP_EVAL_PATH, {"cases": []})
    cases = data.get("cases") or []
    return [
        {
            "id": case.get("id"),
            "type": "multi" if "turns" in case else "single",
            "failure_type": case.get("failure_type"),
            "what_it_tests": (case.get("metadata") or {}).get("what_it_tests", ""),
            "expect": case.get("expect"),
        }
        for case in cases
    ]


def execute_tool_call(call: ToolCall) -> dict[str, Any]:
    func = TOOL_FUNCTIONS.get(call.name)
    if not func:
        return {"tool": call.name, "args": call.args, "result": {"error": "unknown_tool"}}
    started = time.perf_counter()
    try:
        result = func(**call.args)
    except Exception as exc:
        result = {"error": type(exc).__name__, "message": str(exc)}
    return {
        "tool": call.name,
        "args": call.args,
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        "result": result,
    }


def tool_results_message(events: list[dict[str, Any]]) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            "TOOL_RESULTS_JSON:\n"
            f"{json.dumps(events, ensure_ascii=False, indent=2, default=str)[:24000]}\n\n"
            "Use only these tool results. Answer directly with citations when available."
        ),
    }


def assistant_tool_message(response_text: str | None, calls: list[ToolCall]) -> dict[str, str]:
    return {
        "role": "assistant",
        "content": (
            (response_text or "I will call the selected tool(s).")
            + "\n\nTOOL_CALLS_JSON:\n"
            + json.dumps([{"name": call.name, "args": call.args} for call in calls], ensure_ascii=False)
        ),
    }


def complete_with_fallback(
    *,
    provider_name: str,
    fallback_provider_name: str,
    model: str | None,
    messages: list[dict[str, str]],
    tools: list[dict[str, Any]],
    emit,
) -> tuple[Any, str, str | None, dict[str, Any]]:
    attempts = [provider_name]
    if fallback_provider_name and fallback_provider_name not in attempts:
        attempts.append(fallback_provider_name)

    last_error: str | None = None
    for attempt_provider in attempts:
        provider = make_provider(attempt_provider)
        selected_model = model or getattr(provider, "default_model", None)
        emit("provider_attempt", {"provider": attempt_provider, "model": selected_model})
        started = time.perf_counter()
        try:
            response = provider.complete(messages, tools, model=model, temperature=0.0)
            latency_ms = round((time.perf_counter() - started) * 1000, 1)
            usage = extract_usage(response.raw)
            cost = estimate_cost(selected_model, usage)
            metrics = {
                "provider": attempt_provider,
                "model": selected_model,
                "latency_ms": latency_ms,
                "usage": usage,
                "cost_usd": cost,
            }
            emit("provider_success", metrics)
            return response, attempt_provider, selected_model, metrics
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            emit("provider_error", {
                "provider": attempt_provider,
                "model": selected_model,
                "error": last_error,
            })
    raise RuntimeError(last_error or "All providers failed")


def run_chat(payload: dict[str, Any], emit) -> dict[str, Any]:
    provider_name = payload.get("provider") or "openai"
    fallback_provider_name = payload.get("fallback_provider") or "openrouter"
    model = payload.get("model") or None
    version = payload.get("version") or "demo"
    max_tool_rounds = int(payload.get("max_tool_rounds") or 4)
    history = payload.get("history") or []
    user_text = str(payload.get("message") or "").strip()

    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    declarations = load_tool_declarations(TOOLS_PATH)
    openai_tools = to_openai_tools(declarations)
    artifact = build_artifact_version(version, SYSTEM_PROMPT_PATH, TOOLS_PATH)

    working_messages = [
        {"role": "system", "content": system_prompt},
        *history[-10:],
        {"role": "user", "content": user_text},
    ]
    rounds: list[dict[str, Any]] = []
    tool_events: list[dict[str, Any]] = []
    model_metrics: list[dict[str, Any]] = []

    emit("meta", {
        **artifact_version_dict(artifact),
        "started_at": now_iso(),
        "primary_provider": provider_name,
        "fallback_provider": fallback_provider_name,
    })

    final_text = ""
    status = "started"
    active_provider = provider_name
    active_model = model

    for round_index in range(1, max_tool_rounds + 1):
        emit("round_start", {"round": round_index})
        response, active_provider, active_model, metrics = complete_with_fallback(
            provider_name=active_provider,
            fallback_provider_name=fallback_provider_name,
            model=model,
            messages=working_messages,
            tools=openai_tools,
            emit=emit,
        )
        model_metrics.append(metrics)
        calls = response.tool_calls
        round_record = {
            "round": round_index,
            "assistant_text": response.text,
            "tool_calls": [{"name": call.name, "args": call.args} for call in calls],
            "tool_results": [],
            "model_metrics": metrics,
        }

        if not calls:
            status = "answered"
            final_text = response.text or ""
            rounds.append(round_record)
            break

        working_messages.append(assistant_tool_message(response.text, calls))
        non_clarification_events: list[dict[str, Any]] = []
        for call in calls:
            emit("tool_call", {"round": round_index, "name": call.name, "args": call.args})
            event = execute_tool_call(call)
            round_record["tool_results"].append(event)
            tool_events.append(event)
            emit("tool_result", event)
            result = event.get("result", {})
            if isinstance(result, dict) and result.get("awaiting_user"):
                final_text = result.get("question") or call.args.get("question") or "Bạn bổ sung thêm thông tin nhé."
                status = "waiting_for_user"
                rounds.append(round_record)
                break
            non_clarification_events.append(event)
        else:
            rounds.append(round_record)
            working_messages.append(tool_results_message(non_clarification_events))
            continue
        break

    if not final_text and status == "started":
        status = "max_tool_rounds"
        final_text = f"Stopped after {max_tool_rounds} tool rounds."

    for chunk in chunk_text(final_text):
        emit("answer_chunk", {"text": chunk})
        time.sleep(0.012)

    totals = {
        "input_tokens": sum(item["usage"]["input_tokens"] for item in model_metrics),
        "output_tokens": sum(item["usage"]["output_tokens"] for item in model_metrics),
        "total_tokens": sum(item["usage"]["total_tokens"] for item in model_metrics),
        "cost_usd": sum(item["cost_usd"] for item in model_metrics),
        "latency_ms": sum(item["latency_ms"] for item in model_metrics),
    }

    transcript = {
        "transcript_id": f"{version}_{active_provider}_{datetime.now().strftime('%Y%m%dT%H%M%S%f')}",
        **artifact_version_dict(artifact),
        "provider": active_provider,
        "model": active_model,
        "status": status,
        "user": user_text,
        "assistant_text": final_text,
        "rounds": rounds,
        "tool_events": tool_events,
        "model_metrics": model_metrics,
        "totals": totals,
        "created_at": now_iso(),
    }
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    transcript_path = TRANSCRIPTS_DIR / f"{transcript['transcript_id']}.transcript.json"
    transcript_path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    transcript["transcript_path"] = str(transcript_path.relative_to(ROOT)).replace("\\", "/")
    emit("done", {"status": status, "totals": totals, "transcript_path": transcript["transcript_path"]})
    return transcript


def chunk_text(text: str, size: int = 10) -> list[str]:
    if not text:
        return [""]
    chunks: list[str] = []
    cursor = 0
    while cursor < len(text):
        chunks.append(text[cursor:cursor + size])
        cursor += size
    return chunks


class Handler(BaseHTTPRequestHandler):
    server_version = "LabDashboard/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/meta":
            return self.send_json(self.meta_payload())
        if parsed.path == "/api/transcripts":
            return self.send_json(self.transcript_rows())
        if parsed.path in {"/", "/index.html"}:
            return self.send_file(STATIC_DIR / "index.html")
        target = (STATIC_DIR / parsed.path.lstrip("/")).resolve()
        if STATIC_DIR in target.parents and target.exists():
            return self.send_file(target)
        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/chat":
            return self.handle_chat()
        self.send_error(404)

    def meta_payload(self) -> dict[str, Any]:
        current = build_artifact_version("current", SYSTEM_PROMPT_PATH, TOOLS_PATH)
        runs = run_summaries()
        best = max(
            runs,
            key=lambda item: (
                item.get("case_accuracy") or -1,
                item.get("passed_cases") or -1,
                item.get("generated_at") or "",
            ),
            default=None,
        )
        return {
            "artifact": artifact_version_dict(current),
            "version_log": version_log_rows(),
            "runs": runs,
            "best_run": best,
            "tools": tool_docs(),
            "group_cases": group_cases(),
        }

    def transcript_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for path in sorted(TRANSCRIPTS_DIR.glob("*.transcript.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            data = read_json(path, {})
            rows.append({
                "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "status": data.get("status"),
                "provider": data.get("provider"),
                "model": data.get("model"),
                "created_at": data.get("created_at"),
                "total_tokens": (data.get("totals") or {}).get("total_tokens"),
                "cost_usd": (data.get("totals") or {}).get("cost_usd"),
                "user": data.get("user"),
            })
        return rows[:20]

    def handle_chat(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        def emit(event: str, data: Any) -> None:
            self.wfile.write(sse_event(event, data))
            self.wfile.flush()

        try:
            run_chat(payload, emit)
        except Exception as exc:
            emit("fatal_error", {"error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc(limit=3)})

    def send_json(self, payload: Any) -> None:
        body = json.dumps(json_safe(payload), ensure_ascii=False, indent=2, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path) -> None:
        body = path.read_bytes()
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{now_iso()}] {fmt % args}")


def main() -> None:
    query = parse_qs(urlparse("?" + "port=8765").query)
    port = int(query.get("port", ["8765"])[0])
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Lab dashboard running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

