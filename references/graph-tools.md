# Code Review Graph Tools

PI's built-in knowledge graph for codebase analysis. **Always prefer these over grep/find.**

## Essential Workflow

```
build_or_update_graph          → Make sure graph is current
detect_changes                 → Risk-scored change analysis
get_impact_radius              → Find all affected code
get_review_context             → Focused review with source snippets
```

## Discovery

| Tool | Purpose |
|------|---------|
| `list_graph_stats` | Node counts, languages, coverage |
| `get_architecture_overview` | High-level module structure |
| `list_communities` | Code clusters/modules |
| `list_flows` | Execution flows by criticality |
| `find_large_functions` | Refactoring candidates |

## Search

| Tool | Purpose |
|------|---------|
| `semantic_search_nodes` | Find functions/classes by meaning |
| `semantic_search_nodes` + `kind=Function` | Filter by node type |
| `query_graph` + `callers_of` | Who calls this function? |
| `query_graph` + `callees_of` | What does this function call? |
| `query_graph` + `imports_of` | Module dependencies |
| `query_graph` + `importers_of` | Who imports this module? |
| `query_graph` + `tests_for` | Test coverage for a symbol |
| `query_graph` + `inheritors_of` | Subclasses of a base class |
| `query_graph` + `file_summary` | Overview of a file |

## Analysis

| Tool | Purpose |
|------|---------|
| `get_impact_radius` | Blast radius of changes |
| `get_affected_flows` | Critical paths at risk |
| `get_hub_nodes` | Most connected hotspots |
| `get_bridge_nodes` | Architectural chokepoints |
| `get_knowledge_gaps` | Isolated nodes, untested areas |
| `get_surprising_connections` | Unexpected coupling |
| `get_suggested_questions` | Auto-generated review questions |

## Traversal

| Tool | Purpose |
|------|---------|
| `traverse_graph` + `bfs`/`dfs` | Explore neighborhood of a symbol |
| `get_flow` | Details of a specific execution flow |
| `get_community` | Members of a code cluster |

## Refactoring

| Tool | Purpose |
|------|---------|
| `refactor_tool` + `dead_code` | Find unreferenced symbols |
| `refactor_tool` + `rename` | Preview renames |
| `apply_refactor_tool` | Execute a previewed refactor |

## Documentation

| Tool | Purpose |
|------|---------|
| `generate_wiki` | Auto-generate docs from graph |
| `get_wiki_page` | Read generated wiki page |
| `get_docs_section` | Read PI documentation |

## Multi-Repo

| Tool | Purpose |
|------|---------|
| `list_repos` | All registered repositories |
| `cross_repo_search` | Search symbols across repos |

## Tips

1. **Start every session** with `build_or_update_graph` if working with code
2. **Before modifying anything** run `get_impact_radius`
3. **For reviews** use `detect_changes` first, then `get_review_context`
4. **Finding code** use `semantic_search_nodes` instead of `grep`
5. **Understanding architecture** use `get_architecture_overview` + `list_communities`
