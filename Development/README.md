# Development

Feature development workspace. Each feature gets its own folder, organised by status.

## Status Folders

Features move between folders as they progress:

```
Features/
  Backlog/          ← New features start here
  In-Progress/      ← Actively being worked on
  Done/             ← Shipped and verified
```

- **Backlog/** — Ticket captured, maybe analysed, not yet started.
- **In-Progress/** — Actively being developed. Move the feature folder here when work begins.
- **Done/** — Merged, deployed, verified. Move the feature folder here when the work is shipped.

### Moving a feature

Simply move the entire feature folder between status folders:

```
Features/Backlog/my-feature/  →  Features/In-Progress/my-feature/  →  Features/Done/my-feature/
```

In Obsidian, drag the folder in the file explorer. All internal `[[wikilinks]]` resolve by name, so they survive moves.

## Feature Workflow

1. **Raw ticket** — Create `Features/Backlog/<feature-name>/ticket.md` with requirements and acceptance criteria.
2. **Knowledge base search** — Check `Knowledge-Base/` for related docs, past decisions, and domain context.
3. **Codebase analysis** — Use PI graph tools (`semantic_search_nodes`, `query_graph`, `get_impact_radius`) to identify relevant services, files, and patterns. Note findings in `analysis.md`.
4. **Plan** — Write the implementation plan in `plan.md` covering approach, affected services, risks, and testing strategy.
5. **Start work** — Move the folder to `Features/In-Progress/`.
6. **Ship** — Move the folder to `Features/Done/`.

## Folder Structure per Feature

```
<feature-name>/
  ticket.md      # Raw ticket / requirements
  analysis.md    # Codebase findings (use PI graph tools)
  plan.md        # Implementation plan
  notes.md       # Optional: ongoing dev notes
```
