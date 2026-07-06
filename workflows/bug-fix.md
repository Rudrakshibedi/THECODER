---
name: bug-fix
version: 1.1.0
description: Minimal pipeline for investigating, fixing, and validating a reported bug
stages:
  - sequence: 1
    agent: coder
    task_from: idea
  - sequence: 2
    agent: reviewer
    task_from: ""
    loop_back_to: coder
    loop_on_verdict: "CHANGES REQUIRED"
    max_iterations: 2
  - sequence: 3
    agent: tester
    task_from: ""
    requires_verdict: "APPROVED"
---

## Purpose
Apply a targeted fix for a single reported defect. The bug description,
reproduction steps, and expected behaviour are passed as the `idea`. The
Coder investigates the root cause and implements the fix; the Reviewer
validates correctness and checks for regressions; the Tester confirms the
defect is resolved and adds a permanent regression test. The PM, Architect,
and Developer stages are omitted because the requirements, architecture, and
implementation plan already exist — only the source code changes.

## Entry Conditions
- A project with all of the following artifacts already present in
  `workspace/project_{id}/documents/`:
  - `requirements.md`
  - `solution-design.md`
  - `implementation-plan.md`
  - `source-code.md`
- A clear bug report available as free-form text, containing at minimum:
  - What the expected behaviour is
  - What the actual (incorrect) behaviour is
  - Reproduction steps
- The project record must exist in the system (`project_id` must be valid).
- Agents `coder`, `reviewer`, and `tester` must all be registered.

## Inputs
| Input | Source | Required |
|-------|--------|----------|
| Bug description + reproduction steps | Free-form text passed as `idea` | Yes |
| `project_id` | Existing project with all four prior artifacts | Yes |
| `workflow_name` | `"bug-fix"` | Yes |

## Execution Order
```
Bug description + reproduction steps (free-form text)
  ↓
[1] Coder     →  source-code.md  (patched implementation)
  ↓
[2] Reviewer  →  review-report.md
  ↓ APPROVED             ↑ CHANGES REQUIRED (max 2×)
  ↓                      └── [1] Coder (re-run with review context)
[3] Tester    →  test-strategy.md
              →  unit-tests.md  (includes regression test for this bug)
              →  qa-report.md
  ↓ PASSED               ↑ FAILED (max 2× total)
  ↓                      └── [1] Coder → [2] Reviewer → [3] Tester
DONE
```

## Agent Responsibilities
| Agent | Responsibility | Input Artifacts | Output Artifact |
|-------|---------------|-----------------|-----------------|
| coder | Investigate the root cause using all upstream artifacts. Implement a targeted fix that resolves the defect without modifying unrelated code. Document what was changed and why in the source-code.md header | requirements.md, solution-design.md, implementation-plan.md, + bug description (as task) | source-code.md |
| reviewer | Verify the fix is correct and complete. Confirm no regressions were introduced. Flag any CRITICAL or HIGH issues that indicate the fix approach is wrong | requirements.md, solution-design.md, implementation-plan.md, source-code.md | review-report.md |
| tester | Validate the reported defect is resolved. Generate a regression test that will permanently catch this class of bug. Produce a QA report confirming the fix | requirements.md, solution-design.md, source-code.md, review-report.md | test-strategy.md, unit-tests.md, qa-report.md |

## Skills Used
| Agent | Skills |
|-------|--------|
| coder | `source-code-generation` |
| reviewer | `code-review` |
| tester | `unit-test-generation`, `qa-validation` |

## Templates Used
| Agent | Template(s) |
|-------|-------------|
| coder | `code-template` |
| reviewer | `review-report-template` |
| tester | `test-strategy-template`, `qa-report-template` |

Resolved automatically per agent via `AGENT_TEMPLATE_MAP`; no workflow-level
template selection logic is needed since this workflow only reuses agents'
default templates.

## Produced Artifacts
| Artifact | File | Produced By | Note |
|----------|------|-------------|------|
| Source Code | source-code.md | coder | Patched implementation |
| Review Report | review-report.md | reviewer | Fix validation |
| Test Strategy | test-strategy.md | tester | Focused on the defect area |
| Unit Tests | unit-tests.md | tester | Includes regression test |
| QA Report | qa-report.md | tester | Confirms defect resolved |

## Success Conditions
- All three stages complete with `status: success`.
- Reviewer verdict is `APPROVED` within two iterations.
- Tester QA verdict is `PASSED`.
- `qa-report.md` shows the requirement linked to the bug as `PASS`.
- Pipeline run record shows `status: completed`.

## Failure Conditions
- Any required upstream artifact (`requirements.md`, `solution-design.md`,
  `implementation-plan.md`, or `source-code.md`) is absent → Coder fails
  with `MissingDependencyError`; pipeline halts at stage 1. Run
  `create-project` first to generate the missing artifacts.
- Reviewer issues `CHANGES REQUIRED` on the second iteration (max_iterations
  reached) → pipeline halts; Tester is marked `skipped`. The fix approach
  needs rethinking — re-run `bug-fix` with an updated bug description.
- Tester QA verdict is `FAILED` after the maximum retry iterations → pipeline
  fails; `qa-report.md` identifies which requirements are still failing.
- Any LLM or parse error → pipeline halts; all artifacts produced before the
  failure remain available.

## Retry Logic
**Review loop (Reviewer → Coder → Reviewer):**
- Trigger: Reviewer verdict is `CHANGES REQUIRED`.
- Action: Coder re-runs with `review-report.md` injected as upstream context.
  Coder must address every CRITICAL and HIGH issue identified without
  widening the scope of the fix beyond the reported defect.
- Maximum iterations: **2**. Intentionally lower than `create-project` (3×)
  because a targeted bug fix should converge quickly. A fix that requires
  more than two review cycles indicates the root cause analysis was incorrect
  and the workflow should be re-started with a revised bug description.
- Exhausted: pipeline fails; Tester does not run.
- Counter: stored in `PipelineRun.review_iterations`.

**QA loop (Tester → Coder → Reviewer → Tester):**
- Trigger: Tester QA verdict is `FAILED`.
- Action: Coder re-runs with `qa-report.md` injected as context. Reviewer
  re-runs. Tester re-runs.
- Maximum iterations: controlled by `MAX_REVIEW_ITERATIONS` environment
  variable (default: 3, shared counter with the review loop).
- Exhausted: pipeline fails. Re-run `bug-fix` with a more precise bug
  description or escalate to `feature-development` if the fix requires
  broader changes than originally scoped.

## Exit Conditions
| Condition | Outcome |
|-----------|---------|
| All stages succeed, reviewer approved, QA passed | `status: completed` — patched source code and full test artifacts returned |
| Required upstream artifact missing at start | `status: failed` at stage 1 — run `create-project` to generate missing artifacts first |
| Any unrecoverable LLM or parse error | `status: failed` — partial artifacts and step log returned (HTTP 206) |
| Review loop exhausted (2× CHANGES REQUIRED) | `status: failed` — Tester skipped; re-run with revised bug description |
| QA loop exhausted (QA FAILED after max retries) | `status: failed` — qa-report.md identifies failing requirements; escalate to `feature-development` if broader changes are needed |
