# PI Interactive Commands

Quick reference for commands in PI's interactive mode.

## Session Management

| Command | Action |
|---------|--------|
| `/new` | Start a new session |
| `/resume` | Browse past sessions |
| `/name <name>` | Set session display name |
| `/session` | Show session info |
| `/tree` | Navigate session tree, branch to any point |
| `/fork` | Create new session from a past message |
| `/clone` | Duplicate current branch into new session |
| `/compact [prompt]` | Summarize older messages |

## Model & Settings

| Command | Action |
|---------|--------|
| `/model` | Switch models (Ctrl+L) |
| `/scoped-models` | Enable/disable models for Ctrl+P cycling |
| `/settings` | Thinking level, theme, delivery, transport |
| `/thinking <level>` | off / minimal / low / medium / high / xhigh |

## Discovery & Reload

| Command | Action |
|---------|--------|
| `/reload` | Reload keybindings, extensions, skills, prompts, context files |
| `/hotkeys` | Show all keyboard shortcuts |
| `/changelog` | Display version history |

## Output

| Command | Action |
|---------|--------|
| `/copy` | Copy last assistant message to clipboard |
| `/export [file]` | Export session to HTML |
| `/share` | Upload as private GitHub gist |

## Editor Shortcuts

| Key | Action |
|-----|--------|
| `@` | Fuzzy-search project files |
| Tab | Path completion |
| Shift+Enter | Multi-line input |
| Ctrl+V | Paste images |
| `!command` | Run bash and send output to LLM |
| `!!command` | Run bash without sending |
| Ctrl+C | Clear editor |
| Escape | Cancel / abort |
| Ctrl+O | Collapse/expand tool output |
| Ctrl+T | Collapse/expand thinking blocks |
| Shift+Tab | Cycle thinking level |

## CLI Flags

```bash
pi -c                              # Continue most recent session
pi -r                              # Browse and resume sessions
pi --no-session                    # Ephemeral (don't save)
pi --session <id>                  # Use specific session
pi --fork <id>                     # Fork session into new one
pi -p "prompt"                     # Print mode (non-interactive)
pi --tools read,bash,edit,write    # Tool allowlist
pi --no-builtin-tools              # Disable built-in tools
pi --no-context-files              # Skip AGENTS.md loading
pi --thinking high                 # Set thinking level
```
