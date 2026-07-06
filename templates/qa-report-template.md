---
name: qa-report-template
version: 1.0.0
description: Reusable output structure for a QA validation report
used_by:
  - tester
---

## Structure
```
# QA Report: <product name>

## Requirements Validation
| ID    | Type | Description | Status | Notes |
|-------|------|-------------|--------|-------|
| FR-1  | FR   |             | PASS   |       |
| NFR-1 | NFR  |             | PASS   |       |

## Defects Found
| ID   | Severity | Module | Description | Linked Requirement |
|------|----------|--------|-------------|-------------------|

## Summary
- Total requirements validated: N
- PASS: N
- FAIL: N
- NOT TESTABLE: N

**QA Verdict**: PASSED | FAILED
```
