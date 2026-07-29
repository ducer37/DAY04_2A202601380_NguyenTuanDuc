from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def ask_user(question: str = "", response_type: str = "text", options: list[str] | None = None) -> dict[str, Any]:
    valid_types = {"text", "yes_no", "choice"}
    if response_type not in valid_types:
        response_type = "text"
        
    opts = options or []
    if response_type == "choice" and not opts:
        return {
            "tool": "ask_user",
            "error": "ValueError",
            "message": "response_type 'choice' requires non-empty options list",
            "awaiting_user": False,
        }

    return {
        "tool": "ask_user",
        "question": question,
        "response_type": response_type,
        "options": opts,
        "awaiting_user": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

