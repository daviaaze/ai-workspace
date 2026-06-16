---
description: Plan a refactoring for a file or module
argument-hint: "<file-or-module>"
---

Plan a refactoring for: $1

Steps:
1. Read the target code
2. Identify the problems (complexity, duplication, poor naming, etc.)
3. Use `get_impact_radius` to understand blast radius
4. Propose a step-by-step refactoring plan
5. Estimate risk for each step
6. Suggest tests to add before refactoring

Output a refactoring plan with small, safe steps.
