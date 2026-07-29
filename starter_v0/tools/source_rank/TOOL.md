---
name: source_rank
track: team
kind: local_analyzer
requires_env: []
inputs: [items, query, top_n]
outputs: [ranked_items, item_count]
side_effect: false
---
# source_rank

Ranks already-collected sources or user-provided source items by rough trust and
relevance. This tool does not fetch new information.

Use it when the user asks to rank, prioritize, filter, or compare sources that
are already present in the conversation or returned by earlier tools.

Do not use it for web discovery, reading a URL, social search, account timelines,
or formatting a digest.

Each input item can include `title`, `url`, `source`, and `summary`. The tool
returns the same items with `score`, `trust_tier`, and `ranking_reason`.

