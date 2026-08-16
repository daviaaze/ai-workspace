# Ostranauts — Plano de Validação em Jogo (Proton/Wayland)

> **Objetivo:** confirmar que os mods novos carregam e funcionam sem quebrar o jogo.
> Após cada modificação, seguir este roteiro. Tudo que importa aparece no
> **`Player.log`** (flush vivo), **não** no `LogOutput.log` (bufferizado).

---

## 1. Como relançar (NixOS + Wayland + Proton)

Steam launch options (já configuradas):
```
DRI_PRIME=1 WINEDLLOVERRIDES="winhttp.dll=n,b" %command%
```

Relaunch a partir da sessão Wayland ativa (não TTY):
```bash
# 1. Confirmar vars do display (sessão gráfica do usuário)
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export WAYLAND_DISPLAY=wayland-1
export DISPLAY=:0
export LIBVA_DRIVER_NAME=radeonsi
export DRI_PRIME=1

# 2. Abrir Steam (se não estiver rodando) e lançar o jogo
uwsm app -- steam steam://rungameid/1022980
```

**Checklist pré-launch:**
- [ ] BepInEx carregou → `Player.log` contém `BepInEx` e lista de plugins
- [ ] `WINEDLLOVERRIDES=winhttp.dll=n,b` ativo → LogOutput.log **não** fica 0 bytes

---

## 2. Onde ler os logs

| Log | Path | Flush |
|---|---|---|
| **Player.log** (vivo) | `~/.local/share/Steam/steamapps/compatdata/1022980/pfx/drive_c/users/steamuser/AppData/LocalLow/Blue Bottle Games/Ostranauts/Player.log` | ✅ durante o jogo |
| LogOutput.log (bufferizado) | `~/.local/share/Steam/steamapps/common/Ostranauts/BepInEx/LogOutput.log` | ❌ só no exit |

Sempre checar **Player.log** pro diagnóstico ao vivo.

```bash
# tail vivo
tail -f ~/.local/share/Steam/steamapps/compatdata/1022980/pfx/drive_c/users/steamuser/AppData/LocalLow/Blue Bottle Games/Ostranauts/Player.log
```

---

## 3. O que validar (por mod)

### 3.1 PledgeOrganize v0.3.0 (empacotador 2D)

**Sinal de carregamento (Player.log):**
```
[PledgeOrganize] loaded v0.3.0
[PledgeOrganize] registered type 'organize' -> PledgeOrganize.PledgeOrganize
[PledgeOrganize] granted to <nome da crew>
```

**Sinal de funcionamento (após carregar save e deixar crew em idle):**
```
[PledgeOrganize] <crew>: move <item> -> <container>
[PledgeOrganize] repack: <item> -> <container> (sim <N> free)
```

**O que observar in-game:**
- Crew em idle pega item do chão (L1) e leva pra um container/bin (L2), não pro stockpile.
- Quando container está cheio, log mostra "repack" — indica que o empacotador identificou onde re-arrumar.
- **Regra:** pledge só age quando crew está idle e não em modo manual (`IsAIManual`).

**Data-mod presente:**
```
Ostranauts_Data/Mods/PledgeOrganize/
├── data/pledges/pledges.json   (strType:"organize", nPriority:1)
└── mod_info.json               (strGameVersion 1.0.0.9)
```

### 3.2 BatteryCareUnified

**Sinal (Player.log):**
```
[BattCare] loaded
```

**O que observar:**
- Bateria drenada NÃO cai no chão (hold/re-route): crew segura ou leva pro charger.
- Item no chão com `IsCarried` stuck é limpo (auto-unlock) — bateria largada fica pickable.
- Sem erros `Forbidden: Carried` recorrentes em baterias no chão.

### 3.3 OstranautsOpt (modularizado)

**Sinal (LogOutput.log — aparece no exit; ou via Player.log indireta):**
```
[CFG] groups: Perf=True Alloc=True Load=True Save=True Log=True QoL=True Exp=False
=== PerfOpt v5.2.1 (44/45 patches) ===
```
> `Exp=False` → GetMove2_Cache (full-replacement arriscado) fica OFF por padrão → 44/45.

**Toggle de grupo:** editar `BepInEx/config/com.ostranauts.opt.cfg`.

**O que observar:**
- Overlay F7 mostra FPS/spike/GC/mem (se Overlay=True).
- Sem regressão de lag (patches não instrumentam hot-path por frame).
- [DebugLog=True] reduz spam no Player.log.

### 3.4 EndTurnOpt, GetWorkThrottle, WorkClaimThrottle, GetCOsOpt, SeekSocialCache

**Sinal:** aparecem na lista de plugins do LogOutput.log (`Loading [EndTurnOpt 1.0.0]`, etc).

**O que observar:**
- `GetWorkThrottle`: lag menor em work-shifts (cooldown no ProcessAutoTasks).
- Sem NullReferenceException em nenhum (log limpo).

### 3.5 Data mods (verificar ainda vanilla)

```
Ostranauts_Data/Mods/
├── AutoAirlock_Data/
├── EVALockers_Data/
├── ShipsWater_Data/
├── SolarPanels_Data/
├── SmartPick/
└── PledgeOrganize/
```

---

## 4. Smoke-test rápido (5 min)

1. Launch → main menu carrega (sem crash, sem spam de NullReferenceException).
2. Load save existente → carrega sem "Unable to load Loot" (falso-positivo conhecido: ACTDispenseLiquid/Mech/Default não são erro).
3. Advance sim 1 minuto em 1x → observar crew fazendo tasks normais.
4. Idle um crew perto de item no chão + container → log do PledgeOrganize deve aparecer.
5. Tail Player.log → sem erros vermelhos (`[ERROR]`, `NullReferenceException`).

---

## 5. Diagnóstico de falha

| Sintoma | Causa provável | Ação |
|---|---|---|
| LogOutput.log 0 bytes | BepInEx não carregou (winhttp doorstop não mapeou) | Relaunch Steam cold; checar `WINEDLLOVERRIDES` |
| `[PledgeOrganize]` não aparece | pledge não registrado ou data-mod faltando | Checar `Ostranauts_Data/Mods/PledgeOrganize/` + Player.log |
| PledgeOrganize não age | crew em IsAIManual ou sem idle | Selecionar crew, não colocar em manual mode |
| Lag spikes mods novos | Patch em hot-path por frame | Desabilitar grupo no config do OstranautsOpt |
| `Forbidden: Carried` em bateria | BatteryCareUnified não carregou | Checar LogOutput.log por erro de load |

---

## 6. Notas

- Os mods foram **compilados mas NÃO testados em runtime** até esta validação.
- Dependência conhecida: BepInEx doorstop é intermitente sob Proton — se não carregar, relaunch Steam cold.
- `Player.log` é a fonte da verdade pro diagnóstico ao vivo.
