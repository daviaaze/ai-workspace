# Vision Model Pipeline — Image → Description → Action

> **Data:** 2026-06-17 | **Status:** 📋 Design | **Arquivos:** `agents/router.py`, `tui/worker.py`, `agents/orchestrator.py`

---

## 🎯 Problema

DeepSeek, qwen3 (text), e a maioria dos modelos de código são **text-only** — não conseguem processar imagens diretamente. Mas muitos casos de uso envolvem imagens:

- Screenshots de UI para análise de bugs
- Diagramas de arquitetura para documentação
- Logs/gráficos em PNG para debugging
- Fotos de whiteboard para transformar em tasks

Sem um pipeline de visão, o agente fica cego para entradas visuais — o usuário precisa descrever manualmente o que está na imagem, perdendo detalhes.

---

## 🧠 Solução: Pipeline de 2 Estágios

```
Imagem entra (PNG, JPG, WebP)
     │
     ▼
┌──────────────────────────────────┐
│ 1. Vision Model (local, grátis)  │
│    Ollama: llava, minicpm-v,     │
│    gemma3:12b (vision)           │
│    ─────────────────────────────│
│    Input:  "Describe this image  │
│             in detail for a      │
│             developer."          │
│    Output: "The screenshot shows │
│            a React error in      │
│            AuthModal.tsx line 42 │
│            with TypeError: ..."  │
└────────────┬─────────────────────┘
             │ text description
             ▼
┌──────────────────────────────────┐
│ 2. Reasoning Model (primary)     │
│    DeepSeek, qwen3, Gemini, etc. │
│    ─────────────────────────────│
│    Input:  "[Image description]  │
│             + User task: fix     │
│             this error"          │
│    Output: "The TypeError is      │
│            caused by..."         │
└──────────────────────────────────┘
```

O modelo de visão atua como um **tradutor**: imagem → texto. O modelo de raciocínio atua sobre o texto como sempre fez.

---

## 🤖 Modelos de Visão Disponíveis (Ollama)

| Modelo | Tamanho | RAM | Velocidade | Qualidade |
|--------|---------|-----|-----------|-----------|
| `llava:13b` | 7.4 GB | 8 GB | Média | Boa descrição geral |
| `llava:7b` | 4.1 GB | 4 GB | Rápida | OK para screenshots |
| `minicpm-v:8b` | 5.2 GB | 6 GB | Rápida | Excelente em OCR |
| `gemma3:12b` | 7.2 GB | 8 GB | Média | Melhor qualidade geral, suporta visão |
| `llama3.2-vision:11b` | 6.8 GB | 8 GB | Média | Muito boa em diagramas |
| `bakllava:7b` | 4.0 GB | 4 GB | Rápida | Leve, boa para screenshots |

**Recomendação:** `gemma3:12b` para qualidade, `minicpm-v:8b` para OCR/screenshots.

```bash
ollama pull gemma3:12b      # Melhor qualidade geral
ollama pull minicpm-v:8b    # Foco em OCR e screenshots
```

---

## 📊 Matriz de Roteamento (com Visão)

| Situação | Vision Model | Reasoning Model |
|----------|-------------|-----------------|
| Imagem + task de código | ollama/minicpm-v:8b ($0) | deepseek/deepseek-chat |
| Imagem + pesquisa | ollama/gemma3:12b ($0) | ollama/qwen3:14b |
| Imagem + chat rápido | ollama/llava:7b ($0) | ollama/ministral-3:8b |
| Múltiplas imagens | ollama/gemma3:12b ($0) | deepseek/deepseek-chat |
| Diagrama/arquitetura | ollama/llama3.2-vision:11b ($0) | deepseek/deepseek-reasoner |
| Texto puro (sem imagem) | ❌ skip vision | Router normal |

---

## 🔄 Fluxo no Orchestrator

```
AgentWorker._execute_via_orchestrator(task, images=[])
     │
     ├─ images? ──Não──▶ route(task) → execute → done
     │
     └─ Sim
         │
         ▼
    1. check_availability() → find best vision model available
         │
         ▼
    2. vision_describe(image, model) → text descriptions[]
         │  (parallel se múltiplas imagens)
         │
         ▼
    3. task = descriptions[] + original_task
         │
         ▼
    4. route(enhanced_task) → select reasoning model
         │
         ▼
    5. execute(enhanced_task) → result
```

---

## 🔌 Integrações

### 1. Router (`agents/router.py`)

Adicionar ao registro:
```python
# Vision models (Ollama local, free)
ModelInfo(name="gemma3:12b", provider="ollama",
          max_tokens=4096, speed="medium", priority=80,
          supports_tools=False, supports_vision=True),
ModelInfo(name="minicpm-v:8b", provider="ollama",
          max_tokens=4096, speed="fast", priority=85,
          supports_tools=False, supports_vision=True),
ModelInfo(name="llava:13b", provider="ollama",
          max_tokens=4096, speed="medium", priority=75,
          supports_tools=False, supports_vision=True),
```

Nova rota específica para visão:
```python
VISION_ROUTING = [
    ("ollama", "minicpm-v:8b"),    # Fast, good OCR
    ("ollama", "gemma3:12b"),      # Best quality
    ("ollama", "llava:13b"),       # Good fallback
    ("ollama", "llava:7b"),        # Light fallback
]
```

### 2. Worker (`tui/worker.py`)

Novo método no `AgentWorker`:
```python
async def vision_describe(self, image_path: str) -> str:
    """Describe an image using an Ollama vision model."""
    import base64, httpx
    
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{os.getenv('OLLAMA_HOST', 'http://localhost:11434')}/api/generate",
            json={
                "model": "minicpm-v:8b",
                "prompt": "Describe this image in detail for a software developer. "
                          "Include any text, error messages, UI elements, "
                          "diagrams, or code visible in the image.",
                "images": [image_b64],
                "stream": False,
            },
            timeout=60.0,
        )
        return resp.json()["response"]
```

### 3. Orchestrator (`agents/orchestrator.py`)

Pipeline estendido para aceitar imagens:
```python
class OrchestratorConfig:
    images: list[str] = []  # Paths to images to describe first

async def execute(task: str, images: list[str] = []) -> str:
    if images:
        descriptions = []
        for img in images:
            desc = await vision_describe(img)
            descriptions.append(f"[Image {img}]: {desc}")
        task = "\n\n".join(descriptions) + "\n\n---\n\n" + task
    return await route_and_execute(task)
```

### 4. TUI (`tui/app.py`)

Suporte a drag-and-drop ou paste de imagens:
```python
# Ctrl+V com imagem no clipboard → salva em /tmp → pipeline
# Drag de arquivo PNG → detecta extensão → pipeline de visão
```

---

## 💰 Custos

Todo o pipeline de visão é **custo zero** quando usando modelos Ollama locais:

| Estágio | Modelo | Custo |
|---------|--------|-------|
| Visão (descrever imagem) | ollama/minicpm-v:8b | $0 |
| Visão (descrever imagem) | ollama/gemma3:12b | $0 |
| Raciocínio (agir sobre descrição) | ollama/qwen3:14b | $0 |
| Raciocínio (agir sobre descrição) | deepseek/deepseek-chat | ~$0.0004 por task |

O único custo possível é se o modelo de raciocínio escolhido for pago (DeepSeek, Gemini, OpenRouter) — e mesmo assim, o custo é sobre o texto da descrição + task, não sobre a imagem.

---

## 🚦 Pré-requisitos

- [ ] Ollama rodando (`ollama serve`)
- [ ] Pelo menos 1 modelo de visão pulled (`ollama pull minicpm-v:8b`)
- [ ] RAM suficiente (4-8 GB livre para o modelo de visão)
- [ ] `ModelInfo.supports_vision` adicionado ao dataclass
- [ ] `VISION_ROUTING` no SmartRouter
- [ ] `vision_describe()` no AgentWorker
- [ ] Integração no Orchestrator
- [ ] Suporte a imagens no TUI input
