---
name: daily
description: Generate or update daily stand-up and end-of-day review notes from TODOs, Jira, PRs, lifecycle gates, blockers, deploys, and learnings. Use when the user asks for daily, standup, daily review, end-of-day summary, plan tomorrow, or what was done today.
---

# Daily Stand-up / Review Workflow

## Trigger

- "daily"
- "standup"
- "daily review"
- "end-of-day summary"
- "what did I do today?"
- "plan tomorrow"
- "update my daily"

## Purpose

Turn the live TODO board into a concise stand-up note and ensure important
state does not get lost overnight: blockers, PRs, deploy order, risk gates,
validation, and durable learnings.

## Source Files

- TODOs: `/home/daviaaze/Projects/pessoal/ai-workspace/TODOs/YYYY-MM-DD.md`
- Dailies: `/home/daviaaze/Projects/pessoal/ai-workspace/Dailies/YYYY-MM-DD.md`
- Memory/runbooks only when relevant.

## Modes

### Morning planning

Use `todo-review` first.

1. Read today's TODO.
2. If missing, create it from yesterday's unresolved carry-over.
3. Identify the top 1-3 focus lanes:
   - clear review lane first
   - unblock dependencies
   - active build lane
4. Surface blockers and required lifecycle gates.
5. Keep teammate-wide sprint data out unless explicitly requested.

### End-of-day review

1. Read today's TODO.
2. Reconcile completed vs carried-over work.
3. Check evidence when practical:
   - PRs created/merged
   - CI status
   - tests run
   - deploys
   - Jira transitions/comments
4. Capture:
   - done work
   - blockers
   - tomorrow's first action
   - risk/deploy/watch items
   - durable learnings
5. Generate or update `Dailies/YYYY-MM-DD.md`.

## Evidence Sources

Use targeted lookups only:

```bash
# Current repo PR state
gh pr view --json number,title,state,reviewDecision,statusCheckRollup,url

# My open PRs in current repo
gh pr list --author @me --state open

# Jira ticket details when referenced in TODO
jtk issues get XTRNT-123 --fulltext

# Jira assigned work only when planning/sprint status requested
jtk issues search --jql 'assignee = currentUser() AND status not in (Done, Closed) ORDER BY priority DESC, updated DESC'
```

Do not broadly scrape all team work unless asked.

## Daily Note Format

Keep the daily concise (usually ≤50 lines):

```markdown
# Daily — YYYY-MM-DD

## Yesterday
- Completed or materially progressed items.

## Today
- Top planned focus items.

## Blockers
- Blocker + owner/unblock path.

## Notes
- PRs/deploy order/watch items/risk context.
- Link to TODOs/YYYY-MM-DD.md for details.
```

## Daily Review Checklist

Before finalizing:

- [ ] TODO completed items reflected in `## Yesterday` / summary.
- [ ] Unfinished work has a next action.
- [ ] Blockers name owner or unblock path.
- [ ] Multi-repo work includes deploy order.
- [ ] High-risk work names relevant gates:
  - `validate-migration`
  - `security-review`
  - `external-api-review`
  - `observability`
  - `service-ownership`
- [ ] PRs in review are clearly called out.
- [ ] Deploy/watch items are called out.
- [ ] Durable lessons captured via `learn` when appropriate.

## Summary Style

Prefer outcome-oriented lines:

```markdown
- Merged svc-vendor PR #1266 after resolving dependency lockfile conflicts; CI green.
```

Avoid low-signal activity logs:

```markdown
- Looked at files and ran commands.
```

## Carry-over Rules

Carry an item forward only if:

- it is still actionable,
- it has a clear next step,
- it is not just historical detail.

When carrying over, compress details and link back to the previous TODO file.

## Integration

- Use `todo-review` to maintain the live TODO board.
- Use `lux-dev-lifecycle` for non-trivial ticket planning.
- Use `learn` for durable lessons.
- Use `jira` only for ticket/sprint state that matters to the daily.
