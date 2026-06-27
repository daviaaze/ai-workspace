"""
Instagram Reel Transcriber — MCP Server + CLI

Exposes ``transcribe_instagram_reel`` as:
  - MCP tool  (for aiw, any MCP client)
  - CLI       (``python -m ai_workspace.mcp_tools.instagram_transcriber --url URL``)
  - Python    (``from ai_workspace.mcp_tools.instagram_transcriber import transcribe_reel``)

Workflow:
  1. instaloader — download reel video + caption metadata
  2. ffmpeg     — extract audio (16kHz mono WAV)
  3. whisper    — transcribe audio to text
  4. Ollama     — (optional) analyze transcript with local model

Requires:
  nix shell nixpkgs#instaloader nixpkgs#openai-whisper nixpkgs#ffmpeg-headless
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Try importing MCP — graceful fallback to CLI-only mode
try:
    from mcp.server.lowlevel import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

logger = logging.getLogger("aiw.instagram_transcriber")

# ── Config ────────────────────────────────────────────────────────────────────

CACHE_DIR = Path.home() / ".cache" / "aiw" / "instagram_transcripts"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_MODEL = "small"
DEFAULT_OLLAMA_MODEL = "qwen3.5:9b"
TEMP_BASE = Path(tempfile.gettempdir()) / "aiw-instagram"


# ── Core transcription logic ──────────────────────────────────────────────────

def _run(*args: str, timeout: int = 300, cwd: str | Path | None = None) -> str:
    """Run a shell command and return stdout."""
    result = subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(cwd) if cwd else None,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit {result.returncode}): {' '.join(args)}\n"
            f"stderr: {result.stderr[:500]}"
        )
    return result.stdout


def _run_shell(cmd: str, timeout: int = 300, cwd: str | Path | None = None) -> str:
    """Run a shell command string."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(cwd) if cwd else None,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit {result.returncode}): {cmd[:200]}\n"
            f"stderr: {result.stderr[:500]}"
        )
    return result.stdout


def _shortcode_from_url(url: str) -> str:
    """Extract the Instagram shortcode from a reel URL."""
    import re
    # https://www.instagram.com/reel/C9hh6DKtYUb/
    # https://www.instagram.com/reel/C9hh6DKtYUb/?igsh=...
    m = re.search(r"/reel/([A-Za-z0-9_-]+)", url)
    if m:
        return m.group(1)
    raise ValueError(f"Could not extract shortcode from URL: {url}")


def _cache_path(shortcode: str, suffix: str = ".json") -> Path:
    """Get cache path for a shortcode."""
    return CACHE_DIR / f"{shortcode}{suffix}"


async def transcribe_reel(
    url: str,
    model: str = DEFAULT_MODEL,
    language: str | None = None,
    force: bool = False,
    analyze: bool = False,
    ollama_model: str = DEFAULT_OLLAMA_MODEL,
    ollama_host: str = "http://localhost:11434",
    device: str = "cpu",
) -> dict[str, Any]:
    """Download and transcribe an Instagram Reel.

    Returns:
        dict with keys:
            url             — original URL
            shortcode       — Instagram shortcode
            caption         — post caption text
            transcript      — Whisper transcription
            language        — detected/spoken language
            duration_s      — audio duration in seconds
            model           — whisper model used
            analysis        — (optional) Ollama analysis
            cache_hit       — whether result was cached
            success         — bool
            error           — error message if failed
    """
    shortcode = _shortcode_from_url(url)
    cache_path = _cache_path(shortcode)

    # Check cache
    if not force and cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text())
            if cached.get("success"):
                logger.info(f"Cache hit for {shortcode}")
                cached["cache_hit"] = True
                return cached
        except (json.JSONDecodeError, OSError):
            pass

    result: dict[str, Any] = {
        "url": url,
        "shortcode": shortcode,
        "caption": "",
        "transcript": "",
        "language": "",
        "duration_s": 0,
        "model": model,
        "analysis": "",
        "cache_hit": False,
        "success": False,
        "error": "",
    }

    work_dir = TEMP_BASE / shortcode
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ── Step 1: Download reel via yt-dlp ──
        logger.info(f"Downloading reel {shortcode}...")
        video_path = work_dir / "video.mp4"
        _run(
            "yt-dlp",
            "--output", str(video_path),
            "--print", "title",
            "--print", "description",
            url,
            timeout=120,
        )

        # Extract caption from yt-dlp output (printed to stderr with --print)
        try:
            # Re-run just for metadata (yt-dlp prints title then description to stdout)
            meta = _run(
                "yt-dlp",
                "--print", "title",
                "--print", "description",
                "--skip-download",
                url,
                timeout=30,
            )
            lines = meta.strip().split("\n", 1)
            if lines:
                result["title"] = lines[0]
            if len(lines) > 1:
                result["caption"] = lines[1].strip()
        except Exception:
            pass

        if not video_path.exists():
            # yt-dlp might save with a different name
            found = list(work_dir.glob("*.mp4")) + list(work_dir.glob("*.webm"))
            if found:
                video_path = found[0]
            else:
                raise RuntimeError(f"No video file found in {work_dir}")

        # ── Step 2: Extract audio ──
        logger.info("Extracting audio...")
        audio_path = work_dir / "audio.wav"
        _run(
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-ar", "16000", "-ac", "1",
            "-sample_fmt", "s16",
            str(audio_path),
            "-loglevel", "error",
        )

        # Get duration
        dur_output = _run(
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        )
        result["duration_s"] = round(float(dur_output.strip()), 1)

        # ── Step 3: Transcribe with Whisper ──
        logger.info(f"Transcribing with whisper ({model})...")
        output_dir = work_dir / "whisper_out"
        output_dir.mkdir(exist_ok=True)

        whisper_cmd = [
            "whisper",
            str(audio_path),
            "--model", model,
            "--output_dir", str(output_dir),
            "--output_format", "txt",
            "--device", device,
        ]
        if language:
            whisper_cmd.extend(["--language", language])

        _run(*whisper_cmd, timeout=600)

        # Read transcript
        txt_files = list(output_dir.glob("*.txt"))
        if txt_files:
            result["transcript"] = txt_files[0].read_text().strip()
        else:
            # Try reading from audio file name pattern
            txt_files = list(output_dir.glob("audio*.txt"))
            if txt_files:
                result["transcript"] = txt_files[0].read_text().strip()
            else:
                result["transcript"] = "(transcription file not found)"

        # Detect language from whisper output
        vtt_files = list(output_dir.glob("*.vtt"))
        if vtt_files:
            # Kinda hacky — whisper prints "Detected language: X" to stderr
            pass

        # ── Step 4: Optional Ollama analysis ──
        if analyze and result["transcript"]:
            logger.info(f"Analyzing with ollama ({ollama_model})...")
            analysis = await _ollama_analyze(
                transcript=result["transcript"],
                caption=result.get("caption", ""),
                model=ollama_model,
                host=ollama_host,
            )
            result["analysis"] = analysis

        result["success"] = True

        # ── Cache ──
        cache_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        logger.exception("Transcription failed")
        result["error"] = str(e)
        result["success"] = False

    finally:
        # Cleanup work dir
        import shutil
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)

    return result


def _list_transcripts_cli(args: argparse.Namespace) -> None:
    """List cached transcripts."""
    limit = getattr(args, "limit", 20)
    results = []
    for f in sorted(CACHE_DIR.glob("*.json"), reverse=True)[:limit]:
        try:
            data = json.loads(f.read_text())
            results.append({
                "shortcode": data.get("shortcode", f.stem),
                "url": data.get("url", ""),
                "duration_s": data.get("duration_s", 0),
                "success": data.get("success", False),
                "has_transcript": bool(data.get("transcript")),
                "has_caption": bool(data.get("caption")),
                "cached_at": datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
            })
        except Exception:
            continue

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    if not results:
        print("No cached transcripts found.")
        return

    print(f"{'Shortcode':<15} {'Duration':<10} {'Transcript':<12} {'Cached At'}")
    print("-" * 60)
    for r in results:
        t = "✓" if r["has_transcript"] else "✗"
        print(f"{r['shortcode']:<15} {r['duration_s']:<10} {t:<12} {r['cached_at'][:19]}")


async def _ollama_analyze(
    transcript: str,
    caption: str,
    model: str = DEFAULT_OLLAMA_MODEL,
    host: str = "http://localhost:11434",
) -> str:
    """Send transcript to Ollama for summarization + extraction."""
    import httpx

    prompt = (
        "You are an assistant that analyzes Instagram Reel transcripts. "
        "Given the transcript and caption below, produce a structured analysis:\n\n"
        "## SUMMARY\n(2-3 sentence summary of the reel content)\n\n"
        "## KEY POINTS\n- Bullet list of main points mentioned\n\n"
        "## TOPICS & TAGS\n- Topics discussed\n- Relevant technical concepts\n\n"
        "## ACTIONABLE TAKEAWAYS\n- Any advice, recommendations, or next steps\n\n"
        "---\n"
        f"## TRANSCRIPT\n{transcript[:8000]}\n\n"
        f"## POST CAPTION\n{caption[:2000]}\n"
    )

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{host}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
    except Exception as e:
        return f"(Ollama analysis failed: {e})"


# ── CLI entry point ───────────────────────────────────────────────────────────

def main_cli() -> None:
    """CLI entry: python -m ai_workspace.mcp_tools.instagram_transcriber ..."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Instagram Reel Transcriber — download + transcribe + analyze",
    )
    parser.add_argument("--url", help="Instagram Reel URL")
    parser.add_argument("--list", action="store_true", help="List cached transcripts")
    parser.add_argument("--limit", type=int, default=20, help="Max results for --list (default: 20)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Whisper model size (tiny/base/small/medium/large)")
    parser.add_argument("--language", help="Spoken language (auto-detect if omitted)")
    parser.add_argument("--force", action="store_true", help="Re-download + re-transcribe (ignore cache)")
    parser.add_argument("--analyze", action="store_true", help="Analyze transcript with Ollama")
    parser.add_argument("--ollama-model", default=DEFAULT_OLLAMA_MODEL, help="Ollama model for analysis")
    parser.add_argument("--ollama-host", default="http://localhost:11434", help="Ollama API host")
    parser.add_argument("--device", default="cpu", help="Whisper device (cpu/cuda)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--mcp", action="store_true", help="Run as MCP server over stdio")

    args = parser.parse_args()

    if args.mcp:
        asyncio.run(run_mcp_stdio())
        return

    if args.list:
        _list_transcripts_cli(args)
        return

    if not args.url:
        parser.error("--url or --list is required")

    result = asyncio.run(transcribe_reel(
        url=args.url,
        model=args.model,
        language=args.language,
        force=args.force,
        analyze=args.analyze,
        ollama_model=args.ollama_model,
        ollama_host=args.ollama_host,
        device=args.device,
    ))

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Pretty print
    print(f"\n{'='*60}")
    print(f" Instagram Reel: {result['shortcode']}")
    print(f"{'='*60}")
    print(f" URL:      {result['url']}")
    print(f" Duration: {result.get('duration_s', '?')}s")
    print(f" Success:  {'✓' if result['success'] else '✗'}")
    if result.get("cache_hit"):
        print(" (cached)")
    if result.get("error"):
        print(f" Error:    {result['error']}")

    print(f"\n── Caption ──\n{result.get('caption', '(none)')}")

    print(f"\n── Transcript ──\n{result.get('transcript', '(none)')}")

    if result.get("analysis"):
        print(f"\n── Ollama Analysis ──\n{result['analysis']}")

    # Also save to a readable output file
    out_file = CACHE_DIR / f"{result['shortcode']}.txt"
    with open(out_file, "w") as f:
        f.write(f"URL: {result['url']}\n")
        f.write(f"Duration: {result.get('duration_s', '?')}s\n\n")
        f.write(f"=== Caption ===\n{result.get('caption', '(none)')}\n\n")
        f.write(f"=== Transcript ===\n{result.get('transcript', '(none)')}\n")
        if result.get("analysis"):
            f.write(f"\n=== Ollama Analysis ===\n{result['analysis']}\n")
    print(f"\nSaved to: {out_file}")


# ── MCP Server ────────────────────────────────────────────────────────────────

if HAS_MCP:

    mcp_server = Server("instagram-transcriber")

    @mcp_server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="transcribe_instagram_reel",
                description="Download an Instagram Reel, transcribe speech with Whisper, and optionally analyze with Ollama. "
                            "Returns caption text, full transcript, duration, and optional AI analysis.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Full Instagram Reel URL (e.g. https://www.instagram.com/reel/C9hh6DKtYUb/)",
                        },
                        "model": {
                            "type": "string",
                            "description": "Whisper model size: tiny, base, small, medium, large",
                            "default": "small",
                        },
                        "language": {
                            "type": "string",
                            "description": "Optional language code (en, pt, es, etc.). Auto-detected if omitted.",
                        },
                        "analyze": {
                            "type": "boolean",
                            "description": "Analyze transcript with local Ollama model",
                            "default": False,
                        },
                        "ollama_model": {
                            "type": "string",
                            "description": "Ollama model for analysis (default: qwen3.5:9b)",
                            "default": DEFAULT_OLLAMA_MODEL,
                        },
                        "ollama_host": {
                            "type": "string",
                            "description": "Ollama API base URL",
                            "default": "http://localhost:11434",
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Re-download and re-transcribe even if cached",
                            "default": False,
                        },
                    },
                    "required": ["url"],
                },
            ),
            Tool(
                name="list_transcripts",
                description="List all cached Instagram Reel transcripts with metadata.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Max results (default 20)",
                            "default": 20,
                        },
                    },
                },
            ),
        ]

    @mcp_server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "transcribe_instagram_reel":
            url = arguments.get("url", "")
            if not url:
                return [TextContent(type="text", text="Error: url is required")]

            result = await transcribe_reel(
                url=url,
                model=arguments.get("model", DEFAULT_MODEL),
                language=arguments.get("language"),
                force=arguments.get("force", False),
                analyze=arguments.get("analyze", False),
                ollama_model=arguments.get("ollama_model", DEFAULT_OLLAMA_MODEL),
                ollama_host=arguments.get("ollama_host", "http://localhost:11434"),
            )

            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "list_transcripts":
            limit = arguments.get("limit", 20)
            results = []
            for f in sorted(CACHE_DIR.glob("*.json"), reverse=True)[:limit]:
                try:
                    data = json.loads(f.read_text())
                    results.append({
                        "shortcode": data.get("shortcode", f.stem),
                        "url": data.get("url", ""),
                        "duration_s": data.get("duration_s", 0),
                        "success": data.get("success", False),
                        "has_transcript": bool(data.get("transcript")),
                        "cached_at": datetime.fromtimestamp(
                            f.stat().st_mtime, tz=timezone.utc
                        ).isoformat(),
                    })
                except Exception:
                    continue

            return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    async def run_mcp_stdio() -> None:
        """Run the MCP server over stdio."""
        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

else:
    async def run_mcp_stdio() -> None:
        print("MCP package not installed. Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)


# ── Entry points ──────────────────────────────────────────────────────────────

def main() -> None:
    """Console_scripts entry point: ``aiw-transcribe``."""
    main_cli()


if __name__ == "__main__":
    main_cli()
