from __future__ import annotations

from typing import Any

from tools._shared import domain, err, terms


HIGH_TRUST_DOMAINS = {
    "openai.com",
    "anthropic.com",
    "microsoft.com",
    "google.com",
    "deepmind.google",
    "arxiv.org",
    "nature.com",
    "science.org",
    "sec.gov",
    "europa.eu",
    "who.int",
}

MEDIUM_TRUST_DOMAINS = {
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "nytimes.com",
    "theverge.com",
    "wired.com",
    "technologyreview.com",
}


def _source_domain(item: dict[str, Any]) -> str:
    source = str(item.get("source") or "").strip().lower().replace("www.", "")
    return source or domain(str(item.get("url") or "")).lower()


def _trust_score(source: str) -> tuple[int, str]:
    if source in HIGH_TRUST_DOMAINS or source.endswith(".gov") or source.endswith(".edu"):
        return 70, "high"
    if source in MEDIUM_TRUST_DOMAINS:
        return 50, "medium"
    if "x.com" in source or "twitter.com" in source or source.startswith("@"):
        return 20, "social_signal"
    return 35, "unknown"


def rank_sources(
    items: list[dict[str, Any]] | None = None,
    query: str = "",
    top_n: int = 5,
) -> dict[str, Any]:
    try:
        items = items or []
        query_terms = terms(query)
        ranked: list[dict[str, Any]] = []

        for index, item in enumerate(items):
            source = _source_domain(item)
            trust_score, trust_tier = _trust_score(source)
            item_text = " ".join(
                str(item.get(key) or "")
                for key in ("title", "summary", "source", "url")
            )
            overlap = len(query_terms & terms(item_text)) if query_terms else 0
            score = trust_score + min(overlap * 10, 30)
            ranked.append({
                **item,
                "rank_input_index": index,
                "score": score,
                "trust_tier": trust_tier,
                "ranking_reason": (
                    f"trust={trust_tier}; source={source or 'unknown'}; "
                    f"query_term_matches={overlap}"
                ),
            })

        ranked.sort(key=lambda item: (-item["score"], item["rank_input_index"]))
        top_n = max(1, min(int(top_n or 5), 20))
        return {
            "tool": "rank_sources",
            "query": query,
            "item_count": len(items),
            "ranked_items": ranked[:top_n],
        }
    except Exception as exc:
        return err("rank_sources", exc)

