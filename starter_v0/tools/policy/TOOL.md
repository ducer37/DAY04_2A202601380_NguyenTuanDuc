---
name: policy
track: bonus
kind: local_knowledge
provider: markdown_folder
requires_env: []
inputs: [query, policy_area, top_k]
outputs: [results, match_count, freshness, trust_boundary]
side_effect: false
---
# policy

Searches internal company policy documents under `starter_v0/company_policy/*.md` using BM25-style keyword matching and title boosting.

### Policy Areas:
- `all`: Search across all policy documents.
- `ai_research`: AI research workflow, paper scanning, briefing guidelines.
- `source_citation`: Rules on source attribution and citation formats.
- `data_privacy`: Data handling and privacy boundaries.
- `external_publishing`: Guidelines for posting content externally.
- `tool_usage`: Internal rules on tool execution and security boundaries.
