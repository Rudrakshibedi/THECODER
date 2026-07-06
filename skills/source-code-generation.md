---
name: source-code-generation
version: 1.0.0
description: Patterns and discipline for generating complete, production-ready source code
used_by:
  - coder
---

## Capabilities
- Translate API contracts into complete, runnable handler implementations
- Apply layered architecture patterns (controller/service/repository) consistently
- Implement authentication and authorisation middleware correctly
- Write defensive input validation at every external boundary
- Generate complete configuration files for the detected technology stack

## Instructions
When applying this skill, enforce these disciplines:
- **No stubs**: every function body must contain a working implementation; comments like "TODO" or "implement this" are forbidden
- **Error path parity**: for every happy path, implement the corresponding error path (wrong input, resource not found, permission denied)
- **Validation at the boundary**: validate all inputs at the entry point; never trust data from outside the process
- **Secrets via environment**: never hardcode credentials or API keys; use environment variables with all names documented in .env.example
- **Logging at decisions**: log at INFO level when significant branching decisions occur (auth pass/fail, record found/not found, payment processed)
- **Consistent naming**: follow naming conventions from implementation-plan.md exactly — do not invent alternatives

## Expected Usage
Injected into the coder agent system prompt to enforce production-code discipline
and prevent partial or placeholder implementations.
