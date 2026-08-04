---
date: 2026-04-07
tags: [ollama, local-llm, hardware, benchmark]
---

# Ollama Model Review — daviaaze desktop

## Machine capabilities
- **CPU:** AMD Ryzen 9 7900X (6 cores allocated)
- **RAM:** 30 GB
- **GPU:** Radeon RX 6700 XT (Navi 22), **12 GB VRAM**, ROCm working — models ≤ ~9 GB Q4 run fully on GPU
- **Disk:** 932 GB NVMe

## Cleanup (2026-04-07)
Removed 16 models, freed **~104 GB** (315 → 419 GB free):
- Duplicates: `ornith-1.0-9b` (same blob as hf.co Ornith), `llama3.1:latest` (= `llama3.1:8b`)
- 12-month-old: `llama3`, `llama3.1:8b`, `deepseek-r1:14b`, `qwen2.5-coder:7b`, `qwen2.5-coder:1.5b-base`, `nomic-embed-text`
- Oversized/stale: `qwen3-coder:30b` (18 GB, can't fit VRAM), `gpt-oss:20b` (13 GB), `gemma3:12b`, `gemma4:e4b`, `qwen3:14b`, `qwen3-vl:8b`, `maryasov/qwen2.5-coder-cline` (14b + latest)
- Failed evals after pull: `qwen2.5-coder:14b` (broken TTL-cache code, arithmetic errors)

## Benchmarks (ROCm, temp 0.2, 220 max tokens)

| Model | tok/s | Riddle (ans: 27) | TTL-cache code | Notes |
|---|---|---|---|---|
| **ministral-3:8b** | ~40 | ✗ (self-corrected to 24) | ✅ clean, thread-safe, minor missing import | Direct answers, fast |
| ministral-3:14b | ~27 | ✗ (24) | ✅ slightly better structure | 32% slower for marginal gain |
| **qwen3.5:9b** | ~38–40 | ✓ (in thinking) / ✗ with think:off | needs budget | Thinking model — returns **empty** if num_predict too small |
| DeepSeek-R1-Qwen3-8B (Q4_K_M) | ~44 | ✅ correct, clean chain | needs budget | Thinking model, fastest tok/s |
| qwen2.5-coder:14b (tested, removed) | ~26 | ✗ (25, arithmetic error) | ✗ broken logic | Not worth keeping |

## Round-2: online research (2026-04-07)

Sources: ollama.com library, HuggingFace trending (likes7d/downloads). Reddit blocked from this network.

**Findings:**
- Newest-gen flagships (Qwen3.6-27B 17GB, Qwen3.6-35B-A3B ~20GB, GLM-4.7-flash 19GB, qwen3-coder-next 52GB, devstral-small-2 24B) all **exceed 12GB VRAM** — CPU offload kills them for daily use on this box.
- Community "Qwen3.6-14B-A3B" GGUFs (FableVibes/VibeForged) are fiction/RP tunes, not official — skipped.
- Viable new-gen candidates pulled & tested: **granite4.1:8b** (IBM, hybrid arch) and **Nemotron-3-Nano-4B** (NVIDIA, 2.8GB).
- `qwen2.5-coder:14b` retested and rejected (broken code, arithmetic errors) — coding is now well covered by general models.

## Round-2: rigorous evals (executable code tests + deterministic checks)

Tests: fizzbuzz-variant (executed), TTL-cache decorator (executed, thread-safety+expiry), sheep riddle (ans 27), avg-speed math (ans 100), exact 3×5-word bullet format, summary keyword retention.

| Model | Score | tok/s | Latency | FizzBuzz | TTL cache | Riddle | Math | Format | Summary |
|---|---|---|---|---|---|---|---|---|---|
| **granite4.1:8b** | **5/6** | 41.2 | 2.0s | ✅ | ✅ | ✅ | ✅ | ✗ | ✅ |
| **qwen3.5:9b** | **5/6** | 40.9 | 2.0s | ✅ | ✅ | ✅ | ✅ | ✗ | ✅ |
| ministral-3:8b | 4/6 | 40.6 | 2.0s | ✗ (strs not ints) | ✅ | ✅ | ✅ | ✗ | ✅ |
| nemotron-3-nano-4b | 4/6 | **74.7** | **1.3s** | ✅ | ✗ (NoneType bug) | ✅ | ✅ | ✗ | ✅ |
| ministral-3:14b | 4/6 | 27.8 | 2.7s | — | — | — | — | — | — |
| DeepSeek-R1-8B | 2/6* | 44.6 | 2.0s | ✗ | ✗ | ✗ | ✗ | ✅ | ✅ |

\* R1's low score is partly harness friction: thinking tokens eat budgets and code lands outside fenced blocks. Real capability is higher, but for **day-to-day** use the friction is real.
All models failed the exact word-count format test except R1 — word counting is a known LLM weakness, treat as a wash.

## Final recommendation — sweet spot

1. **Daily driver: `granite4.1:8b`** — 5/6, 41 tok/s, non-thinking, passed both executable code tests, clean instruction following.
2. **Alternate: `qwen3.5:9b`** — also 5/6; use with `think:false` for speed or big budgets for hard problems. Keep as pi skill default.
3. **Speed demon: `hf.co/unsloth/NVIDIA-Nemotron-3-Nano-4B-GGUF:Q4_K_M`** — 75 tok/s, 2.8GB; ideal for quick summaries, classification, high-throughput batch jobs.
4. **Deep reasoning only: DeepSeek-R1-8B** — when you need long chains and can afford the latency + parsing hassle.
5. **Embeddings: `batiai/qwen3-embedding:8b`** (official `qwen3-embedding:8b` also exists on ollama registry).

## Round-3: additional candidates (2026-04-07)

| Model | Result |
|---|---|
| phi4-mini:3.8b | 1/6, 78 tok/s — fast but too weak; removed |
| phi4:14b (9.1GB) | **crashes on load** — llama.cpp `graph_reserve` ggml fatal error on ROCm/ollama 0.32.1, even with num_ctx=4096; removed |
| Nanbeige4.2-3B | **unsupported** — `unknown model architecture: 'nanbeige'` on ollama 0.32.1; removed |

➡️ **Action item: upgrade ollama** (nixpkg 0.32.1 is behind). Newer ollama would unlock phi4 and Nanbeige4.2 families. Revisit after upgrade.

## Key learnings
- **Thinking models return empty responses via `/api/generate` with small `num_predict`** — thinking tokens consume the budget invisibly. Use `/api/chat` + `think` param or generous budgets.
- The 8–9B Q4 class all saturate ~40–44 tok/s on the 6700 XT; 14B drops to ~27 tok/s. **9B is the VRAM sweet spot**; quality jump to 14B doesn't justify the 32% speed loss.
- Niche models kept (not evaluated): `llama-open-finance`, `sematre/orpheus:en` (TTS), `QyrouNnet/summarizer:400m`, `llava:13b` (vision), `ministral-3:14b`, hf.co Ornith-1.0-9B. Revisit next cleanup.
