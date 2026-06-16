---
name: daily
description: Generate or update work daily stand-up notes from TODOs and current workspace context. Use when the user asks for daily, standup, end-of-day summary, or what was done today.
---

# Daily Stand-up Workflow

## Trigger
Daily, standup, end-of-day summary, what did I do today.

## Workflow

1. Read any relevant TODOs or notes for the current date.
2. Check workspace context — what was being worked on, recent PRs, open issues.
3. Generate a daily note with:
   - `## Yesterday`
   - `## Today`
   - `## Blockers`
   - `## Notes`
4. Keep it concise (≤50 lines) and link to TODOs for details.
5. Update TODOs if completed/carry-over status changed.
