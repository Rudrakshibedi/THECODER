---
name: solution-design-template
version: 1.0.0
description: Reusable output structure for a technical solution design document
used_by:
  - architect
---

## Structure
```
# Solution Design: <product name>

## 1. System Architecture
Architecture style, rationale, and ASCII component diagram.

## 2. Components
For each component: name, responsibility, FRs it satisfies.

## 3. Database Design
Entities/tables, key fields, relationships, chosen DB technology and why.

## 4. API Contracts
`METHOD /path` — purpose, request shape, response shape.

## 5. Technology Decisions
Each choice with one-line justification and main tradeoff.

## 6. Security Considerations
Auth/authz approach, data protection, NFR security mapping.

## 7. Scaling Considerations
Bottlenecks, scaling strategy, NFR performance/scalability mapping.
```
