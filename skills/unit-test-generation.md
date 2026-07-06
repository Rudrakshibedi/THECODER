---
name: unit-test-generation
version: 1.0.0
description: Patterns for generating complete, runnable unit test suites
used_by:
  - tester
---

## Capabilities
- Generate test files for every source module using the stack-appropriate framework
- Write AAA-structured tests covering happy paths, error paths, and edge cases
- Mock external dependencies correctly without mocking the unit under test
- Generate parameterised tests for boundary value analysis
- Achieve meaningful coverage without redundant tests

## Instructions
When applying this skill, follow these patterns:
- **Framework selection**: Jest/Vitest for TypeScript/JavaScript, pytest for Python, JUnit+Mockito for Java, Go test for Go
- **AAA structure**: every test: Arrange (set up data/mocks) → Act (call the unit) → Assert (verify outcome)
- **One behaviour per test**: each test verifies exactly one logical outcome; separate tests for separate behaviours
- **Mock at the boundary**: mock external I/O (DB, HTTP, filesystem) but never mock the function being tested
- **Boundary values**: for numeric inputs always test zero, one, minimum, maximum, minimum-1, maximum+1
- **Error path coverage**: for every function that can fail, write at least one test that triggers the failure and verifies the error response
- **Test isolation**: every test must be runnable independently with no shared mutable state between tests

## Expected Usage
Injected into the tester agent system prompt to ensure generated unit tests
are complete, runnable, and follow professional testing conventions.
