---
name: create-project
version: 1.1.0
description: Full SDLC pipeline from raw idea to reviewed, tested implementation
stages:
  - sequence: 1
    agent: product-manager
    task_from: idea
  - sequence: 2
    agent: architect
    task_from: ""
  - sequence: 3
    agent: developer
    task_from: ""
  - sequence: 4
    agent: coder
    task_from: ""
  - sequence: 5
    agent: reviewer
    task_from: ""
    loop_back_to: coder
    loop_on_verdict: "CHANGES REQUIRED"
    max_iterations: 3
  - sequence: 6
    agent: tester
    task_from: ""
    requires_verdict: "APPROVED"
---

## Purpose
Execute the complete SDLC pipeline for a brand-new project from a raw idea
through to a reviewed, tested implementation. Covers requirements gathering,
architecture design, implementation planning, code generation, iterative code
review, and QA validation with test artifacts.

## Entry Conditions
- A raw product idea or problem statement is available as free-form text.
- No prior artifacts are required — this workflow starts from scratch.
- The `product-manager`, `architect`, `developer`, `coder`, `reviewer`, and
  `tester` agents must all be registered in the agent registry.

## Inputs
| Input | Format | Provider |
|-------|--------|----------|
| Product idea | Free-form text | User (passed as `idea`) |

## Execution Order
1. **Product Manager** — raw idea → `requirements.md`
2. **Architect** — `requirements.md` → `solution-design.md`
3. **Developer** — `solution-design.md` → `implementation-plan.md`
4. **Coder** — `requirements.md` + `solution-design.md` + `implementation-plan.md` → `source-code.md`
5. **Reviewer** — all upstream artifacts → `review-report.md` + verdict
   - If `CHANGES REQUIRED`: return to Coder (see Retry Logic)
   - If `APPROVED`: proceed to Tester
6. **Tester** — `requirements.md` + `solution-design.md` + `source-code.md` + `review-report.md` → `test-strategy.md` + `qa-report.md`
   - If QA verdict is `FAILED`: return to Coder (see Retry Logic)
   - If QA verdict is `PASSED`: pipeline complete

## Agent Responsibilities
| Agent | Responsibility | Input Artifacts | Output Artifact |
|-------|---------------|-----------------|-----------------|
| product-manager | Convert idea into structured FRs, NFRs, user stories, and acceptance criteria | idea (text) | requirements.md |
| architect | Translate requirements into architecture, DB schema, and API contracts | requirements.md | solution-design.md |
| developer | Produce folder structure, modules, ordered tasks, and coding standards | solution-design.md | implementation-plan.md |
| coder | Generate complete production-ready source code and config files | requirements.md, solution-design.md, implementation-plan.md | source-code.md |
| reviewer | Review code against all upstream specs; issue verdict | requirements.md, solution-design.md, implementation-plan.md, source-code.md | review-report.md |
| tester | Generate test strategy, unit test code, and QA validation report | requirements.md, solution-design.md, source-code.md, review-report.md | test-strategy.md, qa-report.md |

## Skills Used
| Agent | Skills |
|-------|--------|
| product-manager | `requirements-analysis` |
| architect | `system-design` |
| developer | `implementation-planning` |
| coder | `source-code-generation` |
| reviewer | `code-review` |
| tester | `unit-test-generation`, `qa-validation` |

## Templates Used
| Agent | Template(s) |
|-------|-------------|
| product-manager | `requirements-template` |
| architect | `solution-design-template` |
| developer | `implementation-plan-template` |
| coder | `code-template` |
| reviewer | `review-report-template` |
| tester | `test-strategy-template`, `qa-report-template` |

Each agent resolves its template(s) via `AGENT_TEMPLATE_MAP` in
`app/core/config.py`; the Prompt Builder injects the resolved template's
`## Structure` as the agent's Required Output Format. Templates contribute
formatting only — they carry no reasoning, business rules, or orchestration
logic, which remain owned by this workflow and the agents themselves.

## Produced Artifacts
| Artifact | File | Produced By |
|----------|------|-------------|
| Requirements | requirements.md | product-manager |
| Solution Design | solution-design.md | architect |
| Implementation Plan | implementation-plan.md | developer |
| Source Code | source-code.md | coder |
| Review Report | review-report.md | reviewer |
| Test Strategy | test-strategy.md | tester |
| QA Report | qa-report.md | tester |

## Success Conditions
- All six agents complete with status `success`.
- Reviewer verdict is `APPROVED`.
- QA verdict is `PASSED`.
- All seven artifacts are present in `workspace/project_{id}/documents/`.
- Pipeline `status` field is `completed`.

## Failure Conditions
- Any agent fails with an LLM error, missing dependency, or parse error → pipeline
  halts immediately; all subsequent stages are marked `skipped`.
- Reviewer returns `CHANGES REQUIRED` on the third iteration (max_iterations reached)
  → pipeline fails; Tester does not run.
- Tester QA verdict is `FAILED` after the maximum QA retry iterations →
  pipeline fails.
- `source-code.md` is absent when the Reviewer runs (should not occur in normal
  flow but will surface as a `MissingDependencyError`).

## Retry Logic
**Review loop (Reviewer → Coder → Reviewer):**
- Trigger: Reviewer verdict is `CHANGES REQUIRED`.
- Action: Coder re-runs with `review-report.md` injected as additional upstream
  context; then Reviewer re-runs against the updated `source-code.md`.
- Maximum iterations: **3**. On the third `CHANGES REQUIRED` verdict the pipeline
  fails without proceeding to Tester.
- Iteration counter is stored in `PipelineRun.review_iterations`.

**QA loop (Tester → Coder → Reviewer → Tester):**
- Trigger: Tester QA verdict is `FAILED`.
- Action: Coder re-runs with `qa-report.md` injected as context; Reviewer re-runs;
  then Tester re-runs.
- Maximum iterations: controlled by `MAX_REVIEW_ITERATIONS` environment variable
  (default: 3, shared with the review loop counter).

## Exit Conditions
| Condition | Outcome |
|-----------|---------|
| All stages succeed, reviewer approved, QA passed | `status: completed` — full artifact package returned |
| Any agent throws an unrecoverable error | `status: failed` — partial artifacts returned; step log shows which stage failed |
| Review loop exhausted (3× CHANGES REQUIRED) | `status: failed` — Tester skipped; review-report.md available |
| QA loop exhausted (failed QA after max retries) | `status: failed` — qa-report.md available showing failing requirements |
