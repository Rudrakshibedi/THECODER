---
name: qa-validation
version: 1.0.0
description: Techniques for systematically validating an implementation against functional and non-functional requirements
used_by:
  - tester
---

## Capabilities
- Build a requirement traceability matrix mapping test results to FR-# and NFR-# identifiers
- Classify defects by severity and link them to the requirement they violate
- Distinguish statically testable requirements (code inspection) from dynamically testable ones (runtime)
- Produce a structured QA report with a machine-readable verdict

## Instructions
When applying this skill, follow this validation process:
1. **Extract all requirements**: list every FR-# and NFR-# from requirements.md
2. **Classify testability**: statically testable (code inspection), dynamically testable (requires execution), or not testable at this stage
3. **Trace tests to requirements**: every test case must reference the FR-# or NFR-# it validates
4. **Classify defects**: CRITICAL = requirement entirely unmet; HIGH = requirement partially met; MEDIUM = met with degraded quality; LOW = minor deviation
5. **Apply verdict rule**: if any CRITICAL or HIGH defect exists the verdict is FAILED; otherwise PASSED

## Expected Usage
Injected into the tester agent system prompt to produce a requirement-traceable
QA report with a machine-readable verdict the pipeline can act on.
