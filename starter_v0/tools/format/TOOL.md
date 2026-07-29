---
name: format
track: core
kind: local_formatter
requires_env: []
inputs: [items, template, headline]
outputs: [markdown, item_count, generated_at]
side_effect: false
---
# format

Formats already-collected items into a markdown digest. It does not fetch new data.

### Templates:
- `brief`: Headline followed by up to 5 top bullet points.
- `bullets`: Complete list of bullet points for all items.
- `thread`: Numbered social-style thread format (`1/`, `2/`, ...).
- `summary`: Concise summary of top 3 items with short excerpts.
- `daily_ai_vn`: Grouped by sections with bold headlines.
- `sections` (default): H1 headline with H2 section groupings.
