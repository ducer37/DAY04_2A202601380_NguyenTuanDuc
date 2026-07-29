from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from tools._shared import domain


def _src(item: dict[str, Any]) -> str:
    src = item.get("source") or domain(item.get("url", ""))
    url = item.get("url") or ""
    return f"[{src}]({url})" if url else (src or "")


def _bullet(item: dict[str, Any]) -> str:
    text = (item.get("summary") or item.get("title") or "").strip().replace("\n", " ")
    if len(text) > 280:
        text = text[:277] + "..."
    return f"- {text} - {_src(item)}"


def render_digest(items: list[dict[str, Any]] | None = None, template: str = "sections", headline: str = "") -> dict[str, Any]:
    items = items or []
    if not items:
        return {
            "tool": "render_digest",
            "template": template,
            "markdown": f"**{headline}**\n\n*(Không có dữ liệu để hiển thị)*" if headline else "*(Không có dữ liệu để hiển thị)*",
            "item_count": 0,
            "warning": "No items provided to format",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    if template == "brief":
        markdown = (f"**{headline}**\n\n" if headline else "") + "\n".join(_bullet(item) for item in items[:5])
    elif template == "bullets":
        markdown = "\n".join(_bullet(item) for item in items)
    elif template == "thread":
        markdown = "\n\n".join(f"{index + 1}/ {_bullet(item)[2:]}" for index, item in enumerate(items))
    elif template == "summary":
        top = items[:3]
        lines = [f"**{headline or 'Tóm tắt nhanh'}**", ""] if headline else []
        for idx, item in enumerate(top, 1):
            title = item.get("title") or "Item"
            sum_text = (item.get("summary") or title).strip().replace("\n", " ")
            if len(sum_text) > 150:
                sum_text = sum_text[:147] + "..."
            lines.append(f"{idx}. **{title}**: {sum_text} ({_src(item)})")
        markdown = "\n".join(lines)
    elif template == "daily_ai_vn":
        groups: dict[str, list[dict[str, Any]]] = {}
        for item in items:
            groups.setdefault(item.get("section", "Tin chính"), []).append(item)
        parts = [f"**{headline or 'Tin tức hôm nay'}**", ""]
        for section, section_items in groups.items():
            parts += [f"**{section}**", *[_bullet(item) for item in section_items], ""]
        markdown = "\n".join(parts)
    else:
        groups: dict[str, list[dict[str, Any]]] = {}
        for item in items:
            groups.setdefault(item.get("section", "Tổng hợp"), []).append(item)
        parts = ([f"# {headline}", ""] if headline else [])
        for section, section_items in groups.items():
            parts += [f"## {section}", *[_bullet(item) for item in section_items], ""]
        markdown = "\n".join(parts)

    return {
        "tool": "render_digest",
        "template": template,
        "markdown": markdown,
        "item_count": len(items),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
