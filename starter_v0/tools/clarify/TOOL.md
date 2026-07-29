---
name: clarify
track: core
kind: control
requires_env: []
inputs: [question, response_type, options]
outputs: [question, response_type, options, awaiting_user, timestamp]
side_effect: false
requires_confirmation: false
---
# clarify

Returns a question to the user and pauses execution until the user responds in the next turn.

### Response Types:
- `text`: Use when asking open-ended clarifying questions (e.g. requesting a missing Twitter handle or URL).
- `yes_no`: Use when asking for user confirmation before executing side-effect action tools (e.g. `send`).
- `choice`: Use when offering a list of explicit options. Requires `options` list to be non-empty.

### Usage Guidance:
- **DO NOT** guess missing account handles or URLs. Call `clarify(response_type="text")`.
- **DO NOT** execute action tools directly without user consent. Call `clarify(response_type="yes_no")`.
