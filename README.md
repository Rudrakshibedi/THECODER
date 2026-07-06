# AI SDLC Agent Hub — Foundation

Backend foundation for storing and dynamically loading SDLC agents
(PM, Architect, Developer, Tester, Reviewer) defined as markdown files.

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On startup, the app scans `agents/*.md`, parses each one, and syncs
metadata into a SQLite registry (`agent_hub.db`).

## API

- `GET /agents` — list all registered agents (id, name, role, version, file_path)
- `GET /agents/{name}` — full parsed detail (responsibilities, instructions, output format)
- `POST /agents/register` — register an agent
  - `{"name": "pm_agent"}` — index an existing `agents/pm_agent.md` file
  - `{"name": "new_agent", "markdown_content": "---\nname: new_agent\nrole: ...\n---\n## Instructions\n..."}` — create/overwrite a file and register it

## Agent markdown format

```markdown
---
name: pm_agent
role: Product Manager
version: 1.0.0
---

## Responsibilities
- bullet
- bullet

## Instructions
Free-text instructions for the agent.

## Output Format
Expected structure of the agent's output.
```

## Design notes

- Markdown files are the source of truth for agent content; the DB only
  indexes metadata (name, role, version, file path, content hash) for
  fast listing and change detection.
- `services/agent_parser.py` is pure (no I/O) and unit-testable in isolation.
- `services/agent_loader.py` owns all filesystem access and DB sync.
- Swap `DATABASE_URL` in `app/core/config.py` to move from SQLite to Postgres
  without touching any other code.

## Next steps (not in this foundation)

- Agent execution engine (feed loaded instructions + context into an LLM call)
- Pipeline orchestration (PM → Architect → Developer → Tester → Reviewer handoff)
- Auth on the registration endpoint
- Versioning/history of agent markdown changes
