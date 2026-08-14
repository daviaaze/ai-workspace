# Spec: Worktree Manager — Parallel Agent Isolation via Git Worktrees

> **Status:** 📋 Spec | **Data:** 2026-06-27
> **Refs:** loop-engineering primitives, `git worktree` docs, SPEC_LOOP_PATTERNS.md, SPEC_JOB_QUEUE_VISUAL_WORKFLOW.md

---

## 🎯 The Problem

When two agents (or two loop runs) edit files in the same working directory simultaneously:

```
Agent A: edit src/auth.py → writes change X
Agent B: edit src/auth.py → writes change Y (overwrites X)
               ↓
        Merge hell, corrupted state, lost work
```

This is the **parallel collision** failure mode (loop-engineering S2 severity). Current aiw has no isolation mechanism — all agent operations share a single working tree.

**Git worktrees** solve this: each worktree is a checked-out copy of the repo that shares `.git` history but has its own working directory, index, and HEAD. Multiple agents can work in parallel without interference.

```
Main worktree (~/project)          Agent A's worktree (~/project/.worktrees/fix-auth)
┌──────────────────────────┐       ┌──────────────────────────┐
│ .git/    ←──shared──→   │       │ (symlink to main .git)   │
│ src/auth.py              │       │ src/auth.py (A's version) │
│ tests/                   │       │ tests/                   │
│ README.md                │       │ README.md (read-only)   │
└──────────────────────────┘       └──────────────────────────┘
                                          ↑
                                   Agent B's worktree (~/project/.worktrees/fix-db)
                                   ┌──────────────────────────┐
                                   │ (symlink to main .git)   │
                                   │ src/db.py (B's version)  │
                                   │ tests/                   │
                                   └──────────────────────────┘
```

---

## 📐 Design

### WorktreeManager (context manager — primary API)

```python
@dataclass
class WorktreeConfig:
    """Per-repo worktree configuration."""
    repo_path: Path                         # Path to the main repo
    worktree_dir: Path | None = None        # Where to create worktrees
    default_branch: str = "main"            # Base branch for new worktrees
    max_worktrees: int = 10                 # Hard limit per repo
    cleanup_age_hours: int = 24             # Auto-clean abandoned worktrees
    lock_timeout_seconds: int = 300         # Max time to wait for lock

@dataclass
class WorktreeHandle:
    """Handle to an acquired worktree. Returned by acquire()."""
    worktree_id: str                        # UUID
    pattern_id: str                         # Which loop owns this
    item_id: str                            # Which item (PR#, issue#, etc.)
    path: Path                              # Absolute path to worktree dir
    branch: str                             # Git branch name
    base_branch: str                        # The branch it was forked from
    created_at: datetime
    acquired_at: datetime
    locked: bool

class WorktreeManager:
    """Manages git worktree lifecycle for concurrent agent operations.
    
    Usage:
        async with wt_manager.acquire(
            pattern_id="ci-sweeper",
            item_id="fix-auth-flaky",
            base_branch="main",
        ) as wt:
            # wt.path points to an isolated worktree
            # All agent file operations happen inside wt.path
            # Worktree is cleaned up when context exits
            await run_agent_in_worktree(wt.path)
    """
    
    def __init__(self, config: WorktreeConfig | None = None):
        ...
    
    @asynccontextmanager
    async def acquire(
        self,
        pattern_id: str,
        item_id: str,
        base_branch: str | None = None,
        branch_name: str | None = None,  # auto-generated if None
        ttl_seconds: int = 3600,
    ) -> AsyncIterator[WorktreeHandle]:
        """Acquire a worktree for exclusive use.
        
        Creates a git worktree at:
            {worktree_dir}/{pattern_id}/{item_id}/
        
        On enter:
            1. Check max_worktrees limit
            2. Check no existing worktree for same (pattern_id, item_id)
            3. Create git worktree + branch
            4. Lock + register in PostgreSQL
            5. Return WorktreeHandle
        
        On exit:
            1. Run cleanup callbacks if provided
            2. Unlock
            3. Optionally delete worktree (configurable)
            4. Unregister from PostgreSQL
        """
        ...
    
    async def list_worktrees(
        self,
        pattern_id: str | None = None,
        status: str | None = None,  # 'active', 'stale', 'all'
    ) -> list[WorktreeHandle]:
        """List all registered worktrees."""
        ...
    
    async def cleanup_stale(
        self,
        max_age_hours: int = 24,
        dry_run: bool = False,
    ) -> list[str]:
        """Remove worktrees that have been abandoned.
        
        Stale = acquired but not released within max_age_hours,
        or git worktree prune candidates.
        """
        ...
    
    async def release(
        self,
        worktree_id: str,
        delete: bool = True,
        commit_changes: bool = False,
    ) -> None:
        """Release and optionally clean up a worktree."""
        ...
    
    async def get_worktree(
        self,
        pattern_id: str,
        item_id: str,
    ) -> WorktreeHandle | None:
        """Find worktree by (pattern_id, item_id)."""
        ...
    
    async def lock_status(self, worktree_id: str) -> bool:
        """Check if a worktree is currently locked."""
        ...

    def stats(self) -> dict:
        """Return usage statistics."""
        ...
```

### PostgreSQL Schema

```sql
CREATE TABLE worktree_registry (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_id      VARCHAR(100) NOT NULL,       -- which loop owns it
    item_id         VARCHAR(200) NOT NULL,        -- PR#1234, issue#456
    path            TEXT NOT NULL,                -- absolute path
    branch          VARCHAR(200) NOT NULL,        -- git branch name
    base_branch     VARCHAR(200) NOT NULL DEFAULT 'main',
    repo_path       TEXT NOT NULL,                -- main repo path
    
    -- Lifecycle
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    -- 'active', 'locked', 'stale', 'released', 'orphaned'
    
    -- Timing
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acquired_at     TIMESTAMPTZ,                  -- when acquire() returned
    released_at     TIMESTAMPTZ,                  -- when released
    last_used_at    TIMESTAMPTZ,
    
    -- Locking (prevents two agents grabbing the same worktree)
    locked_by       VARCHAR(200),                 -- agent/process ID
    locked_at       TIMESTAMPTZ,
    lock_expires_at TIMESTAMPTZ,                  -- auto-release after TTL
    
    -- Metadata
    total_edits     INT DEFAULT 0,                -- files modified
    total_tool_calls INT DEFAULT 0,               -- tools executed in worktree
    outcome         VARCHAR(50),                  -- 'committed', 'abandoned', 'merged'
    error           TEXT,
    
    -- Constraints
    UNIQUE(pattern_id, item_id),
    UNIQUE(path)
);

CREATE INDEX idx_worktree_status ON worktree_registry(status);
CREATE INDEX idx_worktree_pattern ON worktree_registry(pattern_id, status);
CREATE INDEX idx_worktree_stale ON worktree_registry(status, acquired_at)
    WHERE status IN ('active', 'locked');
CREATE INDEX idx_worktree_repo ON worktree_registry(repo_path);
```

### Safety Limits

```python
WORKTREE_DEFAULTS = {
    "max_worktrees": 10,           # Hard cap per repo
    "cleanup_age_hours": 24,       # Auto-prune stale worktrees
    "lock_timeout": 300,           # 5 min to acquire lock
    "max_branch_length": 80,       # Git branch name limit
    "cleanup_on_release": True,    # Delete worktree when released
}
```

---

## 🔐 Locking Protocol

Worktree locks prevent two loop runs from operating on the same item simultaneously.

```
Agent A                                        Agent B
   │                                              │
   ├─ acquire("ci-sweeper", "fix-auth")           │
   │    INSERT worktree_registry                  │
   │    status='active', locked_by='A'            │
   │    ← WorktreeHandle                          │
   │                                              ├─ acquire("ci-sweeper", "fix-auth")
   │                                              │    → UNIQUE(pattern, item) violation
   │                                              │    → Wait 5s, retry...
   │                                              │    → Locked by A (locked_by, locked_at)
   │                                              │    → Raise WorktreeBusyError
   │                                              │
   ├─ [works in worktree]                         │
   │                                              │
   ├─ release("fix-auth")                         │
   │    UPDATE status='released'                  │
   │    DELETE worktree from disk                 │
   │                                              │
   │                                              ├─ acquire("ci-sweeper", "fix-auth")
   │                                              │    → Success
```

**Deadlock prevention:**
- Lock timeout (default 5 min) → auto-release stale locks
- Acquire order is always deterministic (by `(pattern_id, item_id)`)
- No nested worktree acquisitions allowed (single-level only)

---

## 🧹 Lifecycle

```
                     acquire()
                         │
                    ┌────┴────┐
                    ▼         ▼
              [exists]    [new]
                  │          │
                  │    git worktree add
                  │    git checkout -b {branch}
                  │         │
                  └────┬────┘
                       ▼
              ┌─────────────────┐
              │  status=active  │
              │  locked_by=A    │
              │  acquired_at=T1 │
              └────────┬────────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
        [within TTL]      [TTL expired]
              │                 │
        [agent works]    ┌──────┴──────┐
              │          ▼             ▼
        release()   [cleanup]     [mark stale]
              │     auto-delete   notify human
              ▼         │             │
     ┌────────────┐     └──────┬──────┘
     │ status=    │            ▼
     │ released   │      [released if stale]
     │ git work-  │     or [retained for debug]
     │ tree remove│
     └────────────┘
```

---

## 🔧 Git Operations (Internal)

The manager wraps these raw git commands:

```python
class GitWorktreeOps:
    """Low-level git worktree operations."""
    
    @staticmethod
    async def add(
        repo_path: Path,
        worktree_path: Path,
        branch: str,
        base_branch: str = "main",
    ) -> None:
        """git worktree add -b {branch} {path} {base_branch}"""
        await run_git([
            "worktree", "add",
            "-b", branch,
            str(worktree_path),
            base_branch,
        ], cwd=repo_path)
    
    @staticmethod
    async def remove(worktree_path: Path) -> None:
        """git worktree remove {path}"""
        await run_git(["worktree", "remove", str(worktree_path)])
    
    @staticmethod
    async def prune(repo_path: Path) -> None:
        """git worktree prune — clean up stale git records"""
        await run_git(["worktree", "prune"], cwd=repo_path)
    
    @staticmethod
    async def list(repo_path: Path) -> list[dict]:
        """git worktree list --porcelain"""
        output = await run_git(["worktree", "list", "--porcelain"], cwd=repo_path)
        return parse_porcelain(output)
    
    @staticmethod
    async def lock(worktree_path: Path, reason: str = "") -> None:
        """git worktree lock {path} --reason {reason}"""
        args = ["worktree", "lock", str(worktree_path)]
        if reason:
            args.extend(["--reason", reason])
        await run_git(args)
    
    @staticmethod
    async def unlock(worktree_path: Path) -> None:
        """git worktree unlock {path}"""
        await run_git(["worktree", "unlock", str(worktree_path)])
```

---

## 🔗 Integration Points

### With Loop Patterns (SPEC_LOOP_PATTERNS.md)

```python
# Inside a loop's implementer phase:
async def run_ci_sweeper_fix(item: dict, wt_manager: WorktreeManager):
    """Fix a CI failure inside an isolated worktree."""
    
    async with wt_manager.acquire(
        pattern_id="ci-sweeper",
        item_id=item["id"],
        base_branch="main",
        branch_name=f"fix/{item['id']}",
    ) as wt:
        
        # Run implementer agent inside worktree
        result = await agent_loop(LoopParams(
            task=f"Fix this CI failure: {item['description']}",
            pattern=LoopPattern.REACT,
            tools=code_tools(cwd=wt.path),  # tools scoped to worktree
            system_prompt=load_skill("minimal-fix"),
            max_turns=10,
        ))
        
        # Run verifier inside same worktree
        verify = await agent_loop(LoopParams(
            task=f"Verify the fix in {wt.path}",
            pattern=LoopPattern.DIRECT,
            tools=code_tools(cwd=wt.path),
            system_prompt=load_skill("loop-verifier"),
            max_turns=5,
        ))
        
        # If approved, commit + push branch for PR
        if parse_verdict(verify.final_response) == "APPROVE":
            await git_commit_and_push(wt.path, f"fix: {item['description']}")
```

### With Job Queue (SPEC_JOB_QUEUE_VISUAL_WORKFLOW.md)

The job queue handler receives a `WorktreeManager` instance to use during execution.

---

## ⚡ CLI Interface

```bash
# List active worktrees
aiw worktree list
aiw worktree list --pattern ci-sweeper
aiw worktree list --status stale

# Show worktree details
aiw worktree show wt-<id>

# Release a worktree
aiw worktree release wt-<id>
aiw worktree release wt-<id> --keep  # don't delete on disk

# Cleanup stale worktrees
aiw worktree cleanup
aiw worktree cleanup --dry-run
aiw worktree cleanup --max-age 48  # hours

# Stats
aiw worktree stats
```

---

## 🖥 TUI Integration

Worktree status shown in the Loops tab and a new Worktrees panel:

```
┌─ Worktrees ─────────────────────────────────────────┐
│  ID          │ Pattern      │ Item     │ Status     │
│──────────────┼──────────────┼──────────┼────────────┤
│ wt-a1b2c3   │ ci-sweeper   │ fix-auth │ ● active   │
│ wt-d4e5f6   │ pr-babysitter│ PR#1423  │ ● active   │
│ wt-g7h8i9   │ deps-sweeper │ lodash   │ ◌ released │
│─────────────────────────────────────────────────────│
│ ● active: 2  ◌ released: 1  ○ stale: 0             │
│ Total disk usage: 48 MB  Max: 10 worktrees          │
└─────────────────────────────────────────────────────┘
```

---

## ✅ Acceptance Criteria

- [ ] `WorktreeManager` class with async context manager API
- [ ] `acquire()` creates git worktree + branch, registers in PostgreSQL
- [ ] `release()` deletes worktree, cleans git records, unregisters
- [ ] `list_worktrees()` with filter by pattern/status
- [ ] `cleanup_stale()` detects and removes abandoned worktrees
- [ ] Locking via `(pattern_id, item_id)` UNIQUE constraint + TTL
- [ ] Lock timeout auto-releases stale locks
- [ ] `worktree_registry` PostgreSQL table with full lifecycle tracking
- [ ] `GitWorktreeOps` wrapping all git worktree subcommands
- [ ] `aiw worktree list/show/release/cleanup/stats` CLI commands
- [ ] TUI panel showing worktree status
- [ ] Auto-cleanup on agent crash (cleanup job in queue)
- [ ] Safety: max_worktrees cap enforced
- [ ] Integration test: two loops working in parallel without collision

---

## 📚 References

- [git worktree documentation](https://git-scm.com/docs/git-worktree) — official git docs
- [loop-engineering primitives](https://github.com/cobusgreyling/loop-engineering/blob/main/docs/primitives.md) — worktrees as S3 primitives
- [loop-engineering LOOP.md](https://github.com/cobusgreyling/loop-engineering/blob/main/LOOP.md) — worktree usage in production
- [Grok sub-agent isolation](https://github.com/cobusgreyling/loop-engineering/blob/main/examples/grok/README.md) — `isolation: "worktree"` flag
- SPEC_LOOP_PATTERNS.md — consumes worktrees in implementer phase
- SPEC_JOB_QUEUE_VISUAL_WORKFLOW.md — scheduling context
