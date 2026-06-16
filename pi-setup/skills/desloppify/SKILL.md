---
name: desloppify
description: Clean up AI-generated code artifacts. Use after AI generates code, when the user says clean up, polish, or remove AI cruft.
---

# Desloppify Workflow

## Trigger
Clean up, polish, remove AI cruft, after AI-generated code.

## Workflow

1. **Remove dead code** — unused imports, dead paths, commented-out code.
2. **Remove redundant comments** — keep only WHY, not WHAT. Delete AI-generated summary comments.
3. **Remove unnecessary casts** — keep only when they add safety.
4. **Simplify expressions** — break nested ternaries, extract complex conditions, apply early returns.
5. **Standardize formatting** — run project's formatter. Consistent import ordering.
6. **Naming review** — meaningful names, match codebase conventions.
7. **Validate** — run tests and linter. Report what changed.

## Output
- Files modified
- Issue types fixed (counts)
- Any manual review items
