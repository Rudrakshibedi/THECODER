---
name: feature-development
version: 1.1.0
description: Targeted pipeline for adding a new feature to an existing system
stages:
  - sequence: 1
    agent: product-manager
    task_from: idea
  - sequence: 2
    agent: architect
    task_from: ""
  - sequence: 3
    agent: coder
    task_from: ""
  - sequence: 4
    agent: reviewer
    task_from: ""
    loop_back_to: coder
    loop_on_verdict: "CHANGES REQUIRED"
    max_iterations: 3
  - sequence: 5
    agent: tester
    task_from: ""
    requires_verdict: "APPROVED"
---

## Purpose
Add a well-defined new feature to an existing system that already has a
codebase, requirements, and architecture in place. The Developer stage is
intentionally omitted because the project folder structure and module
definitions are already established — the Architect produces only the
targeted design changes needed for the feature, and the Coder implements
directly against them.

## Entry Conditions
- An existing project with the following artifacts already present in
  `workspace/project_{id}/documents/`:
  - `implementation-plan.md` — must exist; Coder depends on it but this
    workflow does not re-run the Developer to regenerate it.
  - `source-code.md` — must exist; represents the codebase being extended.
- `requirements.md` and `solution-design.md` will be replaced by this
  workflow's PM and Architect runs.
- The feature description must be specific enough for the PM to scope
  requirements without a full discovery phase.
- The project record must exist in the system (`project_id` must be valid).
- Agents `product-manager`, `architect`, `coder`, `reviewer`, and `tester`
  must all be registered in the agent registry.

## Inputs
| Input | Source | Required |
|-------|--------|----------|
| Feature description | Free-form text passed as `idea` | Yes |
| `project_id` | Existing project with prior artifacts | Yes |
| `workflow_name` | `"feature-development"` | Yes |

## Execution Order
```
Feature description (free-form text)
  ↓
[1] Product Manager  →  requirements.md  (feature-scoped)
  ↓
[2] Architect        →  solution-design.md  (full updated design)
  ↓
[3] Coder            →  source-code.md  (feature implementation)
  ↓
[4] Reviewer         →  review-report.md
  ↓ APPROVED                    ↑ CHANGES REQUIRED (max 3×)
  ↓                             └── [3] Coder (re-run with review context)
[5] Tester           →  test-strategy.md
                     →  unit-tests.md
                     →  qa-report.md
  ↓ PASSED                      ↑ FAILED (max 3× total)
  ↓                             └── [3] Coder → [4] Reviewer → [5] Tester
DONE
```

## Agent Responsibilities
| Agent | Responsibility | Input Artifacts | Output Artifact |
|-------|---------------|-----------------|-----------------|
| product-manager | Define requirements for the new feature only. Explicitly scope out-of-scope items and note assumptions about existing behaviour that must be preserved | idea (text) | requirements.md |
| architect | Define architectural changes for the feature: new or modified endpoints, schema migrations, new components. Produce a complete updated solution-design.md, not a diff | requirements.md | solution-design.md |
| coder | Implement the feature following updated solution-design.md and existing implementation-plan.md. Preserve all existing behaviour — only add or modify what the feature requires | requirements.md, solution-design.md, implementation-plan.md | source-code.md |
| reviewer | Review the feature implementation against updated requirements and design; verify no regressions in existing functionality | requirements.md, solution-design.md, implementation-plan.md, source-code.md | review-report.md |
| tester | Generate tests specific to the new feature plus regression tests for existing behaviour that the feature touches | requirements.md, solution-design.md, source-code.md, review-report.md | test-strategy.md, unit-tests.md, qa-report.md |

## Skills Used
| Agent | Skills |
|-------|--------|
| product-manager | `requirements-analysis` |
| architect | `system-design` |
| coder | `source-code-generation` |
| reviewer | `code-review` |
| tester | `unit-test-generation`, `qa-validation` |

## Templates Used
| Agent | Template(s) |
|-------|-------------|
| product-manager | `requirements-template` |
| architect | `solution-design-template` |
| coder | `code-template` |
| reviewer | `review-report-template` |
| tester | `test-strategy-template`, `qa-report-template` |

Resolved automatically per agent via `AGENT_TEMPLATE_MAP`; no workflow-level
template selection logic is needed since this workflow only reuses agents'
default templates.

## Produced Artifacts
| Artifact | File | Produced By | Note |
|----------|------|-------------|------|
| Requirements | requirements.md | product-manager | Replaces prior; scoped to this feature |
| Solution Design | solution-design.md | architect | Full updated design, not a delta |
| Source Code | source-code.md | coder | Feature implementation |
| Review Report | review-report.md | reviewer | |
| Test Strategy | test-strategy.md | tester | |
| Unit Tests | unit-tests.md | tester | |
| QA Report | qa-report.md | tester | |

## Success Conditions
- All five stages complete with `status: success`.
- Reviewer verdict is `APPROVED` within the allowed iterations.
- Tester QA verdict is `PASSED`.
- All seven artifacts are written to `workspace/project_{id}/documents/`.
- Pipeline run record shows `status: completed`.

## Failure Conditions
- `implementation-plan.md` or `source-code.md` is absent when the Coder runs
  → `MissingDependencyError`; pipeline halts at stage 3.
- Reviewer issues `CHANGES REQUIRED` on the third iteration (max_iterations
  reached) → pipeline halts; Tester is marked `skipped`.
- Tester QA verdict is `FAILED` after the maximum retry iterations → pipeline
  fails; all artifacts produced so far remain available.
- Any LLM error or parse error on any stage → pipeline halts immediately;
  subsequent stages are marked `skipped`.

## Retry Logic
**Review loop (Reviewer → Coder → Reviewer):**
- Trigger: Reviewer verdict is `CHANGES REQUIRED`.
- Action: Coder re-runs with `review-report.md` injected as upstream context,
  instructed to address all CRITICAL and HIGH issues without breaking existing
  behaviour. Reviewer then re-runs against the updated `source-code.md`.
- Maximum iterations: **3** total Reviewer executions.
- Exhausted: pipeline fails; Tester does not run.
- Counter: stored in `PipelineRun.review_iterations`.

**QA loop (Tester → Coder → Reviewer → Tester):**
- Trigger: Tester QA verdict is `FAILED`.
- Action: Coder re-runs with `qa-report.md` injected as context to address
  failing requirements. Reviewer re-runs to re-approve. Tester re-runs.
- Maximum iterations: controlled by `MAX_REVIEW_ITERATIONS` environment
  variable (default: 3, shared counter with the review loop).
- Exhausted: pipeline fails; `qa-report.md` available showing which
  requirements are still failing.

## Exit Conditions
| Condition | Outcome |
|-----------|---------|
| All stages succeed, reviewer approved, QA passed | `status: completed` — full artifact package returned |
| `implementation-plan.md` or `source-code.md` missing at start | `status: failed` at stage 3 — run `create-project` first |
| Any unrecoverable LLM or parse error | `status: failed` — partial artifacts and step log returned (HTTP 206) |
| Review loop exhausted (3× CHANGES REQUIRED) | `status: failed` — Tester skipped; review-report.md available |
| QA loop exhausted (QA FAILED after max retries) | `status: failed` — qa-report.md available showing failing requirements |
