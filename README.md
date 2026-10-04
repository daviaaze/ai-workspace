# AI Workspace

A repository of native OMP skills, standalone tools and a knowledge base. The former AIW application, its Python backend, web/TUI clients, worker, MCP server and deployment integrations have been removed.

## Native OMP skills

The 11 repository-authored skills live in [`.omp/skills/`](.omp/skills/SKILL_CATALOG.md): `commit`, `create-pr`, `daily`, `debug`, `deep-research`, `desloppify`, `feature-dev`, `learn`, `nixfiles`, `onboard` and `pre-review`.

Start your host-provided OMP in this repository to discover them:

```bash
omp --cwd "$PWD"
```

Use commands such as `/skill:debug` or `/skill:feature-dev`. No AIW package, database, Python environment or project MCP server is required for these skills. Models, credentials, extensions and safety settings belong to the active host/profile configuration; this repository does not install or enable them. See [USAGE.md](USAGE.md).

## Independent tools and documents

- [`career-ops/`](career-ops/) and [`Projects/leilao-radar/`](Projects/leilao-radar/) remain independent projects with their own setup.
- [`.pi/skills/job-tracker/`](.pi/skills/job-tracker/) and [`.pi/skills/browser-companion/`](.pi/skills/browser-companion/) retain their standalone scripts. The `aiw-job*` command names do not imply a dependency on the removed AIW application.
- Knowledge bases, ERPNext/Frappe reference material, research, templates, project notes and Ostranauts sources/documents are retained.
- UI-design skill guidance remains available for text-based design work, without the removed AIW MCP/Pi tooling.

## Maintenance

```bash
nix develop
```

The flake provides a generic maintenance shell and the existing formatter. It no longer exports AIW application packages, apps or a worker module. Independent tools use their own dependency/setup instructions.

## Historical documentation

The former application's design, research and release history remain in [`docs/`](docs/README.md), analysis/archive material and [CHANGELOG.md](CHANGELOG.md). Their AIW commands and source paths are historical, not current setup instructions.

### Ostranauts mod docs

| Doc | Topic |
|-----|-------|
| [ostranauts-modding-quickref.md](ostranauts-modding-quickref.md) | Quick reference das APIs essenciais |
| [ostranauts-api-reference.md](ostranauts-api-reference.md) | API completa (CondOwner, Task2, Ship, Powered…) |
| [ostranauts-ai-architecture.md](ostranauts-ai-architecture.md) | Arquitetura de IA / interações / pledges |
| [ostranauts-battery-workflow.md](ostranauts-battery-workflow.md) | Workflow de bateria + bug Forbidden:Carried |
| [ostranauts-logistics-mod-plan.md](ostranauts-logistics-mod-plan.md) | Plano do idle-pledge de organização/logística |
| [ostranauts-roadmap-master.md](ostranauts-roadmap-master.md) | Plano mestre de todas as frentes em aberto |
| [ostranauts-mod-replacement-plan.md](ostranauts-mod-replacement-plan.md) | Plano de substituição dos mods de workshop |
| [ostranauts-getwork-throttle-plan.md](ostranauts-getwork-throttle-plan.md) | Plano de otimização do GetWork/ProcessAutoTasks |
| [ostranauts-optimization-audit.md](ostranauts-optimization-audit.md) | Auditoria de performance |
| [ostranauts-optimization-learnings.md](ostranauts-optimization-learnings.md) | Lições de otimização + anti-padrões |

## License

MIT
