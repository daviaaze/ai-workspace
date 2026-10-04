---
name: feature-dev
description: Start and work through a feature or task end-to-end. Use when the user says implement, build, start a feature, work on a task, or references a ticket.
---

# Feature Development Workflow

## Phase 1: Deep Ticket Understanding

**Goal:** extract both explicit requirements and implicit context from the ticket
ecosystem before writing a single line of code.  A shallow ticket read is the #1
cause of rework.

### 1a. Surface — What the ticket says

If a Jira ticket number is available (e.g. `XTRNT-802`):

```bash
# Full ticket with all fields
jtk issues get XTRNT-802 --fulltext

# Priority, type, status, sprint, components, labels
jtk issues get XTRNT-802 -o json | jq '{key, summary, status, priority, type, components, labels}'
```

If no ticket key, ask the user for the task description and check what's in
`ai-workspace/Development/Features/` for feature notes.

### 1b. Linked context — What the ticket connects to

```bash
# Parent epic / child sub-tasks / blocks / is blocked by / related / duplicates
jtk links list XTRNT-802

# If there's a parent epic, read it for the bigger picture
jtk issues get <PARENT-EPIC> --fulltext

# Check for related/duplicate tickets in the same epic or project
jtk issues search --jql '"Epic Link" = XTRNT-XXX ORDER BY created DESC' --max 15
```

**Ask yourself:**
- What is the parent epic's goal?  How does this ticket move the needle?
- Are there sub-tasks that define the work breakdown?
- Are there blocking/blocked-by dependencies?  Who owns them?
- Has this been attempted before in a duplicate or related ticket?

### 1c. Conversation layer — What was discussed

```bash
# Read all comments (often contain decisions, clarifications, edge cases)
jtk comments list XTRNT-802 --fulltext

# Check attachments (designs, data, screenshots)
jtk attachments list XTRNT-802
```

**Pay attention to:**
- Comments that change or refine acceptance criteria
- Design decisions made in the thread
- Questions asked but never answered (these are landmines)
- Who commented — domain experts, PMs, tech leads

### 1d. Documentation layer — What's written elsewhere

```bash
# Search Confluence for related docs (team space, project space, runbooks)
cfl search "XTRNT-802" --type page
cfl search "<topic-keywords>" --type page

# Check workspace memory for relevant patterns and learnings
ls $WORKSPACE/memory/
cat $WORKSPACE/memory/project-patterns.md | rg -i "<keyword>"
cat $WORKSPACE/memory/learning-log.md | rg -i "<keyword>"

# Check runbooks for operational procedures that may relate
ls $WORKSPACE/Runbooks/
```

### 1e. Code layer — What already exists

```bash
# If the ticket mentions specific files/services, inspect them
# Otherwise, use PI graph tools to find relevant code
# (semantic_search_nodes, query_graph, get_impact_radius)

# Check for recent commits touching the same area
git log --oneline -20 -- <path>

# Check for open PRs that might conflict
gh pr list --search "<keyword>" --state open

# Check repo-local AGENTS.md for project-specific conventions
cat AGENTS.md 2>/dev/null
```

**Map the touchpoints:**
- Which repos/services does this ticket touch?  (Use team-conventions repo map)
- What existing patterns exist for similar features?  (project-patterns.md)
- Are there recent changes in the same area?  (risk of merge conflict)
- What's the deployment order if this crosses repos?  (contract → upstream → downstream)

### 1f. Implicit layer — What's not said but must be asked

After gathering all explicit context, surface the gaps.  These are questions the
ticket *should* have answered but didn't:

| Category | Questions |
|----------|-----------|
| **Cross-service** | Which services are consumers of this API/contract?  What downstream systems feel the impact? |
| **Auth/Permissions** | Does this need `isAdmin` gating?  Partner role restrictions?  Public vs. internal endpoints? |
| **Edge cases** | What happens with empty input?  Nulls?  Large payloads?  Concurrent requests?  Retries? |
| **Performance** | Is this on a hot path?  N+1 query risk?  Caching needed? |
| **Backward compatibility** | Does this break existing API contracts?  Old clients still calling old schema? |
| **Feature flags** | Should this be gated behind a flag for gradual rollout? |
| **Observability** | What metrics/alerts confirm correctness in production? |
| **Migration** | Does this need a data migration?  Schema change?  Backfill? |
| **Rollback** | Can we undo this?  What does rollback look like? |

**Raise any unanswered implicit questions with the user before moving on.**

### 1g. Synthesis

Produce a one-paragraph summary:

> **Ticket summary:** XTRNT-XXX — [one-line goal].  Touches [repos/services].
> Parent epic is [EPIC] which aims to [bigger-picture goal].  Key dependency:
> [blocked-by or blocks].  [N] areas need clarification: [list].

Then move to Phase 2.

## Phase 2: Review-Aware Design

**Goal:** size the risk and surface review constraints *before* writing code, so the
implementation is built to pass review on the first attempt.

1. **Risk self-assessment** — use `review-risk-framework` to classify the
   task (1-5), including automatic escalators, using the context gathered in
   Phase 1.

2. **Query plan check** — if this change introduces or modifies a database query
   on a customer-facing high-frequency API, a query plan review is mandatory.
   Flag this in the plan and verify during implementation.

3. **Quality dimension triage** — from the 12 quality dimensions, pick the 3–5 that
   matter most for this change:

   Correctness • Readability • Test Coverage • Error Handling • Performance •
   Security • Maintainability • Consistency • Documentation • Observability •
   Backward Compatibility • Edge Cases

4. **Performance awareness** — if this touches a customer-facing high-frequency
   API, performance must be at the front of mind.  Consider caching, N+1
   avoidance, and connection pooling.

5. **Cross-check with Phase 1 findings** — does the risk score change when you
   consider the linked context, conversation decisions, and code-layer complexity?

6. **State the expected risk score and key quality dimensions** before moving to
   Plan.  If the score is 4+, surface the risk explicitly and confirm the
   approach with the user.

7. **What would Claude flag?** — given the full Phase 1 picture, anticipate what
   the CI auto-review would catch (missing tests, unclear naming, missing error
   handling, undocumented assumptions).  Build those into the plan.

## Phase 3: Plan

- Use PI graph tools to analyze codebase: `semantic_search_nodes`, `query_graph`, `get_impact_radius`.
- Check relevant memory docs and project context.
- Break implementation into small, testable steps.
- Ask for approval before implementation when the plan is non-trivial.

## Phase 4: Implement

- One step at a time.
- **Business logic must live in the API.** When logic is required in the
  frontend, abstract it into testable models or components — and they must
  be accompanied by a test.
- **Refactors and features must be separate commits.** Do not bundle
  formatting/whitespace changes with logic changes.
- Run targeted tests after significant changes.

## Phase 5: Verify & Deliver

- Run final tests/lint/type-check as appropriate.
- Use `desloppify` for cleanup.
- **Review gate:** re-run the Phase 2 self-assessment. Did the actual change
  match the expected risk score? If it crept higher, flag it before PR.
- Use `pre-review` before PR — includes risk-scoring parity with the CI review.
- Use `commit` and `create-pr` when requested or confirmed.
