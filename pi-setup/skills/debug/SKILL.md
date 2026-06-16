---
name: debug
description: Hypothesis-driven debugging. Use when tests are failing, there's a bug, the user says debug, find the bug, or something is not working as expected.
---

# Debug Workflow

## Trigger
Debug, find the bug, tests failing, something not working.

## Workflow

1. **Understand** — read errors and stack traces. Ask about expected vs actual behavior. Check recent commits.
2. **Hypothesize** — list 2-3 most likely causes, ranked by probability.
3. **Instrument** — add targeted logs at function entry/exit, state changes, external API calls, DB queries. Use structured JSON logging.
4. **Observe** — run failing scenario. Capture logs. Validate or invalidate hypotheses.
5. **Propose fix** — present root cause. Offer 2-3 options with trade-offs. Recommend best.
6. **Apply and verify** — apply chosen fix. Run tests. Run original failing scenario.
7. **Clean up** — remove debug logs. Verify no performance impact.

## General Debugging Rules
- Reproduce consistently before fixing.
- Change one thing at a time.
- Verify the fix with the original failing scenario.

## Language-Specific Tips
- **TypeScript/Node**: `console.log(JSON.stringify(state, null, 2))`, `--inspect` + Chrome DevTools
- **Python**: `breakpoint()`, `python -m pdb`
- **Go**: `dlv debug`, `log.Printf("%+v", struct)`
- **Rust**: `dbg!(&value)`, `RUST_LOG=debug`
- **Database**: enable query logging, EXPLAIN for slow queries
