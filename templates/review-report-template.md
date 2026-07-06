---
name: review-report-template
version: 1.0.0
description: Reusable output structure for a code review report
used_by:
  - reviewer
---

## Structure
```
# Review Report: <product name>

## Executive Summary
| Severity | Count |
|----------|-------|
| CRITICAL |       |
| HIGH     |       |
| MEDIUM   |       |
| LOW      |       |

**Must resolve before approval** (CRITICAL + HIGH issues):
- <REV-#>: <one-line summary>

---

## 1. Functional Requirements Coverage
For each FR-# from requirements.md: Implemented / Partial / Missing, and notes.

| FR   | Status | Notes |
|------|--------|-------|

---

## 2. Non-Functional Requirements Coverage
For each NFR-# from requirements.md: Addressed / Partial / Missing, and evidence.

| NFR  | Category | Status | Evidence / Gap |
|------|----------|--------|----------------|

---

## 3. Architecture Compliance
Issues where the code deviates from solution-design.md decisions.

| ID    | Severity | Area | Issue | Recommendation |
|-------|----------|------|-------|----------------|

---

## 4. Code Quality
Issues with naming, structure, modularity, dead code, complexity.

| ID    | Severity | File | Issue | Recommendation |
|-------|----------|------|-------|----------------|

---

## 5. Security
Authentication, authorisation, input validation, secret handling, injection risks.

| ID    | Severity | File | Issue | Recommendation |
|-------|----------|------|-------|----------------|

---

## 6. Error Handling
Unhandled errors, wrong status codes, silent failures.

| ID    | Severity | File | Issue | Recommendation |
|-------|----------|------|-------|----------------|

---

## 7. Performance
Inefficient queries, blocking operations, missing caching, N+1 problems.

| ID    | Severity | File | Issue | Recommendation |
|-------|----------|------|-------|----------------|

---

## 8. Maintainability
Missing documentation, high cyclomatic complexity, poor test surface.

| ID    | Severity | File | Issue | Recommendation |
|-------|----------|------|-------|----------------|

---

**Verdict**: APPROVED | CHANGES REQUIRED
```
