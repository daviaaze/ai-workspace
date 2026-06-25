# PI Setup — Rules & Skills

Lean, stack-agnostic rules and skills for the PI coding agent harness.

## How It Works

PI automatically loads context from `~/.pi/agent/AGENTS.md` in **every session** — this is your workspace map, conventions, and core imperatives. Skills and prompt templates are loaded **on-demand** when the task matches their description.

## What's Included

### Global Context (`~/.pi/agent/AGENTS.md`)
Loaded automatically in every PI session. Contains:
- Workspace path and folder structure
- Core imperatives (Think First, Simplicity First, Surgical Changes, Goal-Driven)
- Code-review-graph tool preferences
- Git conventions
- Escalation rules
- Skills-first workflow instructions

### Skills (loaded on-demand)
| Skill | Trigger | Purpose |
|-------|---------|---------|
| `feature-dev` | "implement", "build", "start a feature" | 4-phase feature workflow |
| `commit` | "commit", "save changes" | Safe commit with conventional messages |
| `create-pr` | "create PR", "open pull request" | PR creation with template |
| `pre-review` | "review my code", "check this PR" | Self-review with graph tools |
| `debug` | "debug", "find the bug" | Hypothesis-driven debugging |
| `desloppify` | "clean up", "polish" | Clean AI artifacts |
| `learn` | "remember this", "don't do this again" | Persist corrections to memory |
| `onboard` | "onboard", "analyze this repo" | Analyze new codebase, create project context |

### Prompt Templates (quick `/name` expansions)
| Template | Command | Purpose |
|----------|---------|---------|
| `adr` | `/adr <title>` | Create Architecture Decision Record |
| `feature` | `/feature <name>` | Start a new feature folder |
| `research` | `/research <topic>` | Start a research spike |
| `learn` | `/learn [topic]` | Save a correction to memory |
| `review` | `/review [focus]` | Review current git diff |
| `analyze` | `/analyze <module>` | Deep codebase analysis |
| `summarize` | `/summarize <topic>` | Summarize file, PR, or topic |
| `test` | `/test <file>` | Generate tests |
| `explain` | `/explain <code>` | Explain how code works |
| `refactor` | `/refactor <file>` | Plan a refactoring |

## Nix / Home Manager Integration

A declarative Home Manager module is included at `pi-setup/nix/pi-workspace.nix`. When enabled, it manages:
- `~/.pi/agent/AGENTS.md`
- `~/.pi/agent/skills/*`
- `~/.pi/agent/prompts/*`

### Add to your flake

**1. Export the module** in `modules/flake-parts/home-manager.nix`:
```nix
flake.homeModules = {
  # ... existing modules ...
  pi-workspace = ../home/features/pi-workspace.nix;
};
```

**2. Copy the module** to your nixfiles:
```bash
cp pi-setup/nix/pi-workspace.nix ~/nixfiles/modules/home/features/pi-workspace.nix
```

**3. Enable in your host config**:
```nix
home-manager.users.youruser = {
  imports = [
    self.homeModules.cli
    self.homeModules.pi-workspace
    # ... other modules ...
  ];

  features.home = {
    cli.enable = true;
    pi-workspace = {
      enable = true;
      workspacePath = "/home/daviaaze/Projects/pessoal/ai-workspace";
    };
  };
};
```

## Manual Installation

### Already installed globally
If you see this in `~/.pi/agent/`, you're done:
```
~/.pi/agent/
├── AGENTS.md
├── skills/
│   ├── feature-dev/SKILL.md
│   ├── commit/SKILL.md
│   ├── create-pr/SKILL.md
│   ├── pre-review/SKILL.md
│   ├── debug/SKILL.md
│   ├── desloppify/SKILL.md
│   ├── learn/SKILL.md
│   └── onboard/SKILL.md
└── prompts/
    ├── adr.md
    ├── feature.md
    ├── research.md
    ├── learn.md
    ├── review.md
    ├── analyze.md
    ├── summarize.md
    ├── test.md
    ├── explain.md
    └── refactor.md
```

### From this workspace
To install or update manually:
```bash
# Copy AGENTS.md
cp pi-setup/rules/00-global.md ~/.pi/agent/AGENTS.md

# Copy skills (each needs its own directory with SKILL.md)
for skill in feature-dev commit create-pr pre-review debug desloppify learn onboard; do
  mkdir -p ~/.pi/agent/skills/$skill
  cp pi-setup/skills/$skill.md ~/.pi/agent/skills/$skill/SKILL.md 2>/dev/null || true
done

# Copy prompts
cp pi-setup/prompts/*.md ~/.pi/agent/prompts/ 2>/dev/null || true
```

**Note:** The skills in `pi-setup/skills/` are markdown reference files. The actual PI skills live in `~/.pi/agent/skills/<name>/SKILL.md` and follow the [Agent Skills standard](https://agentskills.io).

## How PI Uses This

1. **Every session starts** by loading `~/.pi/agent/AGENTS.md` — PI immediately knows about the workspace, its structure, and your conventions.
2. **When you say** "implement this feature", PI reads the `feature-dev` skill description, matches it, loads the full `SKILL.md`, and follows the workflow.
3. **Skills auto-populate** the workspace — creating feature folders, writing plans, saving to memory, etc.
4. **Prompt templates** give you quick commands like `/adr caching-strategy` to create documents instantly.

## Workspace Setup

Your workspace lives at `/home/daviaaze/Projects/pessoal/ai-workspace`. PI always knows this path from `AGENTS.md`.

| Directory | Used By |
|-----------|---------|
| `Development/Features/Backlog/` | `feature-dev` — new tasks start here |
| `Development/Features/In-Progress/` | `feature-dev` — active work |
| `Development/Features/Done/` | `feature-dev` — completed work |
| `Projects/` | `onboard` — project context |
| `Knowledge-Base/` | `feature-dev` — docs and context |
| `Runbooks/` | operational guides |
| `Templates/` | reusable formats |
| `memory/` | `learn` — persistent corrections |
| `Technical-Decisions/` | ADRs |
| `Research/` | `research` prompt — spikes and POCs |

## Customization

### Add a new skill
1. Create `~/.pi/agent/skills/my-skill/SKILL.md`
2. Add frontmatter: `name: my-skill` and `description: What it does`
3. Write workflow instructions

### Add a new prompt template
1. Create `~/.pi/agent/prompts/my-template.md`
2. Add frontmatter: `description: What it does`
3. Write the prompt expansion
4. Invoke with `/my-template`

### Modify global context
Edit `~/.pi/agent/AGENTS.md` to adjust workspace path, stack versions, or escalation levels.

## Learning Cycle

| Problem | Action |
|---------|--------|
| PI repeats a mistake | Adjust `AGENTS.md` or the corresponding **Rule** |
| PI skips a step | Adjust the corresponding **Skill** |
| PI didn't know something | Use `/learn` to save to **memory/** |

> "Every time the agent does something unexpected, it's a signal we need to adjust the setup."
