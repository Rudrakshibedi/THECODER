---
name: documentation
version: 1.1.0
description: Standalone pipeline for generating technical documentation from existing artifacts
stages:
  - sequence: 1
    agent: developer
    task_from: idea
---

## Purpose
Generate or regenerate comprehensive technical documentation for an existing
system. Uses all available upstream SDLC artifacts as source material and
produces a structured `implementation-plan.md` that serves as the authoritative
developer reference: module descriptions, folder structure, API reference, setup
guide, and operational notes. Use this workflow after a `create-project` run or
whenever the documentation has drifted from the codebase.

## Entry Conditions
- The following artifacts must already exist in `workspace/project_{id}/documents/`:
  - `solution-design.md` — **required**: the `developer` agent declares this as
    a hard dependency; the workflow will fail with `MissingDependencyError`
    if it is absent.
  - `requirements.md` — recommended but not a hard dependency for the Developer.
  - `source-code.md` — recommended; allows the Developer to document the actual
    implementation rather than the planned one.
- The `developer` agent must be registered in the agent registry.
- No review or test stage is included — documentation is a human-reviewed
  deliverable, not machine-validated code.

## Inputs
| Input | Source | Required |
|-------|--------|----------|
| Documentation scope or focus | Free-form text passed as `idea` (e.g. "Regenerate full developer docs" or "Document the authentication module") | Yes |
| `project_id` | Existing project with at least `solution-design.md` present | Yes |
| `workflow_name` | `"documentation"` | Yes |

## Execution Order
```
Documentation scope description (free-form text)
  ↓
[1] Developer  →  implementation-plan.md  (used as documentation artifact)
DONE
```
Single-stage workflow. No review or QA loop — documentation quality is
assessed by human review outside the pipeline.

## Agent Responsibilities
| Agent | Responsibility | Input Artifacts | Output Artifact |
|-------|---------------|-----------------|-----------------|
| developer | Read all available upstream artifacts and produce a structured implementation-plan.md that documents the system: folder structure, module responsibilities, API reference, setup and deployment instructions, coding standards, and operational notes. The documentation scope passed as `idea` may focus the output on a specific area | solution-design.md (required), requirements.md (if present), source-code.md (if present) | implementation-plan.md |

## Skills Used
| Agent | Skills |
|-------|--------|
| developer | `implementation-planning`, `documentation-generation` |

Note: `documentation-generation` is defined in `skills/documentation-generation.md`
with `used_by: []`. This workflow is the intended consumer of that skill. The skill
is loaded by the agent runner via `AGENT_SKILL_MAP` — to activate it for this
workflow, add `documentation-generation` to the developer's entry in `AGENT_SKILL_MAP`
in `app/core/config.py` when the backend phase is implemented.

## Templates Used
| Agent | Template(s) |
|-------|-------------|
| developer | `implementation-plan-template` (agent's default template) |

A `documentation-template.md` now exists in `templates/` with a dedicated
README/API-reference/ADR/runbook structure, matching this workflow's intent
better than the developer's default `implementation-plan-template`. It is
not yet wired in: `AGENT_TEMPLATE_MAP` resolves templates per-agent, not
per-workflow-stage, so the developer agent always resolves
`implementation-plan-template` regardless of which workflow invokes it.
Activating `documentation-template` for this workflow specifically would
require adding per-stage template overrides to the workflow stage schema
and threading that override through `pipeline_service` into
`agent_runner.run_agent()` — a backend orchestration change, not a template
change, and out of scope for this phase. Note this for a future backend
enhancement pass.

## Produced Artifacts
| Artifact | File | Produced By | Note |
|----------|------|-------------|------|
| Developer Documentation | implementation-plan.md | developer | Overwrites prior implementation-plan.md; serves as the system's authoritative developer reference |

## Success Conditions
- The developer stage completes with `status: success`.
- `implementation-plan.md` is written to `workspace/project_{id}/documents/`.
- The artifact contains all expected sections: folder structure, module
  descriptions, API reference, setup instructions, and coding standards.
- Pipeline run record shows `status: completed`.

## Failure Conditions
- `solution-design.md` is absent → developer fails with `MissingDependencyError`
  at stage 1. Run `create-project` or `architecture-design` first.
- LLM error or parse error during the developer run → pipeline halts; no
  artifact is written. Retry by re-running the workflow.
- The `idea` input is too vague for the developer to produce a useful document
  → technically succeeds but output quality may be low. Provide a focused scope.

## Retry Logic
No automatic retry logic. This is a single-stage workflow with no loop conditions.

If the stage fails:
- Verify `solution-design.md` exists for the project.
- Correct the issue (run an upstream workflow if needed).
- Re-run `documentation` — the developer re-reads all available artifacts fresh
  on every execution, so re-running is always safe and idempotent.

If the output quality is poor:
- Re-run with a more specific `idea` (e.g. "Document only the authentication
  and payment modules with full API reference").

## Exit Conditions
| Condition | Outcome |
|-----------|---------|
| Developer succeeds | `status: completed` — updated implementation-plan.md available |
| `solution-design.md` missing | `status: failed` at stage 1 — run an upstream workflow first |
| Any LLM or parse error | `status: failed` — step log shows error detail; retry is safe |
