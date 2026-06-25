# PI Workspace Home Manager Module
# Installs AGENTS.md, skills, and prompts to ~/.pi/agent/
{
  config,
  lib,
  pkgs,
  ...
}:
with lib; let
  cfg = config.programs.pi.workspace;
  workspacePath = cfg.workspacePath;

  # AGENTS.md content
  agentsMd = pkgs.writeText "AGENTS.md" ''
    # AI Workspace — Personal Knowledge Base

    Your personal workspace lives at `${workspacePath}`. This is your "treasure map" — the central place where all persistent notes, plans, decisions, and learnings are stored.

    ## Folder Structure

    | Folder | Purpose |
    |---|---|
    | `Development/Features/Backlog/` | Tasks/features waiting to start |
    | `Development/Features/In-Progress/` | Active work |
    | `Development/Features/Done/` | Completed and shipped work |
    | `Projects/` | Project context: architecture, links, decisions |
    | `Research/` | Spikes, POCs, benchmarks |
    | `Technical-Decisions/` | Architecture Decision Records (ADRs) |
    | `References/` | Cheat sheets, commands, snippets |
    | `Templates/` | Reusable document models |
    | `Follow-ups-and-Blockers/` | Action items and blockers |
    | `Knowledge-Base/` | Docs and context |
    | `Prompts/` | Saved prompts |
    | `Processing/` | Inbox to process |
    | `Media-Inbox/` | Images and PDFs to process |
    | `Runbooks/` | How-to guides: deploy, debug, access |
    | `Code-Reviews/` | Review notes |
    | `Ideas-and-Backlog/` | Ideas for later |
    | `memory/` | Corrections and learnings from sessions |
    | `docs/` | External docs and guides |
    | `analysis/` | Analysis documents and investigations |

    ## Core Imperatives

    1. **Think First** — State assumptions explicitly. Ask rather than guess. Present trade-offs before choosing.
    2. **Simplicity First** — Minimum code that solves the problem. No speculative abstractions. No features beyond the ask.
    3. **Surgical Changes** — Touch only what the request requires. Match existing style. Don't refactor adjacent code.
    4. **Goal-Driven** — Define success criteria up front. Verify with tests before declaring done.

    ## Code Review Graph — ALWAYS Prefer Graph Tools

    Before exploring, reviewing, or modifying code, use PI's code-review-graph knowledge graph:

    1. **Before exploring**: `semantic_search_nodes` or `query_graph` instead of grep/find
    2. **Before reviewing**: `detect_changes` + `get_review_context` instead of reading entire files
    3. **Before modifying**: `get_impact_radius` to understand blast radius
    4. **For architecture**: `get_architecture_overview` + `list_communities`
    5. **For testing**: `query_graph` with `pattern="tests_for"` to check coverage

    Workflow:
    - Start with `build_or_update_graph` if unsure if graph is current
    - Use `detect_changes` for any review task
    - Use `get_impact_radius` to find affected code
    - Use `query_graph` callers_of/callees_of for dependency tracing
    - Fall back to read/bash ONLY when graph tools don't cover the need

    ## Workspace is Git-Tracked

    The workspace at `${workspacePath}` is a git repository. When skills modify workspace files (e.g., `/learn` updates memory, `/feature-dev` creates folders, `/onboard` writes project docs), **commit those changes** to keep history.

    ### Workspace Commit Rules
    - Verify branch ≠ `main`/`master` before commit (always work on a topic branch or confirm with user)
    - Stage only the files the skill modified — respect `.gitignore`
    - Use conventional commits with scope: `docs(memory):`, `feat(workspace):`, `refactor(templates):`
    - Keep commits single-concern
    - No AI co-authorship
    - **CONFIRM** before push — workspace is local-only for now

    ### When to Commit
    - After `/learn` saves to memory
    - After `/onboard` creates a project README
    - After `/feature-dev` moves a feature folder or writes plans
    - After `/adr` creates a decision record
    - After `/research` writes findings
    - After manually editing templates, references, or conventions

    ## Escalation

    - **STOP** — Ask first: prod DB migrations, infra apply, force push, delete branches, modify CI/CD
    - **CONFIRM** — Inform and wait: commit, push non-main, create PR, install deps, destructive local DB ops
    - **GO** — Auto-execute: read files, run tests, lint, format, dev server, stage files

    ## Skills-First Workflow

    Before any action, check available skills for a relevant one. If a skill matches, follow it exactly. If no skill matches, improvise but inform the user and ask if a new skill should be created.

    Available skills: `feature-dev`, `commit`, `create-pr`, `pre-review`, `debug`, `desloppify`, `learn`, `onboard`.

    ## Memory

    When something unexpected happens, use the `/skill:learn` skill to persist corrections to the workspace memory:
    - `memory/conventions.md` — rules and standards
    - `memory/project-patterns.md` — workflow patterns
    - `memory/learning-log.md` — date-tagged problems and solutions

    ## Workspace Behavior

    - When running INSIDE the workspace, use relative paths per the README.
    - When running OUTSIDE the workspace (e.g., in a project repo), skills that write persistent data must save to the central workspace using absolute paths.
    - When running OUTSIDE the workspace, read from workspace memory/templates when available.
  '';
in {
  options.programs.pi.workspace = {
    enable = mkEnableOption "PI workspace setup (AGENTS.md, skills, prompts)";

    workspacePath = mkOption {
      type = types.str;
      default = "/home/daviaaze/Projects/pessoal/ai-workspace";
      description = "Path to the PI workspace directory";
    };
  };

  config = mkIf cfg.enable {
    home.file = {
      # Global AGENTS.md
      ".pi/agent/AGENTS.md".source = agentsMd;

      # Skills
      ".pi/agent/skills/feature-dev/SKILL.md".text = ''
        ---
        name: feature-dev
        description: Start and work through a feature or task end-to-end. Use when the user says implement, build, start a feature, work on a task, or wants to plan and execute development work.
        ---

        # Feature Development Workflow

        ## Trigger
        Implement, build, start a feature, work on a task, develop something.

        ## Workflow

        ### Phase 1: Understand
        - Read the task description. Ask clarifying questions on acceptance criteria, edge cases, dependencies.
        - State your understanding before proceeding.

        ### Phase 2: Plan
        - Use PI graph tools to analyze codebase: `semantic_search_nodes`, `query_graph`, `get_impact_radius`.
        - Break implementation into small, testable steps.
        - Identify files to change and test coverage needed.
        - Ask user for approval before implementing.

        ### Phase 3: Implement
        - One step at a time. Run tests after each significant change.
        - Follow global rule imperatives and stack conventions.
        - Use graph tools to verify impact: `get_impact_radius`, `get_affected_flows`.

        ### Phase 4: Verify & Deliver
        - Run final tests. Execute `/skill:desloppify`. Execute `/skill:commit`. Execute `/skill:create-pr`.
        - If feature artifacts were modified in the workspace (analysis, plan, notes), commit those too with `docs(features):` scope.

        ## Workspace Integration
        - Feature folders live at `${workspacePath}/Development/Features/`
        - New tasks start in `Backlog/`, move to `In-Progress/`, then `Done/`
        - Each feature folder: `ticket.md`, `analysis.md`, `plan.md`, `notes.md`

        ## Exit Points
        Each phase is an exit point. Resume later by re-running the skill.
      '';

      ".pi/agent/skills/commit/SKILL.md".text = ''
        ---
        name: commit
        description: Create a safe git commit with a conventional commit message. Use when the user says commit, wants to save changes, or asks to stage and commit.
        ---

        # Safe Commit Workflow

        ## Trigger
        Commit, save changes, stage and commit.

        ## Workflow

        1. **Verify branch** — `git branch --show-current`. If `main`/`master`, STOP and warn.
        2. **Review changes** — `git status` + `git diff` (or `--cached`). Summarize in user-friendly terms.
        3. **Stage** — ask which files, or stage all if confirmed.
        4. **Generate message** — determine type (`feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `security`). Short description ≤50 chars. Bullet points for details.
        5. **Commit** — execute `git commit`. Confirm success.
        6. **Suggest next** — `/skill:create-pr` or `git push` (with escalation check).

        ## Conventional Commit Types
        - `feat:` — new feature
        - `fix:` — bug fix
        - `refactor:` — code change that neither fixes a bug nor adds a feature
        - `docs:` — documentation only
        - `test:` — adding or correcting tests
        - `chore:` — maintenance, deps, tooling
        - `perf:` — performance improvement
        - `security:` — security fix
      '';

      ".pi/agent/skills/create-pr/SKILL.md".text = ''
        ---
        name: create-pr
        description: Create a pull request with description and test table. Use when the user says create PR, open pull request, or asks to publish changes after committing.
        ---

        # PR Creation Workflow

        ## Trigger
        Create PR, open pull request, publish changes.

        ## Workflow

        1. **Gather context** — `git log --oneline`, `git diff main...HEAD --stat`. Read feature doc if exists in workspace.
        2. **Generate description** — what changed and why. Type of change. Link to task/issue.
        3. **Test table** — scenarios tested and results.
        4. **Create** — use `gh pr create` or equivalent. Add labels if repo uses them.
        5. **Notify** — share PR URL. Remind about manual steps (screenshots, manual testing).

        ## PR Template

        ```markdown
        ## What Changed
        Brief description.

        ## Why
        Motivation.

        ## Type
        - [ ] feat / fix / refactor / docs / test / chore / perf / security

        ## Test Results
        | Scenario | Status |
        |----------|--------|
        | | |

        ## Checklist
        - [ ] Tests pass
        - [ ] Lint passes
        - [ ] Type-check passes
        - [ ] Manual testing done
        ```

        ## Workspace Integration
        If a feature folder exists at `${workspacePath}/Development/Features/In-Progress/`, read its `plan.md` and `notes.md` for context.
      '';

      ".pi/agent/skills/pre-review/SKILL.md".text = ''
        ---
        name: pre-review
        description: Self-review code before opening a PR. Use when the user says review my code, check this PR, pre-review, or wants to validate changes before publishing.
        ---

        # Pre-Review Workflow

        ## Trigger
        Review my code, check this PR, pre-review, validate changes.

        ## Workflow

        1. **Get diff** — `git diff main...HEAD`. Identify changed files.
        2. **Use graph tools** — run `detect_changes` and `get_review_context` for focused review.
        3. **Self-check** — evaluate against quality dimensions:
           - Correctness, readability, test coverage, error handling, performance, security, maintainability, consistency, documentation, observability, backward compatibility, edge cases
        4. **Flag issues**:
           - 🟢 Pass — meets standard
           - 🟡 Warning — could be improved
           - 🔴 Block — must fix before PR
        5. **Report** — files changed, critical/warning counts, overall status.
        6. **Suggest fixes** — offer to apply 🔴/🟡 automatically with user confirmation.

        ## Quality Dimensions

        1. **Correctness** — Does it do what was asked? Edge cases handled?
        2. **Readability** — Can a new engineer understand this in 30 seconds?
        3. **Test Coverage** — Tests for happy path and edge cases?
        4. **Error Handling** — Graceful errors, properly logged?
        5. **Performance** — No N+1 queries, unnecessary blocking ops?
        6. **Security** — Input validation, no secrets in code?
        7. **Maintainability** — Easy to change without breaking things?
        8. **Consistency** — Matches existing codebase patterns?
        9. **Documentation** — Complex areas explained?
        10. **Observability** — Logs, metrics, traces for debugging?
        11. **Backward Compatibility** — Doesn't break existing consumers?
        12. **Edge Cases** — Nulls, empty arrays, timeouts, race conditions?
      '';

      ".pi/agent/skills/debug/SKILL.md".text = ''
        ---
        name: debug
        description: Hypothesis-driven debugging. Use when tests are failing, there's a bug, the user says debug, find the bug, or something is not working as expected.
        ---

        # Debug Workflow

        ## Trigger
        Debug, find the bug, tests failing, something not working.

        ## Workflow

        1. **Understand** — read errors and stack traces. Ask about expected vs actual behavior. Check recent commits.
        2. **Hypothesize** — list 2-3 most likely causes, ranked by probability.
        3. **Instrument** — add targeted logs at function entry/exit, state changes, external API calls, DB queries. Use structured JSON logging.
        4. **Observe** — run failing scenario. Capture logs. Validate or invalidate hypotheses.
        5. **Propose fix** — present root cause. Offer 2-3 options with trade-offs. Recommend best.
        6. **Apply and verify** — apply chosen fix. Run tests. Run original failing scenario.
        7. **Clean up** — remove debug logs. Verify no performance impact.

        ## General Debugging Rules
        - Reproduce consistently before fixing.
        - Change one thing at a time.
        - Verify the fix with the original failing scenario.

        ## Language-Specific Tips
        - **TypeScript/Node**: `console.log(JSON.stringify(state, null, 2))`, `--inspect` + Chrome DevTools
        - **Python**: `breakpoint()`, `python -m pdb`
        - **Go**: `dlv debug`, `log.Printf("%+v", struct)`
        - **Rust**: `dbg!(&value)`, `RUST_LOG=debug`
        - **Database**: enable query logging, EXPLAIN for slow queries
      '';

      ".pi/agent/skills/desloppify/SKILL.md".text = ''
        ---
        name: desloppify
        description: Clean up AI-generated code artifacts. Use after AI generates code, when the user says clean up, polish, or remove AI cruft.
        ---

        # Desloppify Workflow

        ## Trigger
        Clean up, polish, remove AI cruft, after AI-generated code.

        ## Workflow

        1. **Remove dead code** — unused imports, dead paths, commented-out code.
        2. **Remove redundant comments** — keep only WHY, not WHAT. Delete AI-generated summary comments.
        3. **Remove unnecessary casts** — keep only when they add safety.
        4. **Simplify expressions** — break nested ternaries, extract complex conditions, apply early returns.
        5. **Standardize formatting** — run project's formatter. Consistent import ordering.
        6. **Naming review** — meaningful names, match codebase conventions.
        7. **Validate** — run tests and linter. Report what changed.

        ## Output
        - Files modified
        - Issue types fixed (counts)
        - Any manual review items
      '';

      ".pi/agent/skills/learn/SKILL.md".text = ''
        ---
        name: learn
        description: Persist a correction or learning from a session. Use when something unexpected happened, the user says remember this, don't do this again, or wants to save a convention/pattern for future sessions.
        ---

        # Learn Workflow

        ## Trigger
        Remember this, don't do this again, save this convention, unexpected behavior.

        ## Workflow

        1. **Capture** — what happened? What was the mistake? What is the correct approach?
        2. **Categorize**:
           - Rules issue → `memory/conventions.md` (or `Technical-Decisions/` if architectural)
           - Skill gap → `memory/project-patterns.md` (or `References/` if reusable snippet)
           - Context issue → `memory/learning-log.md` (or `Projects/` if project-specific)
        3. **Save** — append to the appropriate file with date and topic.
        4. **Commit** — if inside the workspace git repo, stage the modified memory file and commit with `docs(memory): <topic>`.
        5. **Confirm** — tell user what was saved, where, and the commit hash.

        ## Memory Files
        All paths are in `${workspacePath}/`:
        - `memory/conventions.md` — conventions and standards
        - `memory/project-patterns.md` — workflow patterns and file locations
        - `memory/learning-log.md` — date-tagged problems and solutions

        ## Format

        ```markdown
        ### YYYY-MM-DD — Topic

        **Problem:**
        What went wrong?

        **Solution:**
        What was the fix or correct approach?

        **Reference:**
        Link to file, PR, or doc.
        ```
      '';

      ".pi/agent/skills/onboard/SKILL.md".text = ''
        ---
        name: onboard
        description: Analyze a new repository and create a project context folder in the workspace. Use when entering a new codebase, starting work on a new project, or the user says onboard, analyze this repo, or understand this project.
        ---

        # Onboard Workflow

        ## Trigger
        Onboard, analyze this repo, understand this project, entering a new codebase.

        ## Workflow

        1. **Identify** — determine repo name, primary language, framework.
        2. **Graph build** — run `build_or_update_graph` to index the codebase.
        3. **Architecture** — `get_architecture_overview` + `list_communities` for module structure.
        4. **Hotspots** — `get_hub_nodes` for most connected files, `get_bridge_nodes` for chokepoints.
        5. **Key files** — `list_flows` for critical execution paths, `find_large_functions` for refactoring candidates.
        6. **Document** — create `${workspacePath}/Projects/<repo-name>/README.md` with findings.
        7. **Commit** — stage the new project README and commit with `docs(projects): onboard <repo-name>`.

        ## Output: Project README

        ```markdown
        # Project: {name}

        **Status:** onboarded
        **Date:** {date}
        **Language:** {primary}
        **Framework:** {framework}

        ## Architecture
        High-level module structure and data flow.

        ## Key Files
        | File | Role |
        |------|------|

        ## Hotspots
        Most connected / critical nodes.

        ## Entry Points
        Main execution flows.

        ## Decisions
        Link to ADRs in `Technical-Decisions/`.

        ## Risks
        Knowledge gaps, thin communities, untested hotspots.
        ```

        ## Exit Points
        - After graph build (can resume)
        - After architecture overview
        - After full documentation
      '';

      # Prompts
      ".pi/agent/prompts/adr.md".text = ''
        ---
        description: Create an Architecture Decision Record
        argument-hint: "<title>"
        ---

        Create an ADR at `${workspacePath}/Technical-Decisions/ADR-NNN-$1.md` with:

        - Status: proposed
        - Context: what problem are we solving?
        - Decision: what did we decide?
        - Consequences: what becomes easier or harder?
        - Alternatives considered

        Use the next available ADR number.
      '';

      ".pi/agent/prompts/feature.md".text = ''
        ---
        description: Start a new feature or task
        argument-hint: "<feature-name>"
        ---

        Create a feature folder at `${workspacePath}/Development/Features/Backlog/$1/` with:

        - `ticket.md`: capture requirements and acceptance criteria
        - `analysis.md`: (to be filled with codebase analysis)
        - `plan.md`: (to be filled with implementation plan)

        Ask the user for requirements if not provided.
      '';

      ".pi/agent/prompts/research.md".text = ''
        ---
        description: Start a research spike or investigation
        argument-hint: "<topic>"
        ---

        Create a research document at `${workspacePath}/Research/$1.md` with:

        - Goal: what question are we trying to answer?
        - Approach: how will we investigate?
        - Findings: (to be filled)
        - Conclusion: (to be filled)
        - Recommendation: (to be filled)

        Use the research template from `Templates/research.md` if it exists.
      '';

      ".pi/agent/prompts/learn.md".text = ''
        ---
        description: Save a correction or learning from this session
        argument-hint: "[topic]"
        ---

        Save the most recent unexpected behavior or correction to the workspace memory. Categorize:

        - Rules issue → `memory/conventions.md`
        - Skill/workflow gap → `memory/project-patterns.md`
        - Context/one-off → `memory/learning-log.md`

        Topic: $1
      '';

      ".pi/agent/prompts/review.md".text = ''
        ---
        description: Review code changes before committing
        argument-hint: "[focus area]"
        ---

        Review the current changes (`git diff` or `git diff --cached`).

        Focus areas: $1 (default: all)

        Check for:
        - Bugs and logic errors
        - Security issues (input validation, secrets, injection)
        - Error handling gaps
        - Performance problems (N+1, blocking ops)
        - Test coverage
        - Code readability and naming

        Use `detect_changes` and `get_review_context` if available.
      '';

      ".pi/agent/prompts/analyze.md".text = ''
        ---
        description: Analyze a codebase or module deeply
        argument-hint: "<module-or-topic>"
        ---

        Deep analysis of: $1

        Steps:
        1. `build_or_update_graph` if not current
        2. `get_architecture_overview` for high-level structure
        3. `list_communities` to find clusters
        4. `semantic_search_nodes` for relevant symbols
        5. `get_hub_nodes` for architectural hotspots
        6. `get_knowledge_gaps` for weak spots

        Output:
        - Architecture summary
        - Key files and their roles
        - Hotspots (highly connected nodes)
        - Knowledge gaps
        - Suggested improvements
      '';

      ".pi/agent/prompts/summarize.md".text = ''
        ---
        description: Summarize a file, PR, or topic
        argument-hint: "<file-or-topic>"
        ---

        Summarize: $1

        - What is this?
        - Key components
        - How it fits in the broader system
        - Any issues or risks visible
      '';

      ".pi/agent/prompts/test.md".text = ''
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
      '';

      ".pi/agent/prompts/explain.md".text = ''
        ---
        description: Explain how code works
        argument-hint: "<file-or-function>"
        ---

        Explain: $1

        - What does this do at a high level?
        - Walk through the key logic step by step
        - What are the inputs and outputs?
        - Any non-obvious tricks or conventions?
        - How does it fit into the broader system?
      '';

      ".pi/agent/prompts/refactor.md".text = ''
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
      '';
    };
  };
}
