---
name: documentation-generation
version: 1.0.0
description: Techniques for generating clear, maintainable technical documentation
used_by: []
---

## Capabilities
- Generate README files with setup, configuration, and usage instructions
- Generate API reference documentation from endpoint definitions
- Write inline code comments explaining the why, not the what
- Produce architecture decision records (ADRs) for significant technical choices
- Generate operational runbooks for deployment and incident response

## Instructions
When applying this skill:
- **README structure**: Installation → Configuration → Running locally → Running tests → Deployment → API reference → Contributing
- **Why not what**: comments explain the reason for a decision, not a restatement of the code
- **ADR format**: Context → Decision → Status → Consequences
- **API docs**: method, path, auth requirements, request schema, response schema, error codes, and at least one example per endpoint
- **Runbooks**: preconditions → numbered step-by-step procedure → expected outcome → rollback procedure → troubleshooting

## Expected Usage
Available as a standalone skill for any agent that needs to produce documentation
artifacts, or for a dedicated documentation pipeline stage.
