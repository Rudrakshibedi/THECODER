---
name: system-design
version: 1.0.0
description: Principles and patterns for translating requirements into production architecture
used_by:
  - architect
---

## Capabilities
- Select architecture style based on NFRs (monolith vs microservices vs event-driven)
- Design normalised database schemas with correct FK constraints and indexing strategy
- Define RESTful or GraphQL API contracts with request/response shapes and status codes
- Identify security boundaries and apply defence-in-depth patterns
- Map every NFR to a specific architectural mechanism

## Instructions
When applying this skill, use these techniques:
- **NFR-to-architecture mapping**: for every NFR-#, name the specific architectural mechanism that satisfies it
- **API-first design**: define all endpoints before deciding on implementation technology
- **Failure mode analysis**: for each component, specify what happens when it fails and how the system recovers
- **Single source of truth**: every piece of data has exactly one authoritative owner service or table
- **Security at the design stage**: identify authentication boundaries, authorisation rules, and encryption requirements before implementation begins

## Expected Usage
Injected into the architect agent system prompt to ensure the solution design
addresses all requirements with specific, implementable architectural decisions.
