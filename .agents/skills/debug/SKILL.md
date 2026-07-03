---
name: debug
description: Hypothesis-driven debugging. Use when tests are failing, there's a bug, the user says debug, find the bug, or something is not working as expected.
---

# Debug Workflow

## Trigger
Debug, find the bug, tests failing, something not working.

## Workflow

1. **Understand** — read errors and stack traces. Ask about expected vs actual behavior. Check recent commits.
2. **Assess impact** — what risk score would a fix for this bug likely carry? Is the affected code in a critical path (score 4-5) or isolated (score 1-2)? This helps prioritize and gauge the fix's blast radius.
3. **Hypothesize** — list 2-3 most likely causes, ranked by probability.
4. **Instrument** — add targeted logs at function entry/exit, state changes, external API calls, DB queries. Use structured JSON logging.
5. **Observe** — run failing scenario. Capture logs. Validate or invalidate hypotheses.
6. **Propose fix** — present root cause. Offer 2-3 options with trade-offs. State the expected risk score of each fix option.
7. **Apply and verify** — apply chosen fix. Run tests. Run original failing scenario.
8. **Clean up** — remove debug logs. Verify no performance impact.

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
