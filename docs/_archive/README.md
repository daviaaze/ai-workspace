# Archived Documentation

These docs were written during v0.1 development. They've been superseded by the
specs in `docs/specs/` and the current implementation in `src/ai_workspace/`.

| Archived Doc | Superseded By |
|-------------|---------------|
| `BUDGET_ENFORCEMENT.md` | `core/cost.py` (unchanged) |
| `CONTEXT_AWARENESS.md` | `SPEC_CONTEXT_MANAGEMENT.md`, `SPEC_CONTEXT_COMPACTION.md` |
| `INTERACTIVE_SESSION.md` | `SPEC_AGENT_LOOP.md` (agent_loop async generator) |
| `MESSAGE_QUEUE.md` | `agents/loop.py` (event queue in agent_loop) |
| `MODEL_FALLBACK.md` | `agents/loop.py` (_resolve_stream_chat), `providers/__init__.py` |
| `PERMISSION_SYSTEM.md` | `agents/safety.py` (SafetySandbox) |
| `PLANO_AIW_V3_REALINHAMENTO.md` | `docs/specs/` (21 new specs) |
| `SEMANTIC_CACHE.md` | `core/cost.py` (SemanticCache) |
| `SKILL_SYSTEM.md` | pi-compatible skills system (unchanged) |
| `VISION_PIPELINE.md` | Not implemented yet |

**Kept active:**
- `docs/README.md` — project overview (updated)
- `docs/POSITIONING.md` — positioning & differentiation analysis
- `docs/specs/` — canonical specs (21 specs, all implemented)
