# Recursive Learning Skill — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a skill that mines past PI session logs for code structure, discoveries, constraints, and behavioral optimizations, persists findings to workspace memory, and recursively improves its own extraction heuristics.

**Architecture:** A Python CLI (`analyze_sessions.py`) deterministically parses JSONL session files, scores them for learning potential, and outputs compact markdown digests. The agent (LLM) reads these digests, synthesizes patterns, and writes to workspace memory files. A state file tracks what's been mined, enabling meta-learning cycles that improve extraction quality.

**Tech Stack:** Python 3 (stdlib only — json, os, argparse, collections), no external dependencies.

---

## File Structure

```
~/.pi/agent/skills/recursive-learning/
  SKILL.md                      # Agent workflow documentation (create)
  analyze_sessions.py           # Deterministic parser + scorer + CLI (create)
  meta-learning/
    journal.md                  # Meta-learning log (create)
    state.json                  # Mined state + heuristics schema (create)
```

Per-project state lands at `<project>/.meta-learning/state.json`.

Each file's responsibility:
- **SKILL.md** — Teaches the agent the 5-phase workflow: scan → categorize → synthesize → write → update state. Also cycles 2/3 for meta-learning.
- **analyze_sessions.py** — CLI with 3 modes: `scan` (rank sessions, output digests), `state` (show what's been mined), `reset` (clear mined state). Pure stdlib.
- **meta-learning/journal.md** — Human-readable log of extraction gaps, false patterns, heuristic decisions.
- **meta-learning/state.json** — Machine-readable: mined session IDs, discovered files, extraction gaps, cycle counters.

---

### Task 1: Create Directory Structure and Test Skeleton

**Files:**
- Create: `~/.pi/agent/skills/recursive-learning/analyze_sessions.py`
- Create: `~/.pi/agent/skills/recursive-learning/meta-learning/journal.md`
- Create: `~/.pi/agent/skills/recursive-learning/meta-learning/state.json`

- [ ] **Step 1: Create directories**

```bash
mkdir -p ~/.pi/agent/skills/recursive-learning/meta-learning
```

- [ ] **Step 2: Write skeleton analyze_sessions.py with argparse and a dummy scan command**

```python
#!/usr/bin/env python3
"""analyze_sessions.py — Mine PI session logs for learning opportunities.

Deterministic parser that scores sessions by learning potential and
outputs compact markdown digests for LLM synthesis.

Usage:
  analyze_sessions.py scan [--limit N] [--min-score N] [--project DIR]
  analyze_sessions.py state [--project DIR]
  analyze_sessions.py reset [--project DIR]
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Mine PI session logs")
    sub = parser.add_subparsers(dest="mode", required=True)

    scan_p = sub.add_parser("scan", help="Rank sessions and output digests")
    scan_p.add_argument("--limit", type=int, default=10, help="Max sessions to output")
    scan_p.add_argument("--min-score", type=int, default=0, help="Minimum score threshold")
    scan_p.add_argument("--project", type=str, help="Project directory (default: cwd)")

    sub.add_parser("state", help="Show mined state summary")
    sub.add_parser("reset", help="Clear mined state for this project")

    args = parser.parse_args()

    if args.mode == "scan":
        print("Scan mode — not yet implemented")
    elif args.mode == "state":
        print("State mode — not yet implemented")
    elif args.mode == "reset":
        print("Reset mode — not yet implemented")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify skeleton runs**

```bash
python3 ~/.pi/agent/skills/recursive-learning/analyze_sessions.py scan
python3 ~/.pi/agent/skills/recursive-learning/analyze_sessions.py state
python3 ~/.pi/agent/skills/recursive-learning/analyze_sessions.py reset
```

Expected: each prints "not yet implemented" message, no errors.

- [ ] **Step 4: Create meta-learning/journal.md template**

```markdown
# Meta-Learning Journal

## Extraction Gaps
<!-- Patterns the agent missed during synthesis. Add entries as discovered. -->

## False Patterns
<!-- Patterns that were flagged but later proven wrong or project-specific. -->

## Heuristic Tuning
<!-- Scoring weight changes and why -->

## Skill Updates
<!-- Changes made to SKILL.md based on meta-learning -->

---
```

- [ ] **Step 5: Create meta-learning/state.json schema**

```json
{
  "version": 1,
  "project": null,
  "last_analyzed": null,
  "cycles": {
    "cycle1_count": 0,
    "cycle2_count": 0,
    "cycle3_count": 0
  },
  "mined_sessions": {},
  "discovered_files": {},
  "extraction_gaps": [],
  "heuristics": {
    "error_weight": 10,
    "correction_loop_weight": 8,
    "discovery_density_weight": 5,
    "unique_files_weight": 2,
    "short_session_turns": 3,
    "short_session_penalty": 15
  }
}
```

- [ ] **Step 6: Commit**

```bash
cd ~/.pi/agent/skills
git add recursive-learning/
git commit -m "feat(skills): scaffold recursive-learning skill directory"
```

---

### Task 2: Implement Session Discovery

**Files:**
- Modify: `~/.pi/agent/skills/recursive-learning/analyze_sessions.py`

- [ ] **Step 1: Add function to find session directory for a project**

Insert after the `main()` function definition, before `if __name__`:

```python
import os
from pathlib import Path

SESSIONS_BASE = Path.home() / ".pi" / "agent" / "sessions"


def find_project_sessions(project_dir: str) -> list[Path]:
    """Find all session JSONL files for a given project directory.
    
    Session directories are named after the project path with slashes
    replaced by double-dashes and the home directory collapsed to --home--.
    """
    resolved = str(Path(project_dir).resolve())
    home = str(Path.home())
    
    # Build the session dir name: replace / with -- and collapse home
    # Example: /home/user/projects/foo -> --home--user-projects-foo--
    session_dir_name = resolved.replace(home, "--home--").replace("/", "--") + "--"
    
    session_dir = SESSIONS_BASE / session_dir_name
    if not session_dir.exists():
        return []
    
    return sorted(
        [f for f in session_dir.iterdir() if f.suffix == ".jsonl"],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
```

- [ ] **Step 2: Test session discovery against real data**

Run a quick test:

```bash
python3 -c "
import sys; sys.path.insert(0, '$HOME/.pi/agent/skills/recursive-learning')
from analyze_sessions import find_project_sessions
sessions = find_project_sessions('$HOME/nixfiles')
print(f'Found {len(sessions)} sessions')
for s in sessions[:5]:
    print(f'  {s.name} ({s.stat().st_size // 1024}KB)')
"
```

Expected: finds 50+ sessions from the nixfiles project, sorted by modification time (newest first).

- [ ] **Step 3: Commit**

```bash
cd ~/.pi/agent/skills
git add recursive-learning/analyze_sessions.py
git commit -m "feat(analyze_sessions): add session discovery for current project"
```

---

### Task 3: Implement JSONL Parsing — Extract Messages, Tool Calls, Errors

**Files:**
- Modify: `~/.pi/agent/skills/recursive-learning/analyze_sessions.py`

- [ ] **Step 1: Add SessionMetrics dataclass and parsing function**

Insert after session discovery functions:

```python
from dataclasses import dataclass, field
from collections import Counter
import json


@dataclass
class SessionMetrics:
    """Extracted metrics from a single session."""
    session_id: str
    timestamp: str
    cwd: str
    file_path: Path
    
    # Content
    first_user_message: str = ""
    turn_count: int = 0
    assistant_turns: int = 0
    
    # Tool calls
    tool_calls: Counter = field(default_factory=Counter)
    tool_sequences: list[list[str]] = field(default_factory=list)
    
    # Errors
    tool_errors: list[dict] = field(default_factory=list)  # [{tool, error}]
    bash_failures: int = 0
    
    # Files
    files_read: set[str] = field(default_factory=set)
    files_edited: set[str] = field(default_factory=set)
    all_files_touched: set[str] = field(default_factory=set)
    
    # Correction loops: same file accessed 3+ times
    file_access_counts: Counter = field(default_factory=Counter)
    
    # Tokens
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_read: int = 0
    total_thinking_chars: int = 0


def parse_session(file_path: Path) -> SessionMetrics | None:
    """Parse a single session JSONL file and extract metrics."""
    metrics = None
    current_tool_sequence: list[str] = []
    
    with open(file_path) as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            # Session header
            if entry.get("type") == "session":
                metrics = SessionMetrics(
                    session_id=entry.get("id", ""),
                    timestamp=entry.get("timestamp", ""),
                    cwd=entry.get("cwd", ""),
                    file_path=file_path,
                )
                continue
            
            if metrics is None:
                continue
            
            msg = entry.get("message", {})
            if not isinstance(msg, dict):
                continue
            
            role = msg.get("role", "")
            
            # Count turns
            if role == "assistant":
                metrics.assistant_turns += 1
                metrics.turn_count += 1
                
                # Token usage
                usage = msg.get("usage", {})
                metrics.total_input_tokens += usage.get("inputTokens", 0)
                metrics.total_output_tokens += usage.get("outputTokens", 0)
                metrics.total_cache_read += usage.get("cacheReadInputTokens", 0)
                
                # Thinking
                thinking = msg.get("thinking", "")
                metrics.total_thinking_chars += len(thinking)
                
                # Track tool call sequence
                current_tool_sequence = []
                
            elif role == "user":
                metrics.turn_count += 1
                # Capture first user message
                if not metrics.first_user_message:
                    content = msg.get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                metrics.first_user_message = block.get("text", "")
                                break
            
            # Extract tool calls from assistant content blocks
            if role == "assistant":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_call":
                            tool_name = block.get("toolName", "unknown")
                            metrics.tool_calls[tool_name] += 1
                            current_tool_sequence.append(tool_name)
                            
                            # Track file accesses
                            args = block.get("args", {})
                            if isinstance(args, dict):
                                fp = args.get("path") or args.get("file_path") or args.get("filePath", "")
                                if fp:
                                    metrics.all_files_touched.add(fp)
                                    metrics.file_access_counts[fp] += 1
                                    if tool_name == "edit":
                                        metrics.files_edited.add(fp)
                                    elif tool_name == "read":
                                        metrics.files_read.add(fp)
                
                if current_tool_sequence:
                    metrics.tool_sequences.append(list(current_tool_sequence))
            
            # Track tool errors
            if role == "toolResult":
                tool_name = msg.get("toolName", "")
                is_error = msg.get("isError", False)
                
                if tool_name == "bash":
                    # Check for bash failures from content
                    content = msg.get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict):
                                text = block.get("text", "")
                                if text and ("exit code 1" in text or "error" in text.lower()):
                                    metrics.bash_failures += 1
                                    break
                
                if is_error:
                    error_text = ""
                    content = msg.get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict):
                                error_text += block.get("text", "")
                    metrics.tool_errors.append({
                        "tool": tool_name,
                        "error": error_text[:200],
                    })
    
    return metrics
```

- [ ] **Step 2: Test parsing on a real session**

```bash
python3 << 'PYEOF'
import sys; sys.path.insert(0, '$HOME/.pi/agent/skills/recursive-learning')
from analyze_sessions import find_project_sessions, parse_session

sessions = find_project_sessions('$HOME/nixfiles')
if sessions:
    m = parse_session(sessions[0])
    print(f"Session: {m.session_id[:20]}...")
    print(f"First message: {m.first_user_message[:120]}")
    print(f"Turns: {m.turn_count}, Assistant turns: {m.assistant_turns}")
    print(f"Tool calls: {dict(m.tool_calls)}")
    print(f"Errors: {len(m.tool_errors)}, Bash failures: {m.bash_failures}")
    print(f"Files touched: {len(m.all_files_touched)}")
    print(f"Tokens: input={m.total_input_tokens}, output={m.total_output_tokens}")
    print(f"File access counts: {dict(m.file_access_counts.most_common(5))}")
PYEOF
```

Expected: output shows realistic metrics from a real session.

- [ ] **Step 3: Commit**

```bash
cd ~/.pi/agent/skills
git add recursive-learning/analyze_sessions.py
git commit -m "feat(analyze_sessions): add JSONL parsing with SessionMetrics extraction"
```

---

### Task 4: Implement Scoring Algorithm

**Files:**
- Modify: `~/.pi/agent/skills/recursive-learning/analyze_sessions.py`

- [ ] **Step 1: Add scoring function**

```python
def score_session(metrics: SessionMetrics, heuristics: dict | None = None) -> dict:
    """Score a session for learning potential. Returns score breakdown."""
    if heuristics is None:
        heuristics = {}
    
    error_w = heuristics.get("error_weight", 10)
    correction_w = heuristics.get("correction_loop_weight", 8)
    discovery_w = heuristics.get("discovery_density_weight", 5)
    files_w = heuristics.get("unique_files_weight", 2)
    short_turns = heuristics.get("short_session_turns", 3)
    short_penalty = heuristics.get("short_session_penalty", 15)
    
    errors = len(metrics.tool_errors) + metrics.bash_failures
    
    # Correction loops: files accessed 3+ times
    corrections = sum(1 for c in metrics.file_access_counts.values() if c >= 3)
    
    # Discovery density: unique files / total tool calls (avoid div by zero)
    total_tools = sum(metrics.tool_calls.values())
    discovery = len(metrics.all_files_touched) / max(total_tools, 1)
    
    unique_files = len(metrics.all_files_touched)
    
    raw_score = (
        errors * error_w
        + corrections * correction_w
        + int(discovery * discovery_w * 100)
        + unique_files * files_w
    )
    
    # Penalize trivial sessions
    if metrics.assistant_turns < short_turns:
        raw_score -= short_penalty
    
    return {
        "score": max(raw_score, 0),
        "breakdown": {
            "errors": errors * error_w,
            "correction_loops": corrections * correction_w,
            "discovery_density": int(discovery * discovery_w * 100),
            "unique_files": unique_files * files_w,
            "short_session_penalty": -(short_penalty if metrics.assistant_turns < short_turns else 0),
        },
        "raw": {
            "error_count": errors,
            "correction_loops": corrections,
            "discovery_ratio": round(discovery, 3),
            "unique_files": unique_files,
            "assistant_turns": metrics.assistant_turns,
        },
    }
```

- [ ] **Step 2: Test scoring on real session**

```bash
python3 << 'PYEOF'
import sys; sys.path.insert(0, '$HOME/.pi/agent/skills/recursive-learning')
from analyze_sessions import find_project_sessions, parse_session, score_session

sessions = find_project_sessions('$HOME/nixfiles')
for s in sessions[:5]:
    m = parse_session(s)
    result = score_session(m)
    print(f"{s.name[:50]}... score={result['score']} | {result['raw']}")
PYEOF
```

Expected: sessions with errors and file exploration score higher than trivial sessions.

- [ ] **Step 3: Commit**

```bash
cd ~/.pi/agent/skills
git add recursive-learning/analyze_sessions.py
git commit -m "feat(analyze_sessions): add scoring algorithm with configurable weights"
```

---

### Task 5: Implement Digest Generation

**Files:**
- Modify: `~/.pi/agent/skills/recursive-learning/analyze_sessions.py`

- [ ] **Step 1: Add digest generation function**

```python
def generate_digest(metrics: SessionMetrics, score_result: dict, known_files: set[str]) -> str:
    """Generate a compact markdown digest for LLM consumption."""
    
    # Extract date from timestamp
    ts = metrics.timestamp[:10] if metrics.timestamp else "unknown"
    
    # Intent: first 100 chars of first user message
    intent = metrics.first_user_message[:120].replace("\n", " ")
    if len(metrics.first_user_message) > 120:
        intent += "..."
    
    # Top tools
    top_tools = ", ".join(
        f"{name}({count})" 
        for name, count in metrics.tool_calls.most_common(5)
    )
    
    # Correction loops: files hit 3+ times
    corrections = [
        (f, c) for f, c in metrics.file_access_counts.most_common(10)
        if c >= 3
    ]
    correction_str = ""
    if corrections:
        correction_str = ", ".join(f"{f}({c}x)" for f, c in corrections)
    
    # Errors
    error_summary = ""
    if metrics.tool_errors:
        error_tools = Counter(e["tool"] for e in metrics.tool_errors)
        error_summary = ", ".join(f"{t}({c})" for t, c in error_tools.most_common(5))
    
    # Discoveries: files not seen before
    new_files = metrics.all_files_touched - known_files
    
    # Files section
    files_touched = sorted(metrics.all_files_touched)[:20]
    files_str = "\n".join(f"- {f}" for f in files_touched)
    
    # Token summary
    token_str = ""
    if metrics.total_input_tokens:
        token_str = (
            f"input={metrics.total_input_tokens:,} "
            f"output={metrics.total_output_tokens:,} "
            f"cache_read={metrics.total_cache_read:,} "
            f"thinking={metrics.total_thinking_chars:,}chars"
        )
    
    digest = f"""## Session {ts} — {intent[:80] if intent else '(no user message)'}
**Score:** {score_result['score']} | **Turns:** {metrics.assistant_turns} | **Tools:** {sum(metrics.tool_calls.values())}
**Intent:** {intent}
**Top tools:** {top_tools}
"""
    
    if token_str:
        digest += f"**Tokens:** {token_str}\n"
    
    if error_summary:
        digest += f"**Tool errors:** {error_summary}\n"
    
    if metrics.bash_failures:
        digest += f"**Bash failures:** {metrics.bash_failures}\n"
    
    if correction_str:
        digest += f"**Correction loops:** {correction_str}\n"
    
    if new_files:
        digest += f"**New discoveries ({len(new_files)}):** {', '.join(sorted(new_files)[:10])}\n"
    
    digest += f"""
**Files touched ({len(metrics.all_files_touched)}):**
{files_str}
"""
    
    # Error details (collapsed)
    if metrics.tool_errors:
        digest += "\n**Error details:**\n"
        for e in metrics.tool_errors[:5]:
            err_text = e["error"][:150].replace("\n", " ")
            digest += f"- `{e['tool']}`: {err_text}\n"
    
    digest += f"\n**Session ID:** `{metrics.session_id}`\n"
    
    return digest
```

- [ ] **Step 2: Test digest generation**

```bash
python3 << 'PYEOF'
import sys; sys.path.insert(0, '$HOME/.pi/agent/skills/recursive-learning')
from analyze_sessions import find_project_sessions, parse_session, score_session, generate_digest

sessions = find_project_sessions('$HOME/nixfiles')
m = parse_session(sessions[0])
score = score_session(m)
digest = generate_digest(m, score, set())
print(digest)
print(f"\nDigest size: {len(digest)} chars, ~{len(digest)//4} tokens")
PYEOF
```

Expected: compact markdown digest under 5KB for a typical session.

- [ ] **Step 3: Commit**

```bash
cd ~/.pi/agent/skills
git add recursive-learning/analyze_sessions.py
git commit -m "feat(analyze_sessions): add compact markdown digest generation"
```

---

### Task 6: Implement State Management (state.json)

**Files:**
- Modify: `~/.pi/agent/skills/recursive-learning/analyze_sessions.py`

- [ ] **Step 1: Add state management functions**

```python
DEFAULT_STATE = {
    "version": 1,
    "project": None,
    "last_analyzed": None,
    "cycles": {"cycle1_count": 0, "cycle2_count": 0, "cycle3_count": 0},
    "mined_sessions": {},
    "discovered_files": {},
    "extraction_gaps": [],
    "heuristics": {
        "error_weight": 10,
        "correction_loop_weight": 8,
        "discovery_density_weight": 5,
        "unique_files_weight": 2,
        "short_session_turns": 3,
        "short_session_penalty": 15,
    },
}


def get_state_path(project_dir: str) -> Path:
    """Get path to per-project state file."""
    return Path(project_dir) / ".meta-learning" / "state.json"


def load_state(project_dir: str) -> dict:
    """Load state for a project, returning defaults if no state exists."""
    state_path = get_state_path(project_dir)
    if state_path.exists():
        try:
            with open(state_path) as f:
                state = json.load(f)
            # Merge with defaults for forward compatibility
            for key, value in DEFAULT_STATE.items():
                if key not in state:
                    state[key] = value
            return state
        except (json.JSONDecodeError, IOError):
            pass
    return dict(DEFAULT_STATE)


def save_state(project_dir: str, state: dict):
    """Save state for a project."""
    state_path = get_state_path(project_dir)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state["last_analyzed"] = __import__("datetime").datetime.now().isoformat()
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)


def get_known_files(state: dict) -> set[str]:
    """Return set of all files discovered in previous sessions."""
    return set(state.get("discovered_files", {}).keys())


def mark_session_mined(state: dict, session_id: str, score: int, categories: list[str]):
    """Mark a session as mined in state."""
    state["mined_sessions"][session_id] = {
        "score": score,
        "categories": categories,
        "mined_at": __import__("datetime").datetime.now().isoformat(),
    }


def mark_files_discovered(state: dict, files: set[str]):
    """Add files to discovered set with current date."""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    for f in files:
        if f not in state["discovered_files"]:
            state["discovered_files"][f] = {"first_seen": today}
    state["cycles"]["cycle1_count"] += 1
```

- [ ] **Step 2: Test state management (write then read)**

```bash
python3 << 'PYEOF'
import sys, tempfile, os
sys.path.insert(0, '$HOME/.pi/agent/skills/recursive-learning')
from analyze_sessions import load_state, save_state, mark_session_mined, mark_files_discovered, get_known_files

with tempfile.TemporaryDirectory() as tmp:
    state = load_state(tmp)
    print(f"Default state: {state['version']}")
    
    mark_session_mined(state, "test-session-id", 87, ["debugging", "state-management"])
    mark_files_discovered(state, {"src/lib/appMixer.ts", "src/widget/appMixer.tsx"})
    
    save_state(tmp, state)
    print("State saved")
    
    # Read back
    state2 = load_state(tmp)
    print(f"Mined sessions: {list(state2['mined_sessions'].keys())}")
    print(f"Known files: {get_known_files(state2)}")
    print(f"Cycle 1 count: {state2['cycles']['cycle1_count']}")
PYEOF
```

Expected: state persists correctly, cycle counter increments, files tracked.

- [ ] **Step 3: Commit**

```bash
cd ~/.pi/agent/skills
git add recursive-learning/analyze_sessions.py
git commit -m "feat(analyze_sessions): add state management for per-project tracking"
```

---

### Task 7: Wire CLI — scan, state, reset Commands

**Files:**
- Modify: `~/.pi/agent/skills/recursive-learning/analyze_sessions.py`

- [ ] **Step 1: Replace the dummy scan/state/reset implementations with real logic**

Replace the `if args.mode == "scan":` block inside `main()` with:

```python
def cmd_scan(args):
    """Rank sessions, output digests for top-N unmined sessions."""
    project_dir = args.project or os.getcwd()
    state = load_state(project_dir)
    known_files = get_known_files(state)
    heuristics = state.get("heuristics", {})
    
    sessions = find_project_sessions(project_dir)
    if not sessions:
        print("No sessions found for this project.")
        return
    
    # Parse and score all sessions, skip already mined
    scored = []
    for session_path in sessions:
        session_id = session_path.stem.split("_", 1)[1] if "_" in session_path.stem else session_path.stem
        if session_id in state.get("mined_sessions", {}):
            continue
        
        metrics = parse_session(session_path)
        if metrics is None:
            continue
        
        score_result = score_session(metrics, heuristics)
        if score_result["score"] < args.min_score:
            continue
        
        scored.append((score_result["score"], metrics, score_result))
    
    # Sort by score descending, take top N
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[: args.limit]
    
    if not top:
        print("No unmined sessions found above score threshold.")
        return
    
    # Output digests
    print(f"# Session Analysis — {Path(project_dir).name}")
    print(f"**Total sessions:** {len(sessions)} | **Mined:** {len(state.get('mined_sessions', {}))} | **New:** {len(scored)}")
    print(f"**Showing top {len(top)} by score**\n")
    
    for score, metrics, score_result in top:
        digest = generate_digest(metrics, score_result, known_files)
        print(digest)
        print("---\n")


def cmd_state(args):
    """Show mined state summary."""
    project_dir = args.project or os.getcwd()
    state = load_state(project_dir)
    
    print(f"# State: {Path(project_dir).name}")
    print(f"**Last analyzed:** {state.get('last_analyzed', 'never')}")
    print(f"**Mined sessions:** {len(state.get('mined_sessions', {}))}")
    print(f"**Discovered files:** {len(state.get('discovered_files', {}))}")
    print(f"**Cycles:** cycle1={state['cycles']['cycle1_count']}, cycle2={state['cycles']['cycle2_count']}, cycle3={state['cycles']['cycle3_count']}")
    print(f"**Heuristics:** {state.get('heuristics', {})}")
    print(f"**Extraction gaps:** {state.get('extraction_gaps', [])}")


def cmd_reset(args):
    """Clear mined state."""
    project_dir = args.project or os.getcwd()
    state_path = get_state_path(project_dir)
    if state_path.exists():
        state_path.unlink()
        print(f"State cleared for {project_dir}")
    else:
        print(f"No state file found for {project_dir}")
```

Then update the `main()` function:

```python
def main():
    parser = argparse.ArgumentParser(
        description="Mine PI session logs for learning opportunities"
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    scan_p = sub.add_parser("scan", help="Rank sessions and output digests")
    scan_p.add_argument("--limit", type=int, default=10)
    scan_p.add_argument("--min-score", type=int, default=0)
    scan_p.add_argument("--project", type=str)

    state_p = sub.add_parser("state", help="Show mined state summary")
    state_p.add_argument("--project", type=str)

    reset_p = sub.add_parser("reset", help="Clear mined state for this project")
    reset_p.add_argument("--project", type=str)

    args = parser.parse_args()

    if args.mode == "scan":
        cmd_scan(args)
    elif args.mode == "state":
        cmd_state(args)
    elif args.mode == "reset":
        cmd_reset(args)
```

- [ ] **Step 2: Test full scan against real project**

```bash
python3 ~/.pi/agent/skills/recursive-learning/analyze_sessions.py scan --project ~/nixfiles --limit 3
```

Expected: outputs 3 session digests with scores, tool counts, files touched. Each digest 1-5KB.

- [ ] **Step 3: Test state command**

```bash
python3 ~/.pi/agent/skills/recursive-learning/analyze_sessions.py state --project ~/nixfiles
```

Expected: shows 0 mined sessions initially.

- [ ] **Step 4: Commit**

```bash
cd ~/.pi/agent/skills
git add recursive-learning/analyze_sessions.py
git commit -m "feat(analyze_sessions): wire CLI with scan, state, reset commands"
```

---

### Task 8: Integration Test — Scan, Mine, Verify Non-Duplication

**Files:**
- No new files — testing existing functionality end-to-end

- [ ] **Step 1: Run scan and capture digests to a file**

```bash
python3 ~/.pi/agent/skills/recursive-learning/analyze_sessions.py scan \
  --project ~/nixfiles --limit 5 > /tmp/session-digests.md 2>&1
wc -l /tmp/session-digests.md
wc -c /tmp/session-digests.md
```

- [ ] **Step 2: Verify digest format**

- [ ] Check that each digest has: Score, Turns, Tools, Intent, Top tools, Files touched
- [ ] Check total output is under 30KB (5 digests × ~5KB each)

- [ ] **Step 3: Simulate mining — manually mark sessions as learned**

```bash
python3 << 'PYEOF'
import sys; sys.path.insert(0, '$HOME/.pi/agent/skills/recursive-learning')
from analyze_sessions import (
    load_state, save_state, mark_session_mined,
    mark_files_discovered, find_project_sessions, parse_session
)

project = '$HOME/nixfiles'
state = load_state(project)
sessions = find_project_sessions(project)

# Mark first 3 sessions as mined
for s in sessions[:3]:
    m = parse_session(s)
    if m:
        mark_session_mined(state, m.session_id, 50, ["integration-test"])
        mark_files_discovered(state, m.all_files_touched)

save_state(project, state)
print(f"Mined: {len(state['mined_sessions'])} sessions")
print(f"Files: {len(state['discovered_files'])} discovered")
PYEOF
```

- [ ] **Step 4: Run scan again — verify those 3 are skipped**

```bash
python3 ~/.pi/agent/skills/recursive-learning/analyze_sessions.py scan \
  --project ~/nixfiles --limit 5
```

Expected: the 3 mined sessions do not appear in output. Different sessions shown.

- [ ] **Step 5: Verify state file exists and is valid**

```bash
cat ~/nixfiles/.meta-learning/state.json | python3 -m json.tool | head -30
```

- [ ] **Step 6: Clean up test state**

```bash
python3 ~/.pi/agent/skills/recursive-learning/analyze_sessions.py reset --project ~/nixfiles
```

- [ ] **Step 7: Commit**

```bash
cd ~/.pi/agent/skills
git add recursive-learning/
git commit -m "test(analyze_sessions): verify scan, state tracking, and deduplication"
```

---

### Task 9: Write SKILL.md — Agent Workflow Documentation

**Files:**
- Create: `~/.pi/agent/skills/recursive-learning/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

```markdown
---
name: recursive-learning
description: Use when the user says learn from sessions, mine past sessions, extract patterns from history, or optimize agent behavior from past experience. Also use after completing a significant project phase to capture discoveries.
---

# Recursive Learning

## Overview

Mine past PI session logs for code structure, discoveries, constraints, and behavioral optimizations. Persist findings to workspace memory so future sessions start smarter. Learns recursively: detects extraction gaps and improves its own heuristics over time.

## When to Use

- After a significant debugging session or feature completion
- When entering a project with many past sessions
- When the user says "learn from sessions" or "what have we discovered"
- Periodically (every 10-20 sessions) to prevent knowledge decay

**Do NOT use** for trivial sessions (< 3 tool calls) or sessions that only reviewed existing code.

## Quick Reference

| Phase | Action | Tool/Command |
|---|---|---|
| 1. Scan | Run analyzer, get ranked digests | `python3 analyze_sessions.py scan --limit 10` |
| 2. Categorize | Classify findings into 4 buckets | Read digests, assign categories |
| 3. Synthesize | Filter duplicates, find patterns | Cross-reference with existing memory |
| 4. Write | Append to memory files | Follow `learn` skill format |
| 5. Update | Mark sessions as mined | `python3 analyze_sessions.py state` |

## 4 Buckets → Memory Mapping

| Bucket | What goes there | Memory file |
|---|---|---|
| Code structure | File roles, module boundaries, architecture patterns | `project-patterns.md` |
| Discoveries | API behaviors, tool quirks, bugs found, library internals | `learning-log.md` |
| Constraints | Platform limitations, workarounds, build gotchas, can't-do's | `conventions.md` or project README |
| Behavior optimizations | Wasted token patterns, repeated mistakes, better tool sequences | `conventions.md` (global) or `project-patterns.md` |

## Phase 2-3 Details: Categorize & Synthesize

For each digest, ask:
1. **Code structure:** What files were touched? Is the role of each file clear? Are there architectural patterns (data flow, module boundaries)?
2. **Discoveries:** What errors occurred? What was the fix? Any surprising API behavior? First-time file access?
3. **Constraints:** What could NOT be done? What workarounds were needed? Build system quirks?
4. **Behavior optimizations:** Were there repeated tool calls? Failed approaches before success? Over-read files?

Synthesis rules:
- **Skip duplicates:** Already in memory? Skip.
- **Skip anecdotes:** Single-session occurrence? Skip (needs 2+ sessions to be a pattern).
- **Keep patterns:** Seen in 2+ sessions? Write.
- **Update entries:** Existing entry is wrong/outdated? Update with new date.

## Phase 4: Write Format

Use the `learn` skill format for all entries:

```markdown
### YYYY-MM-DD — Extracted: <topic>

**Problem:**
<what went wrong or what was discovered>

**Solution:**
<correct approach or key insight>

**Source:**
Session <date> (<project>), Session <date> (<project>)
```

**REQUIRED SUB-SKILL:** Use `learn` for the actual file writes to maintain format consistency.

## Phase 5: Update State

After writing, update state by importing and calling:

```python
from analyze_sessions import load_state, save_state, mark_session_mined, mark_files_discovered

state = load_state(project_dir)
for session_id, categories in learned_sessions:
    mark_session_mined(state, session_id, score, categories)
for files in discovered_files:
    mark_files_discovered(state, files)
save_state(project_dir, state)
```

## Meta-Learning (Cycles 2 & 3)

**Cycle 2** — Every 5+ sessions analyzed since last review:
- Run `python3 analyze_sessions.py state` to see extraction gaps
- Review journal.md for false patterns
- Tune heuristics in state.json if scoring misses valuable sessions
- Check: did any learned pattern turn out wrong? If so, log to journal.md as a false pattern

**Cycle 3** — Every 3+ heuristic changes:
- Review this SKILL.md for outdated category definitions
- Update Phase 2-3 synthesis questions if they missed patterns
- Update bucket mapping if categories drift
- Commit changes to the skill and journal

## Common Mistakes

- **Mining without state:** Always load state first — otherwise you re-analyze already-mined sessions and waste tokens
- **Single-session as pattern:** One session's discovery is an anecdote. Wait for 2+ occurrences.
- **Skipping synthesis:** Don't blindly write every digest finding. Filter, cross-reference, synthesize.
- **Forgetting meta-learning:** After 5+ runs, stop and review extraction quality. The skill gets worse if you never tune it.
```

- [ ] **Step 2: Verify SKILL.md is concise (< 500 words body)**

```bash
wc -w ~/.pi/agent/skills/recursive-learning/SKILL.md
```

- [ ] **Step 3: Commit**

```bash
cd ~/.pi/agent/skills
git add recursive-learning/SKILL.md
git commit -m "docs(skills): add recursive-learning SKILL.md with agent workflow"
```

---

### Task 10: End-to-End — Run Full Learning Cycle

**Files:**
- No new files — end-to-end verification

- [ ] **Step 1: Scan and save digests**

```bash
python3 ~/.pi/agent/skills/recursive-learning/analyze_sessions.py scan \
  --project ~/nixfiles --limit 3 > /tmp/learning-digests.md
```

- [ ] **Step 2: Agent simulates Phase 2-4: categorize, synthesize, write**

Read the digests and identify at least one finding per bucket, write to workspace memory.

- [ ] **Step 3: Verify memory files have new entries**

- [ ] **Step 4: Update state, verify cycle counter increments**

- [ ] **Step 5: Commit workspace changes**

```bash
cd ~/home/daviaaze/Projects/pessoal/ai-workspace
git add memory/
git commit -m "docs(memory): initial recursive-learning findings from nixfiles sessions"
```
