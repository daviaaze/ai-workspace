# Integração AI Workspace → nixfiles

> ⚠️ **STALE (2026-06-16):** Portas, hostnames e paths desatualizados.
> Para a configuração atual de deploy, veja [`BUILD_LOG.md`](./BUILD_LOG.md) seção "NixOS deployment on homelab".
> Hostname correto: `dvision-homelab`. Porta PostgreSQL: `2284`.

---

## Como adicionar ao seu flake.nix

### Passo 1: Adicionar input no `nixfiles/flake.nix`

```nix
inputs = {
    # ... seus inputs existentes ...

    ai-workspace = {
      url = "path:/home/daviaaze/Projects/ai-workspace";
      inputs.nixpkgs.follows = "nixpkgs";
    };
};
```

### Passo 2: Importar módulo no `dvision-thinkbook/default.nix`

```nix
{
  imports = [
    # ... seus imports existentes ...

    # AI Workspace module (pacote + systemd timers)
    inputs.ai-workspace.nixosModules.ai-workspace
  ];
}
```

### Passo 3: Configurar no mesmo arquivo

```nix
# Na sessão features (dentro do dvision-thinkbook/default.nix)
features = {
  # ... suas features existentes ...

  ai-workspace = {
    enable = true;

    database = {
      enable = true;
      url = "postgresql:///ai_workspace";
    };

    obsidian = {
      enable = true;
      vaultPath = "/home/daviaaze/Documents/Obsidian";  # ajuste
    };

    scheduling = {
      enable = false;  # Prefect é opcional e pesado
    };

    flows = {
      morningBriefing.enable = true;     # 7h BRT todo dia
      dailyResearch.enable = true;       # 8h BRT todo dia
      continuousLearning.enable = true;  # 2h BRT todo dia
      obsidianSync.enable = true;        # A cada 6h
    };
  };
};
```

### Passo 4: Adicionar no Home Manager (para aliases no shell)

No teu `home.nix` ou módulo home:

```nix
# Comandos do shell
programs.fish.shellAliases = {
  aiw-s = "aiw search";
  aiw-a = "aiw ask";
  aiw-t = "aiw task list";
  aiw-due = "aiw task due";
};
```

## Exemplo: pacote no category list

No `modules/shared/package-categories.nix`:

```nix
shared.packages.categories = {
  # ...
  cli = {
    # ...
    development = with pkgs; [
      pi-coding-agent
      opencode
      code-review-graph
      opencli
      ai-workspace  # ← adicionar aqui
    ];
  };
};
```

## Exemplo: integração com sua infra de agents

Seu diretório `.agents/skills/` já tem:
- `code-review/` — scripts que podem ser usados como tools
- `nixos-best-practices/` — referências para o agente coder

O AI Workspace pode importar essas skills como ferramentas do crewAI:

```python
# Dentro de um agente crewAI:
from crewai.tools import tool
import subprocess

@tool("code-review")
def run_code_review(path: str) -> str:
    """Run your code-review skill on a project path."""
    result = subprocess.run(
        ["python3", "~/.agents/skills/code-review/scripts/run_review.py"],
        cwd=path, capture_output=True, text=True
    )
    return result.stdout
```

## Ciclo de vida diário

```
07:00 → morning_briefing: sync Obsidian, gera briefing do dia
08:00 → daily_research: pesquisa tópicos configurados
09:00 → Você usa `aiw` durante o dia:
         - aiw search "alguma coisa"
         - aiw ask "pergunta rápida"
         - aiw task add "nova tarefa"
         - aiw memory add "aprendizado X"
02:00 → continuous_learning: extrai padrões, atualiza memória
```

## Dependências

Já instalado:
- ✅ Python 3.13
- ✅ PostgreSQL 17
- ✅ Ollama (gemma4, qwen3, deepseek-r1, etc.)
- ✅ Obsidian (via home-manager)

A instalar (via Nix ou pip):
- pip: crewai, mem0ai, pgvector, psycopg2, typer, rich
- pip (opcional): prefect
- db: extensão pgvector no PostgreSQL
