from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, domain, err


def web_search(query: str = "", topic: str = "general", timeframe: str | None = "week", max_results: int = 5) -> dict[str, Any]:
    try:
        key = os.getenv("TAVILY_API_KEY")
        if not key:
            raise RuntimeError("Missing TAVILY_API_KEY env var")

        clean_query = query.strip()
        valid_timeframes = {"day", "week", "month", "year"}
        tf = timeframe if timeframe in valid_timeframes else "week"
        
        body: dict[str, Any] = {
            "query": clean_query,
            "topic": topic if topic in {"general", "news"} else "general",
            "max_results": int(max_results or 5),
            "search_depth": "basic",
        }
        if tf:
            body["time_range"] = tf

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                response = requests.post(
                    "https://api.tavily.com/search",
                    json=body,
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()
                items = [{
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "source": domain(item.get("url", "")),
                    "summary": item.get("content"),
                    "score": item.get("score"),
                } for item in data.get("results", [])]
                return {"tool": "web_search", "query": clean_query, "topic": topic, "timeframe": tf, "items": items}
            except Exception as exc:
                last_exc = exc
                if "429" in str(exc) or "timeout" in str(exc).lower():
                    continue
                raise

        raise last_exc or RuntimeError("Tavily request failed after retries")
    except Exception as exc:
        return err("web_search", exc)

