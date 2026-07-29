---
name: fetch
track: core
kind: live_api
provider: Firecrawl
requires_env: [FIRECRAWL_API_KEY]
inputs: [url]
outputs: [items]
side_effect: false
---
# fetch

Reads the content of a single URL via Firecrawl with URL validation and content truncation.

### Constraints:
- `url` must start with `http://` or `https://`.
- Output markdown content is truncated to 10,000 characters maximum to avoid context overflow.
- If no explicit URL is provided in user input, DO NOT call `fetch`. Call `clarify` instead.
