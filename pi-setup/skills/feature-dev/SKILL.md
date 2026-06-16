---
name: feature-dev
description: Start and work through a feature or task end-to-end. Use when the user says implement, build, start a feature, work on a task, or references a ticket.
---

# Feature Development Workflow

## Phase 1: Understand

- Read the ticket/task description.
- Ask clarifying questions on acceptance criteria, edge cases, and dependencies.
- State understanding before proceeding.

## Phase 2: Plan

- Use PI graph tools to analyze codebase: `semantic_search_nodes`, `query_graph`, `get_impact_radius`.
- Check relevant memory docs and project context.
- Break implementation into small, testable steps.
- Ask for approval before implementation when the plan is non-trivial.

## Phase 3: Implement

- One step at a time.
- Run targeted tests after significant changes.

## Phase 4: Verify & Deliver

- Run final tests/lint/type-check as appropriate.
- Use `desloppify` for cleanup.
- Use `pre-review` before PR.
- Use `commit` and `create-pr` when requested or confirmed.
