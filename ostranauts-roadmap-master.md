# Ostranauts — Plano Mestre (Roadmap Completo)

> **Visão geral de todas as frentes em aberto**, consolidadas. Cada frente referencia sua
> doc detalhada. Status atualizado em 2026-08-16.
> Jogo 1.0.0.9, BepInEx 5.4.23.5, Proton/Wayland, netstandard2.1 C# 9.0.
> Docs-fonte: `ostranauts-*.md` no workspace + `/tmp/game_api_full/` (612 .cs decompilados).

---

## 0. Estado do ambiente (happy path confirmado)

| Item | Valor |
|---|---|
| Launch options Steam | `DRI_PRIME=1 WINEDLLOVERRIDES="winhttp.dll=n,b" %command%` |
| BepInEx core | `0Harmony.dll`, `BepInEx.dll` presentes em `BepInEx/core/` |
| Live log | `Player.log` (forma `Debug.Log`) — **BepInEx `LogOutput.log` é bufferizado** |
| dotnet build | `nix-shell -p dotnet-sdk_8 --run`, csproj HintPaths **resolvidos** `/home/daviaaze/.local/share/Steam/...` |

> **Regra de ouro de live-debug:** logar via `UnityEngine.Debug.Log` (vai p/ `Player.log`,
> flush confiável), **nunca** confiar em `LogOutput.log` (bufferizado, só dumps no start/exit).

---

## 1. Frentes ativas por tema

### 1A. Mods plugin ativos hoje (BepInEx/plugins/)
`BatteryCare`, `BatteryRechargeFix`, `GetCOsOpt`, `GetWorkThrottle`, `ItemOverlayThrottle`,
`OstBattFix`, `OstranautsOpt`, `OstranautsSimDiag`, `SeekSocialCache`, `WorkClaimThrottle`
(+ framework).

> ⚠️ **Nota de limpeza:** há 3 mods de bateria (`BatteryCare`, `BatteryRechargeFix`,
> `OstBattFix`) que fazem coisas parecidas/sobrepostas — possivelmente conflitam. Ver §4.

---

## 2. Roadmap por frente

### Frente A — Otimização de performance (documentada em `ostranauts-optimization-audit.md`)

**Já implementado (10 fixos, A1–A9 + battery):** NoCopy, PreSizeCondsTemp, NoTickerLog,
FirstOrDefault, ProcessAutoTasks cooldown (GetWorkThrottle), VisualizeOverlays throttle
(ItemOverlayThrottle), ClaimNextTask throttle (WorkClaimThrottle), GetCOs visitor (GetCOsOpt),
SeekSocialDeny cache (SeekSocialCache). Estado consolidado na tabela A1–A9:
`ostranauts-optimization-audit.md`.

**Restante (por prioridade):**
- ⏸️ **Fix 3 — `GetMove2` Dictionary reusável** — **SKIPPED_WARNING**: requer substituição total do
  método (1000+ linhas); não habilitar `Patch_GetMove2_Cache` às cegas (doc: audit §3).
- [ ] **Fix 4 — `EndTurn` `aCondsTemp.AddRange` → iteração direta** (Transpiler, baixo risco, médio ganho).
- [ ] **Fix 5 — `TriggeredInternal` CTTest3rd cache** (verificar se `SeekSocialDeny` tem CTTest3rd).
- [ ] **Fix 6 — `ClaimNextTask` HashSet em vez de `List.IndexOf`** (quando roda).
- [ ] **Fix 7—8 — `HandleHaulTask`/`HandleFeedTask` reuse de dict/interactions.**
- [ ] **Fix 9–13 — remove O(n) em aTickers/aManUpdates/UpdateStats/etc. (low).**
- [ ] **Validação de dose/impacto por perf** (externo `perf` + jitmap não disponível sob Wine → usar SIM-DIAG).

> ⚠️ Lição crítica: **não instrumentar hot-paths por frame** (causou lag). Aprovação de cada
> Transpiler com teste de regressão.

### Frente B — Mod de logística/organização em idle (doc: `ostranauts-logistics-mod-plan.md`)

**Problema:** haul despeja tudo no chão (L1); bins/containers (L2) ficam vazios.
**Solução:** idle-pledge `PledgeOrganize` (ponte L1→L2) + empacotamento 2D + multi-haul.

- [ ] Data-mod: `pledges.json` (`strType:"organize"`, `nPriority:1`) + `mod_info.json`.
- [ ] Registro do pledge no `PledgeFactory` (postfix, evitando editar `dictTypes`).
- [ ] `PledgeOrganize.Do()` MVP — multi-item + slots + dolly.
- [ ] Empacotamento 2D (Tetris/BFH) para chão e container.
- [ ] Roteamento L1→L2 (bins por `ctAllowed`).
- [ ] Aninhamento bolsa-em-baú, respeito a bins oversized.
- [ ] Build + install + teste em idle.

### Frente C — Mods de bateria (docs: `battery-workflow.md`)

**Problema:** bateria drenada cai no chão (não recarrega) e some (`Forbidden: Carried`).

**Implementado:** `BatteryRechargeFix` (força bReplaceBatteries), `BatteryCare` (hold+FailTask,
auto-unlock sticky `IsCarried`), `OstBattFix` (DropCO clear flags).

- [x] Diagnóstico/root cause (workflow.md)
- [x] Hold / re-route / FailTask recovery
- [x] Auto-unlock IsCarried
- [ ] **Unificar os 3 mods em 1** (BatteryCare) para evitar conflito de postfix `DropCO`/`Do`.
- [ ] Validar em jogo com `Debug.Log` a rota real de recharge.

### Frente D — Documentação técnica (parcial)

- [x] `ostranauts-ai-architecture.md` (workers, jobs, duties, interactions, pledges, pathfinding)
- [x] `ostranauts-api-reference.md`, `ostranauts-modding-quickref.md`
- [x] `ostranauts-battery-workflow.md`
- [x] `ostranauts-logistics-mod-plan.md`
- [x] **Consolidar docs de otimização** — `audit.md` (tabela A1–A9 + status 2026-08-16),
  `learnings.md` (anti-padrões + lição de bateria), e este roadmap (frentes A/C/D alinhadas).
- [x] `ostranauts-optimization-learnings.md` — atualizado (seções 5/7/8 com estado de 2026-08-16).

---

## 3. Backlog / ideias futuras

1. **Modularização do `Ostranauts.Opt`** — consolidar todos os micro-patchs de performance em um
   único plugin com configs por patch (mais fácil de manter/desligar).
2. **Perf de fluxos do `NavStation`/auto-dock** — explorar (interrompido quando o foco virou autotask).
3. **UI overlay de inventory organize goals** — mostrar onde cada item deve ir (helper visual).
4. **Configuração** — toggle por-atividade no menu (raster, multi-haul, empacotar).

---

## 4. Regras de trabalho (para o assistente)

- **Antes de implementar**: pesquisar mods existentes, wiki.gg/Modding, padrões e anti-padrões.
- **Após implementar**: revisar tudo (perfect review).
- **Build**: um única `.cs` por plugin (CS0111), HintPath resolvidos, `nix-shell -p dotnet-sdk_8`.
- **Debug live**: `UnityEngine.Debug.Log` → `Player.log`.
- **Patch Harmony**: verificar se o alvo existe; `PatchAll` reporta sucesso mesmo se método não for
  achado (vai só p/ `LogOutput.log`). Usar `Debug.Log` p/ confirmar que o patch disparou.
- **Não** instrumentar hot-paths por frame; **não** mexer em `strID` runtime.
- **Hooks em métodos heavy** → refletir para `Player.log` para prova real.

---

## 6. Próximos passos sugeridos (ordem)

1. **Unificar mods de bateria** (Frente C) — remove conflito potencial; baixo risco.
2. **Implementar Fix 4 (`EndTurn` AddRange → direto)** (Frente A) — médio ganho, baixo risco.
3. **Implementar o MVP do `PledgeOrganize` (data-pledge + registro + ponte L1→L2)** (Frente B).
4. **Refinar plano de empacotamento 2D com teste isolado** antes de integrar.
5. **Consolidar docs de otimização** pós-implantação.