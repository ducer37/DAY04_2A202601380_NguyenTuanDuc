---
name: paper_text
track: bonus
kind: live_api_plus_local_extract
provider: arXiv + pypdf
requires_env: [ARXIV_USER_AGENT]
inputs: [arxiv_url, max_pages, max_chars]
outputs: [items, pdf_path, txt_path, page_count, section_count, has_references]
side_effect: local_file_write
---
# paper_text

Downloads an arXiv PDF paper and extracts its text locally using `pypdf`.

### Internal Pipeline:
1. Parses `arxiv_url` or arXiv ID (e.g. `2301.07041` or `https://arxiv.org/abs/2301.07041`).
2. Downloads PDF to `starter_v0/arxiv_papers/{arxiv_id}.pdf`.
3. Extracts text from the first `max_pages` pages and writes excerpt to `{arxiv_id}.txt`.

### When to use `paper_text` vs `papers`:
- Use `papers` when searching for multiple papers by topic (returns title and abstract).
- Use `paper_text` when given a specific arXiv URL/ID and asked to inspect or read its full content.

### Constraints:
- Requires `pypdf` python package.
- Output text is truncated to `max_chars` (default: 8000).
