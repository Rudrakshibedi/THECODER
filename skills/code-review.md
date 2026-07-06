---
name: code-review
version: 1.0.0
description: Structured approach to reviewing code against requirements, architecture, and quality standards
used_by:
  - reviewer
---

## Capabilities
- Map source code to FR-# requirements and identify gaps
- Identify security vulnerabilities: injection, broken auth, sensitive data exposure, misconfiguration
- Identify error handling gaps: unhandled exceptions, wrong status codes, silent failures
- Assess code quality: naming, complexity, duplication, separation of concerns
- Evaluate NFR compliance through code evidence

## Instructions
When applying this skill, follow this review sequence in order:
1. **Requirements pass**: for every FR-# and NFR-# in requirements.md, find the implementing code or mark as missing/partial
2. **Security pass**: check every external input for validation; check every protected endpoint for auth enforcement; search for hardcoded secrets
3. **Error handling pass**: check every function for unhandled exceptions; verify every API handler returns correct error status codes
4. **Quality pass**: flag functions over 50 lines, files over 300 lines, magic numbers, and deeply nested conditionals
5. **Architecture pass**: verify code matches the layered structure from solution-design.md; flag any layer violations
- Severity CRITICAL: data loss, security breach, or complete feature failure
- Severity HIGH: NFR violation or significant functional degradation
- Severity MEDIUM: quality issue that increases maintenance burden
- Severity LOW: style or minor improvement

## Expected Usage
Injected into the reviewer agent system prompt to ensure systematic,
requirement-traceable review coverage.
