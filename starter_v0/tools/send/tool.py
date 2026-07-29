from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, err


MAX_TELEGRAM_CHARS = 4096


def send_telegram(text: str = "", confirmed: bool = False) -> dict[str, Any]:
    if not confirmed:
        return {
            "tool": "send_telegram",
            "status": "needs_confirmation",
            "message": "Only send after the user explicitly confirms.",
        }
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            raise RuntimeError("Missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID env var")

        clean_text = text or ""
        truncated = False
        if len(clean_text) > MAX_TELEGRAM_CHARS:
            clean_text = clean_text[: MAX_TELEGRAM_CHARS - 3] + "..."
            truncated = True

        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": clean_text, "parse_mode": "Markdown"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return {
            "tool": "send_telegram",
            "status": "sent",
            "chars_sent": len(clean_text),
            "truncated": truncated,
            "preview": clean_text[:100],
        }
    except Exception as exc:
        return err("send_telegram", exc)

