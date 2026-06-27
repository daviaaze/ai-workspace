---
name: instagram-transcriber
description: Download Instagram Reels, transcribe speech with local Whisper, analyze with Ollama, and extract structured insights. Use when the user asks to transcribe an Instagram reel, extract audio from a reel, analyze a video, or summarize content from an Instagram link.
---

# Instagram Reel Transcriber

## Prerequisites

The following tools must be available (all from nixpkgs):

- `instaloader` — download reel video + caption metadata
- `whisper` (openai-whisper) — speech-to-text transcription
- `ffmpeg` — audio extraction from video
- `python3` with the `mcp` package (optional, for MCP mode)

They are pre-installed in this environment. If not found, run:

```bash
nix shell nixpkgs#instaloader nixpkgs#openai-whisper nixpkgs#ffmpeg-headless
```

## Available Tools

Two custom tools are registered by the pi extension at `.pi/extensions/instagram-transcriber.ts`:

### 1. `transcribe_instagram_reel`

**Description:** Download an Instagram Reel, transcribe speech with Whisper, and optionally analyze with Ollama.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | yes | — | Full Instagram Reel URL |
| `model` | string | no | `small` | Whisper model size: tiny/base/small/medium/large |
| `language` | string | no | auto | Spoken language code (en, pt, es…) |
| `analyze` | boolean | no | false | Analyze transcript with local Ollama model |
| `ollama_model` | string | no | `qwen3.5:9b` | Ollama model for analysis |
| `force` | boolean | no | false | Re-download even if cached |

**Returns:** Caption text, full transcript, audio duration, optional Ollama analysis.

### 2. `list_transcripts`

**Description:** List all cached Instagram Reel transcripts with metadata.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | no | 20 | Max results (1–100) |

**Returns:** JSON array with shortcode, URL, duration, transcript status, cache timestamp.

## Quick Start

### Transcribe a reel

Just ask pi:

> "Transcribe this reel: https://www.instagram.com/reel/C9hh6DKtYUb/"

Or use the CLI directly:

```bash
aiw-transcribe --url "https://www.instagram.com/reel/C9hh6DKtYUb/"
```

### Transcribe + analyze with Ollama

> "Transcribe and analyze this reel with Ollama: https://www.instagram.com/reel/C9hh6DKtYUb/"

Or:

```bash
aiw-transcribe --url "https://www.instagram.com/reel/C9hh6DKtYUb/" --analyze
```

### List cached transcripts

> "Show me my cached Instagram transcripts"

Or:

```bash
aiw-transcribe --list
```

### Full pipeline (step by step)

If you prefer to run the pipeline manually:

```bash
# 1. Download the reel
instaloader -- -f "reel/SHORTCODE"

# 2. Extract audio
ffmpeg -i *.mp4 -vn -ar 16000 -ac 1 audio.wav

# 3. Transcribe
whisper audio.wav --model small --output_dir transcript/
```

## Architecture

```
Instagram URL
     │
     ▼
instaloader ──► video.mp4 + metadata (caption, comments)
     │
     ▼
  ffmpeg ──► audio.wav (16kHz mono)
     │
     ▼
 whisper ──► transcript.txt
     │
     ▼ (optional)
  Ollama ──► structured analysis
     │
     ▼
  JSON result → cached in ~/.cache/aiw/instagram_transcripts/
```

## Caching

Transcripts are cached in `~/.cache/aiw/instagram_transcripts/{shortcode}.json`.
Subsequent calls with the same URL return instantly. Use `force: true` to re-download.

## MCP Server

The transcriber also runs as a standalone MCP server:

```bash
python -m ai_workspace.mcp_tools.instagram_transcriber --mcp
```

This exposes the same tools via the Model Context Protocol for use with any MCP client (Claude Code, Codex, etc.). The tools are also registered on the main aiw MCP server:

```bash
python -m ai_workspace.mcp_server
```

## Ollama Models Available

| Model | Best for |
|-------|----------|
| `qwen3.5:9b` | General summarization, extraction |
| `gemma3:12b` / `qwen3:14b` | Deeper analysis |
| `qwen2.5-coder:7b` | Extracting code/tech from developer reels |
| `deepseek-r1:14b` | Reasoning-heavy analysis |

## Troubleshooting

**"instaloader not found":**
```bash
nix shell nixpkgs#instaloader
```

**"whisper not found":**
```bash
nix shell nixpkgs#openai-whisper
```

**"ModuleNotFoundError: No module named 'mcp'":**
```bash
pip install mcp
```

**Instagram blocks the request:**
Instagram requires a logged-in session. Either:
1. Set `INSTAGRAM_SESSION_ID` environment variable, or
2. Use browser cookies with `instaloader --cookies cookies.txt`
