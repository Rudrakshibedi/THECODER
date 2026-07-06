---
name: test-strategy-template
version: 1.0.0
description: Reusable output structure for a test strategy document plus its accompanying unit test code
used_by:
  - tester
---

## Structure
```
# Test Strategy: <product name>

## 1. Testing Approach
Philosophy, pyramid proportions, tools, and mapping to NFRs.

## 2. Unit Test Cases
Grouped by module. ID (UT-#), what is tested, input, expected outcome.

## 3. Integration Tests
Grouped by component interaction. ID (IT-#), components, scenario, outcome.

## 4. API Tests
Grouped by endpoint. ID (AT-#), endpoint, scenario, expected response/status.

## 5. Edge Cases
ID (EC-#), boundary or failure scenario, expected system behavior.

## 6. Security Tests
ID (ST-#), what is verified, expected outcome. Map to NFR security items.

## 7. Performance Tests
ID (PT-#), what is measured, target threshold, test method.

---

# Unit Tests: <product name>

### <tests/path/to/module.test.ext>
```<language>
<complete runnable test code>
```

### <tests/path/to/next.test.ext>
```<language>
<complete runnable test code>
```
```
