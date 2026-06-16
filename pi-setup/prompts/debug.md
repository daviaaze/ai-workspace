---
description: Hypothesis-driven debugging workflow
argument-hint: "<bug-description>"
---

Debug the following issue: $1

Follow a hypothesis-driven workflow:

1. **Observe** — What exactly is happening? What should happen instead?
2. **Reproduce** — Find the smallest reliable failing scenario.
3. **Hypothesize** — List 2-3 likely root causes, ranked by probability.
4. **Isolate** — For each hypothesis, choose the smallest check that confirms/rules it out.
5. **Inspect evidence** — Logs, traces, failing test output, recent diffs, relevant graph context.
6. **Fix** — Minimal change for the confirmed root cause.
7. **Confirm** — Re-run the original failing scenario and relevant regression tests.

Do not rewrite working components; trace the data flow first.
