---
name: debug
description: Hypothesis-driven, root-cause-first debugging. Use when tests are failing, there's a bug, the user says debug, find the bug, or something is not working as expected.
---

# Debug Workflow

## Trigger
Debug, find the bug, tests failing, something not working, unexpected behavior, build/CI failures.

## Iron Law
**No fixes without root-cause investigation first.** Symptom patches mask the real issue and create new bugs. Under time pressure this matters most — systematic is faster than guess-and-check thrashing.

## Workflow

1. **Understand** — read errors and stack traces completely (line numbers, codes). Reproduce consistently. Check recent commits (`git diff`, recent changes). Expected vs actual behavior.
2. **Assess impact** — what risk score would a fix carry? Critical path (4-5) or isolated (1-2)? Prioritize accordingly.
3. **Gather evidence** — in multi-component systems, log at each component boundary (what enters/exits) before guessing which layer fails.
4. **Trace data flow** — for deep errors, trace the bad value backward to its origin. Fix at the source, not the symptom.
5. **Hypothesize** — list 2-3 most likely causes, ranked by probability. State: "I think X is the root cause because Y."
6. **Instrument** — add targeted structured logs at function entry/exit, state changes, external API calls, DB queries.
7. **Observe** — run the failing scenario. Validate or invalidate hypotheses one at a time. Don't stack fixes.
8. **Propose fix** — present root cause. Offer 2-3 options with trade-offs and expected risk score of each.
9. **Apply and verify** — smallest possible change to test the hypothesis. Create a failing test first when feasible. Apply fix, run tests, run the original failing scenario.
10. **Clean up** — remove debug logs. Verify no performance impact. Commit single-concern.

## When Fixes Keep Failing

- **< 3 attempts:** return to Phase 1 with new evidence. Don't attempt fix #4 reflexively.
- **≥ 3 failed fixes:** STOP. Each fix revealing a new problem in a different place signals an architectural issue, not a missed hypothesis. Question the design with the user before continuing.

## Red Flags (STOP and return to investigation)
- "Quick fix for now, investigate later"
- Proposing solutions before tracing data flow
- "One more fix attempt" after 2+ failures
- Each fix creates a new symptom elsewhere
- Adding multiple changes at once to "save time"

## General Rules
- Reproduce consistently before fixing.
- Change one thing at a time.
- Verify with the original failing scenario.
- If investigation reveals the issue is truly environmental/timing/external: document, add retry/timeout/monitoring, move on. But 95% of "no root cause" is incomplete investigation.

## Language-Specific Tips
- **TypeScript/Node**: `console.log(JSON.stringify(state, null, 2))`, `--inspect` + Chrome DevTools
- **Python**: `breakpoint()`, `python -m pdb`
- **Go**: `dlv debug`, `log.Printf("%+v", struct)`
- **Rust**: `dbg!(&value)`, `RUST_LOG=debug`
- **Database**: enable query logging, `EXPLAIN` for slow queries

> Merged from the former `systematic-debugging` skill. Supporting techniques (root-cause-tracing, condition-based-waiting, find-polluter) removed as separate files; essentials are inline above.