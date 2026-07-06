---
name: documentation-template
version: 1.0.0
description: Reusable output structure for a technical documentation deliverable (README, API reference, ADRs, runbook)
used_by: []
---

## Structure
```
# Documentation: <product name>

## 1. Overview
What the system does, who it is for, and how this document is organised.

## 2. Installation
Prerequisites and step-by-step setup instructions.

## 3. Configuration
Environment variables, config files, and default values.

## 4. Running Locally
Commands to start the system and verify it is running.

## 5. Running Tests
Commands to run the test suite and interpret results.

## 6. API Reference
Per endpoint: `METHOD /path`, auth requirements, request schema, response
schema, error codes, and at least one example.

## 7. Architecture Decision Records
| ID | Context | Decision | Status | Consequences |
|----|---------|----------|--------|---------------|

## 8. Deployment
Deployment steps and environments.

## 9. Operational Runbook
Preconditions, numbered procedure, expected outcome, rollback procedure,
troubleshooting.

## 10. Contributing
How to propose changes and the review process.
```
