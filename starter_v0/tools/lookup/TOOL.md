---
name: lookup
track: core
kind: live_api
provider: Tavily
requires_env: [TAVILY_API_KEY]
inputs: [query, topic, timeframe, max_results]
outputs: [items]
side_effect: false
---
# lookup

Searches the web via Tavily API with query normalization and automatic retry support.

### Argument Rules:
- `query`: Must contain ONLY clean topic keywords (e.g. `"AI"`, `"robotics"`). DO NOT append `"news"`, `"today"`, or timeframe words.
- `topic`: `"news"` for breaking/current news, `"general"` for general knowledge.
- `timeframe`: `"day"`, `"week"`, `"month"`, `"year"`. Use `"day"` when searching for today's news.

### Examples:
| User Request | Correct Arguments |
|---|---|
| "Tin AI hôm nay" | `query="AI"`, `topic="news"`, `timeframe="day"` |
| "Nghiên cứu về robotics" | `query="robotics"`, `topic="general"`, `timeframe="week"` |
