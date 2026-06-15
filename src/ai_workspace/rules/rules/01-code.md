---
tags: [code]
always_apply: false
---

# Rule: Code Quality

Apply when editing: `.ts`, `.js`, `.tsx`, `.jsx`, `.py`, `.rs`, `.go`, `.java`, `.rb`, `.php` or in `src/`, `lib/`, `app/`, `api/`, `services/`, `handlers/`, `pkg/`, `internal/`

## Architecture
- Respect layers: Controllers/Handlers → Business Logic → Data Access. Never bypass.
- Prefer dependency injection. Follow existing DI patterns.

## Validation
- Validate at the boundary. Never trust external input.
- Use the project's validation schemas. Reuse, don't redefine.

## Error Handling
- Domain-specific errors. Never swallow exceptions without logging.
- Return appropriate status codes. Include error context for debugging.

## Logging
- Structured logging (JSON). Include correlation IDs for tracing.
- Log at appropriate levels: debug, info, warn, error.

## Testing
- Every new feature needs tests. Follow existing patterns (unit, integration, e2e).
- Mock external dependencies. Verify before and after refactors.
