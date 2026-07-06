---
name: implementation-plan-template
version: 1.0.0
description: Reusable output structure for an engineering implementation plan
used_by:
  - developer
---

## Structure
```
# Implementation Plan: <product name>

## 1. Folder Structure
ASCII directory tree with one-line purpose per folder.

## 2. Modules
For each module: name, responsibility, component it implements, key dependencies.

## 3. Development Tasks
Numbered DT-# tasks grouped by phase (Foundation / Core / Integration / Hardening).
Each task: what to build, which module, which prior tasks it depends on.

## 4. API Implementation Plan
Per endpoint: build order, dependencies, validation rules, error cases.

## 5. Database Implementation Steps
Ordered migration steps respecting FK dependencies, indexing strategy, seed data.

## 6. Coding Standards
Naming, file organisation, error handling, logging, testing expectations, PR conventions.
```
