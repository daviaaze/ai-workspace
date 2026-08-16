# Ostranauts — Plano Mestre (Roadmap Completo)

> **Visão geral de todas as frentes**, consolidadas. Cada frente referencia sua doc detalhada.
> Status atualizado em **2026-08-16** (pós-parallel-fronts + packer).
> Jogo 1.0.0.9, BepInEx 5.4.23.5, Proton/Wayland, netstandard2.1 C# 9.0.
> Docs-fonte: `ostranauts-*.md` no workspace + `/tmp/game_api_full/` (612 .cs decompilados).

---

## 0. Estado do ambiente (happy path confirmado)

| Item | Valor |
|---|---|
| Launch options Steam | `DRI_PRIME=1 WINEDLLOVERRIDES="winhttp.dll=n,b" %command%` |
| BepInEx core | `0Harmony.dll`, `BepInEx.dll` presentes em `BepInEx/core/` |
| Live log | `Player.log` (via `Debug.Log`) — **BepInEx `LogOutput.log` é bufferizado** |
| dotnet build | `nix-shell -p dotnet-sdk_8 --run`, csproj HintPaths **resolvidos** `/home/daviaaze/.local/share/Steam/...` |

> **Regra de ouro de live-debug:** logar via `UnityEngine.Debug.Log` (vai p/ `Player.log`,
> flush confiável), **nunca** confiar em `LogOutput.log` (bufferizado, só dumps no start/exit).

---

## 1. Mods ativos hoje (BepInEx/plugins/)

| DLL | Função | Frente |
|---|---|---|
| `BatteryCareUnified` | bateria: hold/re-route no AddCO + clear flags no DropCO + diagnóstico FailTask | C (unificado) |
| `PledgeOrganize` v0.3.0 | idle-pledge L1→L2 com **empacotamento 2D best-fit-decreasing** (Packer2D) | B |
| `OstranautsOpt` v5.2.1 | 45 patches de perf (themaoci) — GC, load, ToList, tickers, save | A |
| `GetWorkThrottle` | cooldown 2.0s no ProcessAutoTasks | A |
| `WorkClaimThrottle` | throttle idle-aware no ClaimNextTask | A |
| `ItemOverlayThrottle` | throttle em Item.VisualizeOverlays | A |
| `GetCOsOpt` | visitor reutilizável p/ Ship.GetCOs | A |
| `SeekSocialCache` | interaction reutilizável p/ SeekSocialDeny | A |
| `EndTurnOpt` | EndTurn aCondsTemp AddRange → iteração direta (Transpiler) | A |
| `OstranautsSimDiag` | cronômetro SIM-DIAG | A |
| framework | ConfigurationManager + Ostranauts.Autoloader | — |

> ✅ Bateria unificada (antes 3 mods sobrepostos: BatteryCare/BatteryRechargeFix/OstBattFix → BatteryCareUnified).

---

## 2. Roadmap por frente

### Frente A — Otimização de performance (doc: `ostranauts-optimization-audit.md`)

**Implementados (11 fixos):**
- **A1** NoCopy (UpdateICOs AddRange) · **A2** PreSizeCondsTemp · **A3** NoTickerLog (Transpiler)
- **A4** FirstOrDefault skip · **A5** ProcessAutoTasks cooldown (GetWorkThrottle)
- **A6** VisualizeOverlays throttle (ItemOverlayThrottle) · **A7** ClaimNextTask throttle (WorkClaimThrottle)
- **A8** GetCOs visitor (GetCOsOpt) · **A9** SeekSocialDeny cache (SeekSocialCache)
- **A10** EndTurn AddRange → direta (EndTurnOpt) · **A11** OstranautsOpt v5.2.1 (45 patches themaoci)

**Restante (por prioridade):**
- ⏸️ **Fix 3 — `GetMove2` Dictionary reusável** — **SKIPPED**: requer substituição total (1000+ linhas).
- [x] **Modularizar OstranautsOpt** — 45 patches agrupados em 9 toggles (Performance, AllocOpt, Loading, Saving, DebugLog, Gameplay, Experimental, Overlay, MemManagement) via ConfigFile. GetMove2 (full-replacement arriscado) default OFF.
- [ ] **Validação de dose/impacto por perf** — relatórios SIM-DIAG no jogador.

> ⚠️ Lição crítica: **não instrumentar hot-paths por frame** (causou lag). Aprovação de cada
> Transpiler com teste de regressão.

### Frente B — Mod de logística/organização em idle (doc: `ostranauts-logistics-mod-plan.md`)

**Problema:** haul despeja tudo no chão (L1); bins/containers (L2) ficam vazios.
**Solução:** idle-pledge `PledgeOrganize` (ponte L1→L2) guiado por **Packer2D** (best-fit-decreasing).

- [x] Data-mod: `pledges.json` (`strType:"organize"`, `nPriority:1`) + `mod_info.json`.
- [x] Registro do pledge no `PledgeFactory` (reflexão em dictTypes, sem Harmony).
- [x] `PledgeOrganize.Do()` MVP — multi-item + slots + dolly.
- [x] **Packer2D integrado** — escolha de container via simulação 2D real (best-fit-decreasing com
  rotação); quando não cabe em nenhum, identifica candidato a repacking. Validado isoladamente:
  5/5 items em grid 6x6, fuzz 200 runs @ 83.2% placement, 0 exceptions.
- [ ] Roteamento L1→L2 com re-packing real (remover + reinserrer soltos em ordem decrescente).
- [ ] Aninhamento bolsa-em-baú, respeito a bins oversized (dolly p/ IsCumbersome/IsOversized).
- [ ] Teste em jogo (idle).

### Frente C — Mods de bateria (docs: `ostranauts-battery-workflow.md`)

**Problema:** bateria drenada cai no chão (não recarrega) e some (`Forbidden: Carried`).

- [x] Diagnóstico/root cause (workflow.md) — ship re-AddCO não limpa IsCarried.
- [x] **Unificado** em `BatteryCareUnified`: AddCO postfix (hold/re-route p/ charger) + DropCO
  postfix (clear IsCarried/IsSlotted/IsInContainer) + FailTask diagnóstico.
- [x] Hold / re-route / FailTask recovery.
- [x] Auto-unlock IsCarried.
- [ ] Validação final em jogo (Player.log).

### Frente D — Documentação técnica

- [x] `ostranauts-ai-architecture.md` (workers, jobs, duties, interactions, pledges, pathfinding).
- [x] `ostranauts-api-reference.md`, `ostranauts-modding-quickref.md`.
- [x] `ostranauts-battery-workflow.md`.
- [x] `ostranauts-logistics-mod-plan.md`.
- [x] `ostranauts-optimization-audit.md` + `ostranauts-optimization-learnings.md`.
- [x] Consolidado status 2026-08-16 (este roadmap).

---

## 3. Backlog / ideias futuras

1. **Modularização do `OstranautsOpt`** — 45 patches com toggles por config (mais fácil manter/desligar).
2. **Re-packing real no PledgeOrganize** — remover + reinserrer soltos em ordem decrescente p/ desfragmentar.
3. **Perf de fluxos do `NavStation`/auto-dock** — explorar.
4. **UI overlay de inventory organize goals** — helper visual.
5. **Configuração** — toggle por-atividade no menu.

---

## 4. Regras de trabalho

- **Antes de implementar**: pesquisar mods existentes, wiki.gg/Modding, padrões e anti-padrões.
- **Após implementar**: revisar tudo (perfect review).
- **Build**: uma única `.cs` por plugin (CS0111), HintPath resolvidos, `nix-shell -p dotnet-sdk_8`.
- **Debug live**: `UnityEngine.Debug.Log` → `Player.log`.
- **Patch Harmony**: verificar se o alvo existe; `PatchAll` reporta sucesso mesmo se método não for achado.
- **Não** instrumentar hot-paths por frame; **não** mexer em `strID` runtime.

---

## 5. Próximos passos sugeridos (ordem)

1. **Modularizar OstranautsOpt** — toggles por patch-group (Frente A / backlog #1).
2. **Validação em jogo** dos mods novos (PledgeOrganize v0.3.0, BatteryCareUnified, EndTurnOpt).
3. **Re-packing real** no PledgeOrganize.
4. Consolidar docs pós-validação.