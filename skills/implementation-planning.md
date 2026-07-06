---
name: implementation-planning
version: 1.0.0
description: Techniques for breaking a technical design into sequenced, dependency-ordered tasks
used_by:
  - developer
---

## Capabilities
- Decompose components into modules with clear single responsibilities
- Identify task dependencies and express them explicitly so work is correctly sequenced
- Define folder structures that reflect the architecture's bounded contexts
- Write coding standards specific enough to eliminate common ambiguities at code-review time
- Sequence database migrations to respect foreign key constraints

## Instructions
When applying this skill, use these techniques:
- **Dependency-first sequencing**: identify which tasks have no dependencies (phase 1), then which depend only on phase-1 tasks (phase 2), and so on
- **One task per testable increment**: each DT-# task should result in something runnable and testable
- **Standards specificity test**: for each standard, ask "would two engineers independently make the same choice?" — if not, add specificity
- **Migration ordering rule**: tables with no FKs first; tables referencing already-created tables next
- **No orphan modules**: every module defined must appear in at least one DT-# task

## Expected Usage
Injected into the developer agent system prompt to improve the completeness
and sequencing of the implementation plan it produces for the Coder.
