---
description: Generate tests for a file or function
argument-hint: "<file-or-function>"
---

Generate tests for: $1

Steps:
1. Read the target file to understand what it does
2. Identify the public API / exported functions
3. Write tests covering:
   - Happy path
   - Edge cases (null, empty, invalid input)
   - Error conditions
4. Follow existing test patterns in the project
5. Run tests to verify they pass

Output the test file content. Ask where to save it if unclear.
