---
name: papers
track: bonus
kind: live_api
provider: arXiv API
requires_env: [ARXIV_USER_AGENT]
inputs: [query, max_results, sort_by]
outputs: [items, total_results, rate_limit_note]
side_effect: false
---
# papers

Searches arXiv via the official Atom API with rate limiting support.

### When to use `papers` vs `lookup`:
- Use `papers` when searching for academic/scientific papers on arXiv.
- Use `lookup` when searching for general web news or articles.

### Arguments:
- `query`: Scientific topic keywords in English or Vietnamese (e.g. "diffusion model", "mô hình ngôn ngữ").
- `max_results`: Maximum number of results to fetch (default: 5, min: 1, max: 10).
- `sort_by`: `relevance` (default), `lastUpdatedDate` (newest updated), or `submittedDate` (newest submitted).

### Rate Limit & Constraints:
- arXiv API requires at least 3 seconds delay between requests.
- Tool automatically handles in-process rate limiting.
