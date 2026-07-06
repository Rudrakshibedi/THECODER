---
name: requirements-analysis
version: 1.0.0
description: Structured techniques for extracting, organising, and validating product requirements
used_by:
  - product-manager
---

## Capabilities
- Decompose a vague product idea into atomic functional requirements
- Identify implicit NFRs from the problem domain (e.g. fintech implies compliance; consumer app implies accessibility)
- Write Given/When/Then acceptance criteria that are directly testable
- Spot scope creep and out-of-scope items early
- Map requirements to user personas and business goals

## Instructions
When applying this skill, use these techniques:
- **MoSCoW prioritisation**: tag each FR as Must/Should/Could/Won't
- **5 Whys**: for each stated need, ask why five times to reach the root goal
- **NFR completeness check**: before finishing, verify all 15 NFR categories are addressed with measurable targets
- **Traceability rule**: every FR must trace to at least one user story
- **Ambiguity scan**: flag any requirement containing vague words like "fast", "easy", "scalable" and replace with measurable targets (e.g. "p95 response time under 300ms at 1000 concurrent users")

## Expected Usage
Injected into the product-manager agent system prompt to improve completeness
and testability of the requirements document it produces.
