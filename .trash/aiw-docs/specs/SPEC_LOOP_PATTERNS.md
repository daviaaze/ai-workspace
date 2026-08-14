# Spec: Loop Patterns — Production Agent Loops

> **Status:** 📋 Spec | **Data:** 2026-06-27
> **Refs:** loop-engineering (cobusgreyling), SPEC_AGENT_LOOP.md, SPEC_WORKTREE_MANAGER.md, SPEC_JOB_QUEUE_VISUAL_WORKFLOW.md

---

## 🎯 What This Adds

The current `agent_loop()` is a **general execution engine** — it runs a task through a loop pattern (ReAct, Direct, Plan-Execute, ReWOO, DAG) and returns. What's missing:

| Gap | Impact |
|-----|--------|
| **No scheduled production patterns** | Every run is ad-hoc. No Daily Triage, no PR babysitting, no CI sweeper running on a cadence. |
| **No maker/checker verification** | The agent marks its own work complete. No structural quality gate. |
| **No per-loop state** | No `STATE.md` or equivalent durable memory between runs of the same loop. Amnesia every cycle. |
| **No readiness levels** | No L0→L3 maturity model. No safe ramp from "report only" to "unattended." |
| **No token budget per loop** | No kill switch, no daily cap, no run log. |
| **No human escalation protocol** | Loop failures write to stderr, not to a structured inbox. |
| **No multi-loop coordination** | If Daily Triage and CI Sweeper both run, they don't know about each other. |

This spec defines **production loop patterns** that sit **on top of** the existing agent loop, adding scheduling, state, verification, human gates, budget, and observability.

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     Pattern Registry                              │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────┐  │
│  │ Daily    │ │ PR       │ │ CI     │ │Depend. │ │Changelog │  │
│  │ Triage   │ │Babysitter│ │Sweeper │ │Sweeper │ │ Drafter  │  │
│  └──────────┘ └──────────┘ └────────┘ └────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐                                       │
│  │ Post-    │ │ Issue    │                                       │
│  │ Merge    │ │ Triage   │                                       │
│  └──────────┘ └──────────┘                                       │
└───────────────────┬──────────────────────────────────────────────┘
                    │
┌───────────────────┴──────────────────────────────────────────────┐
│                    Loop Runner                                     │
│  Per-pattern scheduler → state load → triage → action → verify    │
│  → state write → human escalation if needed                       │
└───────────────────┬──────────────────────────────────────────────┘
                    │
┌───────────────────┴──────────────────────────────────────────────┐
│                Primitive Layer (existing + new)                    │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────┐  │
│  │agent_loop│ │Worktree  │ │State   │ │MCP     │ │Verifier  │  │
│  │(ReAct/..)│ │Manager   │ │(STATE) │ │Client  │ │Sub-agent │  │
│  └──────────┘ └──────────┘ └────────┘ └────────┘ └──────────┘  │
└───────────────────┬──────────────────────────────────────────────┘
                    │
┌───────────────────┴──────────────────────────────────────────────┐
│              PostgreSQL (queue + state + run_log + budget)        │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📐 Data Model

### Pattern Registry (PostgreSQL)

```sql
CREATE TABLE loop_patterns (
    id          VARCHAR(100) PRIMARY KEY,   -- 'daily-triage', 'pr-babysitter'
    title       VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    cadence     BIGINT NOT NULL,            -- seconds between runs
    max_turns   INT NOT NULL DEFAULT 20,
    max_tokens  BIGINT NOT NULL DEFAULT 100000,
    verifier    BOOLEAN NOT NULL DEFAULT FALSE, -- maker/checker required
    worktree    BOOLEAN NOT NULL DEFAULT FALSE, -- needs git worktree
    requires_mcp TEXT[] DEFAULT '{}',        -- 'github', 'linear', 'slack'
    requires_skills TEXT[] DEFAULT '{}',     -- skill names needed
    readiness   VARCHAR(10) DEFAULT 'L0',    -- L0, L1, L2, L3
    enabled     BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Built-in patterns seeded on migration
INSERT INTO loop_patterns (id, title, description, cadence, verifier, worktree, readiness) VALUES
    ('daily-triage',      'Daily Triage',        'Morning scan of CI, issues, commits. Report-only week one.', 86400, FALSE, FALSE, 'L0'),
    ('pr-babysitter',     'PR Babysitter',        'Shepherd PRs through review, CI, rebase, and merge.',        900,   TRUE,  TRUE,  'L0'),
    ('ci-sweeper',        'CI Sweeper',           'React to failing checks with minimal fixes.',                 900,   TRUE,  TRUE,  'L0'),
    ('dependency-sweeper','Dependency Sweeper',   'Patch CVEs and stale deps in worktrees.',                   21600,  TRUE,  TRUE,  'L0'),
    ('post-merge-cleanup','Post-Merge Cleanup',   'TODOs, deprecations, tech debt after merges.',              21600,  FALSE, TRUE,  'L0'),
    ('issue-triage',      'Issue Triage',         'Dedupe, score, label incoming issues.',                      7200,  FALSE, FALSE, 'L0'),
    ('changelog-drafter', 'Changelog Drafter',    'Scan merges & commits, produce release notes drafts.',        86400, FALSE, FALSE, 'L0');
```

### Loop State (PostgreSQL + optional STATE.md mirror)

```sql
CREATE TABLE loop_state (
    id          SERIAL PRIMARY KEY,
    pattern_id  VARCHAR(100) NOT NULL REFERENCES loop_patterns(id),
    run_id      INT NOT NULL,                    -- FK to job_queue
    state_type  VARCHAR(20) DEFAULT 'snapshot',  -- 'snapshot' | 'delta'
    data        JSONB NOT NULL,                  -- full state payload
    
    -- Standard sections that every loop must set
    last_run    TIMESTAMPTZ,
    items_active JSONB DEFAULT '[]',   -- [{id, title, status, attempts}]
    items_watch  JSONB DEFAULT '[]',   -- [{id, title, status}]
    items_noise  JSONB DEFAULT '[]',   -- [{id, title, reason}]
    items_pruned JSONB DEFAULT '[]',   -- resolved this run
    escalations  JSONB DEFAULT '[]',   -- [{item, reason, context}]
    human_overrides JSONB DEFAULT '[]',
    
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_loop_state_pattern ON loop_state(pattern_id, created_at DESC);
```

### Run Log

```sql
CREATE TABLE loop_run_log (
    id          BIGSERIAL PRIMARY KEY,
    pattern_id  VARCHAR(100) NOT NULL REFERENCES loop_patterns(id),
    run_id      INT NOT NULL,                    -- FK to job_queue
    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    duration_ms INT,
    items_found INT DEFAULT 0,
    actions_taken INT DEFAULT 0,
    escalations INT DEFAULT 0,
    tokens_estimate BIGINT DEFAULT 0,
    outcome     VARCHAR(20),                     -- 'success', 'failed', 'escalated', 'noop'
    error       TEXT,
    
    -- Budget tracking
    token_budget BIGINT,                         -- cap at start of run
    tokens_remaining BIGINT,                     -- after run
    
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_loop_run_log_pattern ON loop_run_log(pattern_id, started_at DESC);
```

### Token Budget

```sql
CREATE TABLE loop_budget (
    id              SERIAL PRIMARY KEY,
    pattern_id      VARCHAR(100) NOT NULL REFERENCES loop_patterns(id),
    daily_cap       BIGINT NOT NULL DEFAULT 100000,  -- tokens per day
    daily_spent     BIGINT DEFAULT 0,
    budget_date     DATE NOT NULL DEFAULT CURRENT_DATE,
    paused          BOOLEAN DEFAULT FALSE,
    pause_reason    TEXT,
    kill_switch     BOOLEAN DEFAULT FALSE,            -- completely disabled
    notify_at_pct   INT DEFAULT 80,                   -- notify when >80% of cap
    
    UNIQUE(pattern_id, budget_date)
);
```

---

## 🧩 Pattern Definitions (7 Production Loops)

Each pattern follows the same lifecycle:

```
Schedule fires
  → Load state from loop_state (or STATE.md)
  → Run triage skill (scan CI, issues, PRs, commits)
  → Classify items into active/watch/noise
  → For active items:
       if ready_level >= L2:
         → Open worktree (if worktree=true)
         → Run implementer (agent_loop with appropriate pattern)
         → Run verifier sub-agent (maker/checker)
         → If verify passes: propose PR or write fix
  → Update state (prune resolved, add new items)
  → Write run log
  → If escalations: ping human via connector
  → Check budget: pause if exceeded
```

### Pattern 1: Daily Triage

```
ID:         daily-triage
Cadence:    1d (86400s) — morning
Verifier:   NO (report-only at L1)
Worktree:   NO
State:      loop_state with items_active/watch/noise
Skills:     loop-triage
MCP:        GitHub read (issues, CI), Linear read
Max tokens: 50_000/run

Lifecycle:
  L0 — Draft:   Pattern registered but disabled
  L1 — Report:  Runs daily. Triage → state. Updates items_active.
                No auto-action. Human reads state file.
  L2 — Assist:  For obvious small fixes (typo, lint), runs implementer.
                Verifier not needed since changes are trivial.
  L3 — Unattended: Same as L2. Auto-PR for trivial fixes on allowlist paths.
                Escalates anything ambiguous.

Failure modes:
  - Triage noise → tighten skill rules, add noise section
  - State rot → prune resolved items every run
  - Missed overnight failures → fireImmediately on start
```

### Pattern 2: PR Babysitter

```
ID:         pr-babysitter
Cadence:    10m (600s) during work hours
Verifier:   YES — maker/checker split required
Worktree:   YES — each fix attempt in isolated worktree
State:      loop_state tracking watched PRs
Skills:     pr-review-triage, minimal-fix, rebase-and-clean
MCP:        GitHub read+write (comments, labels), Linear optional
Max tokens: 2_000_000/day (with early exit!)

Lifecycle:
  L0 — Draft:   Pattern registered.
  L1 — Watch:   Scans open PRs. Comments status to PRs but proposes nothing.
                Updates state with PR status.
  L2 — Assist:  For allowlisted low-risk PRs:
                Worktree → implementer (minimal-fix for reviewer comments)
                → verifier checks diff scope + tests → proposes via PR comment
  L3 — Unattended: Same but can add "ready to merge" label.
                NO auto-merge without explicit allowlist.

Key design:
  - Early exit: if watchlist empty, finish in <3k tokens
  - Max 3 fix attempts per PR per run → escalate
  - Verifier must be separate sub-agent from implementer
  - PR comments signed as "🤖 aiw — PR Babysitter"
```

### Pattern 3: CI Sweeper

```
ID:         ci-sweeper
Cadence:    15m (900s)
Verifier:   YES — must run tests in worktree
Worktree:   YES — each fix attempt isolated
State:      loop_state tracking active CI failures
Skills:     ci-triage, minimal-fix
MCP:        GitHub read (checks, logs)
Max tokens: 1_000_000/day

Lifecycle:
  L0 — Draft.
  L1 — Monitor: Scans CI failures. Classifies: flake vs regression vs infra.
                Updates state. No auto-fix.
  L2 — Assist:  For classified regressions:
                Worktree → implementer (minimal-fix)
                → verifier runs tests in worktree → proposes PR
  L3 — Unattended: Same. Auto-labels flakes, escalates infra failures.

Key design:
  - Flake detection: if same test failed+passed on retry with no code change,
    classify as flake, do NOT auto-fix
  - Branch allowlist in skill: only main, release/*, watched PRs
  - Pause if main is red and >3 failures detected (batch fixes)
```

### Pattern 4: Dependency Sweeper

```
ID:         dependency-sweeper
Cadence:    6h (21600s)
Verifier:   YES — npm ci && npm test in worktree
Worktree:   YES
State:      loop_state tracking scanned deps + CVEs
Skills:     dependency-triage, minimal-fix
MCP:        GitHub (security advisories), npm/pip registry
Max tokens: 500_000/day

Lifecycle:
  L0 — Draft.
  L1 — Scan:   Scan dependencies, report CVEs. No auto-fix.
  L2 — Patch:  For patch-level + low-risk CVEs: worktree → update → verify
                → propose PR. Majors and denylisted packages → human gate.
  L3 — Same, with auto-PR for low-risk patches.

Key design:
  - Denylist packages never auto-updated (e.g. crypto, auth libs)
  - Verifier runs full test suite in worktree
  - Max 5 auto-PRs per day (cleanup throttle)
```

### Pattern 5: Post-Merge Cleanup

```
ID:         post-merge-cleanup
Cadence:    1d (86400s) — off-peak
Verifier:   NO (changes are trivial)
Worktree:   YES
State:      loop_state tracking TODO/FIXME/HACK items
Skills:     cleanup-triage, minimal-fix
MCP:        GitHub read
Max tokens: 200_000/run

Lifecycle:
  L0 — Draft.
  L1 — Report: Scan recent merges. Find TODOs, deprecations, stale branches.
               Report in state. No auto-action.
  L2 — Assist: Auto-fix trivial items (typos, deprecated API calls) in worktree.
  L3 — Unattended: Same, auto-PR.

Key design:
  - One fix per line-item — never batch TODOs into monster PRs
  - Verifier not needed for trivial but worktree isolation required
```

### Pattern 6: Issue Triage

```
ID:         issue-triage
Cadence:    2h (7200s)
Verifier:   NO
Worktree:   NO
State:      loop_state tracking issue categories
Skills:     issue-triage
MCP:        GitHub (issues, labels), Linear
Max tokens: 100_000/run

Lifecycle:
  L0 — Draft.
  L1 — Label:  Scan new issues. Dedupe, score priority, suggest labels.
                Propose-only — human applies labels.
  L2 — Triage:  Auto-label low-risk categories (docs, question).
                Escalate security+bugs to human.
  L3 — Unattended: Full auto-label + auto-assign priority.
                Escalate security only.
```

### Pattern 7: Changelog Drafter

```
ID:         changelog-drafter
Cadence:    1d or on release tag
Verifier:   NO
Worktree:   NO
State:      loop_state tracking last scanned commit
Skills:     changelog-scan, draft-release-notes
MCP:        GitHub read (merges, commits)
Max tokens: 100_000/run

Lifecycle:
  L0 — Draft.
  L1 — Draft:  Scan merges since last run. Produce RELEASE_NOTES_DRAFT.md.
                Human approves before publish.
  L2 — Edit:    Same, but writes to GH Release draft.
  L3 — Unattended: Same, human reviews before publish.
```

---

## 🧠 Maker/Checker (Verifier Sub-Agent)

The single most important structural pattern for reliable loops.

```python
# Pseudo-code for the verifier pattern inside any loop

async def run_with_verification(
    pattern: str,
    task: str,
    item: dict,
    worktree_path: Path | None,
) -> LoopResult:
    """Run implementer → verifier → decision."""
    
    # Phase 1: Implement (in worktree if provided)
    impl_params = LoopParams(
        task=task,
        pattern=LoopPattern.REACT,
        system_prompt=SKILLS["minimal-fix"],  # implementer skill
        tools=TOOLS["code"],  # read, write, edit, shell
        max_turns=10,
    )
    
    impl_result = await agent_loop(impl_params)
    
    # Phase 2: Verify (separate sub-agent, different session)
    verify_params = LoopParams(
        task=f"Verify this fix:\n\nTarget: {item}\n\nProposal: {impl_result.final_response}",
        pattern=LoopPattern.DIRECT,
        system_prompt=SKILLS["loop-verifier"],  # verifier skill
        tools=TOOLS["code"],  # needs to read files, run tests
        max_turns=5,
        temperature=0.3,  # lower temperature for verification
    )
    
    verify_result = await agent_loop(verify_params)
    
    # Phase 3: Decision
    verdict = parse_verdict(verify_result.final_response)
    # 'APPROVE' | 'REJECT' | 'ESCALATE_HUMAN'
    
    return LoopResult(
        pattern=pattern,
        item=item,
        impl_result=impl_result,
        verify_result=verify_result,
        verdict=verdict,
    )
```

**Rules:**
- Verifier must be a **separate sub-agent** from the implementer (different session, no shared context)
- Verifier's default stance: **REJECT until proven otherwise**
- Verifier **must run tests** (or equivalent) — not just read the diff
- If verifier cannot run tests (env issue) → `ESCALATE_HUMAN`
- Same model for both is fine, but **different instructions** and **no context sharing**

---

## 📊 Readiness Levels

```
L0 ─ Draft      Pattern registered, disabled, no runs
  │
L1 ─ Report     Triage → state update. No auto-action.
  │             Skill quality evaluated. Human reviews state daily.
  │
L2 ─ Assisted   Small auto-fixes with verifier + worktree.
  │             Denylist enforced. Budget set. Run log active.
  │
L3 ─ Unattended  Full autonomy. Budget + kill switch + observability.
                  Metrics tracked. Human gates documented.
```

### Gate Checklist

| Check | L1 | L2 | L3 |
|-------|----|----|----|
| Pattern registered | ✅ | ✅ | ✅ |
| Triage skill exists | ✅ | ✅ | ✅ |
| State file/schema | ✅ | ✅ | ✅ |
| State read+write on every run | ✅ | ✅ | ✅ |
| Prune resolved items | ✅ | ✅ | ✅ |
| Token budget set |    | ✅ | ✅ |
| Run log active |    | ✅ | ✅ |
| Denylist in skills |    | ✅ | ✅ |
| Verifier sub-agent |    | ✅ | ✅ |
| Worktree isolation |    | ✅* | ✅ |
| Connector permissions scoped |    | ✅ | ✅ |
| Human escalation protocol |    | ✅ | ✅ |
| Metrics tracked |    |    | ✅ |
| Kill switch |    |    | ✅ |
| Auto-PR allowlist |    |    | ✅ |

*Only for patterns that edit code

---

## 🔗 Integration Points

### Integration with Job Queue (SPEC_JOB_QUEUE_VISUAL_WORKFLOW.md)

Each loop instance is a **recurring job** in the PostgreSQL job queue:

```python
# Register a loop
job_queue.schedule_recurring(
    pattern="daily-triage",
    cadence_seconds=86400,
    handler="ai_workspace.loops.daily_triage.run",
    kwargs={"project_root": "/home/user/project"},
    max_retries=2,
)

# The queue fires the handler on cadence
# Handler loads state, runs triage, takes action, writes state
```

### Integration with Worktree Manager (SPEC_WORKTREE_MANAGER.md)

Patterns that edit code use the worktree manager:

```python
async with worktree_manager.acquire(pattern_id="pr-babysitter", item_id="PR#1234") as wt:
    # wt.path is a git worktree checked out at the PR's branch
    # Implementer edits files here
    # Verifier runs tests here
    # Worktree is cleaned up when context exits
```

### Integration with Agent Loop (SPEC_AGENT_LOOP.md)

Each loop's implementer phase calls `agent_loop()` with the appropriate pattern:

```python
result = await agent_loop(LoopParams(
    task=item.description,
    pattern=LoopPattern.REACT,  # most loops use ReAct
    system_prompt=load_skill("minimal-fix"),
    tools=load_tools_for_pattern("ci-sweeper"),
    max_turns=10,
    parallel_tools=True,
))
```

---

## ⚡ CLI Interface

```bash
# List all patterns
aiw loop list

# Show pattern detail
aiw loop show daily-triage

# Enable/disable a pattern at a readiness level
aiw loop enable daily-triage --level L1
aiw loop disable daily-triage

# Run a single cycle (ad-hoc, outside schedule)
aiw loop run daily-triage

# Show state for a pattern
aiw loop state daily-triage

# Show run log for a pattern
aiw loop log daily-triage --limit 20

# Show budget for a pattern
aiw loop budget daily-triage

# Set budget cap
aiw loop budget daily-triage --daily-cap 50000

# Pause/resume/kill
aiw loop pause daily-triage
aiw loop resume daily-triage
aiw loop kill daily-triage

# Run readiness audit (like loop-audit)
aiw loop audit
aiw loop audit --pattern daily-triage --suggest
```

---

## 🖥 TUI Integration

A new "Loops" tab in the TUI dashboard:

```
┌─────────────────────────────────────────────────────────┐
│  Loops (F6)                                             │
├──────────┬──────┬────────┬────────┬──────┬──────────────┤
│ Pattern  │Level │ Status │ Items  │ Spent│ Next Run     │
├──────────┼──────┼────────┼────────┼──────┼──────────────┤
│ Daily    │ L1   │ ▸ Running │ 3 act │ 12k  │ 07:00 BRT  │
│ PR Baby  │ L2   │ ◌ Paused │ 0 act  │ 0    │ (paused)   │
│ CI       │ L0   │ ○ Disab │ —      │ —    │ —           │
├──────────┴──────┴────────┴────────┴──────┴──────────────┤
│                                                          │
│  [Daily Triage — Last Run: 2026-06-27 07:01]             │
│                                                          │
│  Active:                                                  │
│  • CI red on main (test_auth_flaky)                    │
│    Attempts: 1/3 | Status: awaiting classification      │
│                                                          │
│  Watch:                                                   │
│  • PR #1423 — idle 3d | Last action: none               │
│                                                          │
│  Noise:                                                   │
│  • Dependabot PRs (separate automation)                 │
│                                                          │
│  [E]scalate  [R]etry  [P]ause  [K]ill  [L]og           │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Acceptance Criteria

- [ ] 7 patterns registered in `loop_patterns` table with seed migration
- [ ] `loop_state` table stores per-pattern state with active/watch/noise/pruned sections
- [ ] `loop_run_log` table captures every run with outcome, duration, tokens
- [ ] `loop_budget` table enforces daily caps with automatic pause
- [ ] Each pattern has a livecycle progression through L0→L3
- [ ] Maker/checker split: verifier is a separate sub-agent, never shares context with implementer
- [ ] Verifier default stance is REJECT; must run tests to approve
- [ ] `aiw loop list/show/enable/disable/run/state/log/budget/pause/resume/kill/audit` CLI commands
- [ ] Early exit for empty watchlist (<3k tokens)
- [ ] Max 3 fix attempts per item per run → escalate
- [ ] Safety: denylist, no auto-merge without allowlist, connector least privilege
- [ ] TUI "Loops" tab with per-pattern status, active items, controls

---

## 📚 References

- [loop-engineering patterns](https://github.com/cobusgreyling/loop-engineering/tree/main/patterns) — 7 canonical patterns
- [loop-engineering LOOP.md](https://github.com/cobusgreyling/loop-engineering/blob/main/LOOP.md) — multi-loop coordination
- [loop-design-checklist.md](https://github.com/cobusgreyling/loop-engineering/blob/main/docs/loop-design-checklist.md) — readiness gates
- [failure-modes.md](https://github.com/cobusgreyling/loop-engineering/blob/main/docs/failure-modes.md) — S1/S2/S3 failure catalog
- [operating-loops.md](https://github.com/cobusgreyling/loop-engineering/blob/main/docs/operating-loops.md) — cost, logging, metrics
- [safety.md](https://github.com/cobusgreyling/loop-engineering/blob/main/docs/safety.md) — path denylist, auto-merge policy
- SPEC_AGENT_LOOP.md — the execution engine that implementer phase calls
- SPEC_WORKTREE_MANAGER.md — git worktree abstraction for parallel isolation
- SPEC_JOB_QUEUE_VISUAL_WORKFLOW.md — PostgreSQL queue backing loop scheduling
