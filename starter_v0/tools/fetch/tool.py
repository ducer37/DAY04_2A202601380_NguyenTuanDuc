from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, domain, err


def read_url(url: str = "") -> dict[str, Any]:
    try:
        clean_url = (url or "").strip()
        if not clean_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL format: '{url}'. Must start with http:// or https://")

        key = os.getenv("FIRECRAWL_API_KEY")
        if not key:
            raise RuntimeError("Missing FIRECRAWL_API_KEY env var")

        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                response = requests.post(
                    "https://api.firecrawl.dev/v1/scrape",
                    json={"url": clean_url, "formats": ["markdown"]},
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json().get("data", {})
                meta = data.get("metadata", {}) or {}
                markdown_content = data.get("markdown") or ""
                if len(markdown_content) > 10000:
                    markdown_content = markdown_content[:9997] + "..."

                return {"tool": "read_url", "url": clean_url, "items": [{
                    "title": meta.get("title") or clean_url,
                    "url": meta.get("sourceURL") or clean_url,
                    "source": domain(clean_url),
                    "summary": markdown_content[:4000],
                }]}
            except Exception as exc:
                last_exc = exc
                if "429" in str(exc) or "timeout" in str(exc).lower():
                    continue
                raise

        raise last_exc or RuntimeError("Firecrawl request failed after retries")
    except Exception as exc:
        return err("read_url", exc)

