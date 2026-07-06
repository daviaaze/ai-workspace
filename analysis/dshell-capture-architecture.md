# dshell — Arquitetura de Captura de Tela (screenshot / recording / screenshare)

> Análise + proposta de arquitetura "nível Ubuntu" para o stack de captura do `dshell` (shell GJS/Astal sobre Hyprland).
> Status: proposta (não implementado). Data: 2026-07-04.

## 1. Estado atual

### Dependências (flake.nix `wrapperPackages`)
| Binário | Papel | Instalado? | Default? |
|---|---|---|---|
| `grim` | Screenshot (still) | ✅ | — |
| `wl-clipboard` (`wl-copy`) | Clipboard (imagem) | ✅ | — |
| `wf-recorder` | Recording (fallback, ffmpeg/CPU) | ✅ | ❌ (é o fallback) |
| `wl-screenrec` | Recording (GPU/vaapi/dma-buf) | ❌ **NÃO** | ✅ (gschema `recorder-backend=0`) |
| `wayfreeze` | Congelar tela antes do screenshot de área | ❌ **NÃO** | — |
| `hyprland` (`hyprctl`) | Virtual monitors | ✅ | — |
| `pipewire` | (instalado mas **não usado** para captura — só `appMixer` lê streams) | ✅ | — |

### Fluxos
- **Screenshot**: `grim -o <monitor>` / `grim -g "<x,y WxH>"` → PNG → `wl-copy -t image/png`. Área via region-selector custom (coords locais → somadas offset global no capture). Freeze via `wayfreeze` (silenciosamente pulado — binário ausente).
- **Recording**: subprocess `wl-screenrec` (default) ou `wf-recorder`; `-o`/`-g`/`-f`; codec por extensão (mp4 default, webm toggle). SIGINT pra parar. Boundary desenhado por `recording-boundary` (espera coords globais).
- **Screenshare (portal)**: `share-picker-main.ts` é o `custom_picker_binary` do XDPH — imprime `[SELECTION]r/screen:NAME` no stdout, XDPH cria o stream PipeWire. O shell só fornece a UI de seleção.
- **Share tracking**: `registerShare`/`unregisterShare` — **morto** (zero callers; XDPH não emite sinal de ciclo de vida de sessão).

## 2. Problemas (resumo dos bugs confirmados)
1. 🔴 **wl-screenrec (default) não está instalado** → gravação falha "not found" em install limpo.
2. 🔴 **wayfreeze não instalado** → freeze de screenshot de área sempre pulado.
3. 🔴 Falso "Recording failed" ao parar em <1s (sem flag `#stopRequested`).
4. 🟠 Exit handler menciona "wf-recorder" hardcoded (default é wl-screenrec).
5. 🟠 `stopRecording`: `signal(2)` sem try/catch nem escalada SIGTERM (inconsistente c/ `dispose`/`stopFreeze`).
6. 🟠 Boundary obsoleto quando um share desregistra com outro ativo (só esconde quando lista esvazia).
7. 🟠 `createVirtualMonitor`: `hyprctl` síncrono (trava UI) + race de registro do output headless.
8. 🟠 3 seletores sobrepostos (region-selector, screenshot-overlay, share-picker) sem unificação.
9. 🟠 Sem auto-detecção de backend (vaapi/GPU) — usuário precisa saber configurar gschema.
10. 🟠 Share tracking morto — shell não sabe quais shares de portal estão ativos.

## 3. Arquitetura-alvo (tiered)

### Tier 0 — Confiabilidade do stack CLI atual (esforço baixo, impacto alto)
**Objetivo**: captura funciona out-of-the-box e sem bugs de lifecycle.
- Adicionar `wl-screenrec` + `wayfreeze` ao `wrapperPackages`.
- `recorder-backend` default → `auto` (novo); `startRecording` detecta: tenta `wl-screenrec`; se falhar em <2s (heuristic já corrigida), re-tenta com `wf-recorder` automaticamente. Override manual permanece.
- Fix bugs #3–#7: flag `#stopRequested`; capturar `backendName` no closure do exit; try/catch + SIGTERM em `stopRecording`; recompute boundary dos shares restantes em `unregisterShare`; `hyprctl` assíncrono + retry de registro.
- **Resultado**: stack CLI atual, porém confiável. É o que a maioria dos usuários Hyprland/Sway usa e é competitivo em performance (wl-screenrec ~2.5% CPU).

### Tier 1 — Unificação de UX + wiring de shares (esforço médio)
- **Um seletor**: estender o share-picker (ou region-selector) para cobrir screenshot-area / record-area / record-monitor / record-window / share — mesma UI, mesmos atalhos. O region-selector de área (já bom) é reusado.
- Desacoplar `screenshot-overlay` do recording (overlay é UI de freeze de screenshot; recording não deveria abri-lo).
- **Wire do share tracking**: como XDPH não emite sinal, monitorar o grafo PipeWire via DBus (`org.freedesktop.DBus`/`pw-cli` ou `org.pipewire.*`) para detectar nós ScreenCast-portal ativos → preenche `activeShares` + boundary automaticamente. Alternativa honesta: remover o código morto se não valer o esforço.
- Virtual monitor: `hyprctl` 100% async.

### Tier 2 — Captura nativa via Portal+PipeWire+GStreamer (esforço alto, "nível Ubuntu")
**Objetivo**: o shell vira cliente do `org.freedesktop.portal.ScreenCast` (como o GNOME/mutter faz internamente), unificando recording e share.
- **Recording**: `CreateSession → SelectSources(monitor/window/region, cursor, persist) → Start → node_id PipeWire → pipeline GStreamer`:
  ```
  pipewiresrc path=<node_id> ! videoconvert !
  <encoder: vaapih264enc | x264enc | vp9enc | nvh264enc> !
  mp4mux ! filesink location=<file>
  ```
  Áudio em stream separada: `pipewiresrc ... ! opusenc/aacenc` → mux.
- **Vantagens**: UX unificada com o path de share do XDPH; codec flexível (encodebin); accel por hardware (`vaapi`/`nvenc`); multi-monitor correto por design (portal dá 1 stream por fonte); token restore (persistir seleção); **streaming-capable** (pode expor como câmera virtual ou source pra OBS); sem fragilidade de flags CLI por ferramenta.
- **Custos**: deps `gstreamer` + `gst-plugins-base` (pipewiresrc) + `gst-libav` (codecs) + `gst-plugins-bad` (vaapi/nvenc); tipos `@girs/gst-1.0`; pipeline GStreamer em GJS (mais código); negociação DBus do portal.
- **Screenshots**: manter `grim` (rápido/simples) — ou opcionalmente portal `Screenshot`. Grim é suficiente.

## 4. Tradeoff central
| Critério | CLI (grim+wl-screenrec+wf-recorder) | Portal+PipeWire+GStreamer |
|---|---|---|
| Performance | 🟢 wl-screenrec ~2.5% CPU (vaapi) | 🟡 equivalente c/ vaapi encoder |
| Simplicidade | 🟢 subprocess | 🔴 DBus + pipeline Gst |
| UX unificada c/ share | 🔴 paralela | 🟢 mesma path |
| Streaming p/ OBS/cam | 🔴 não | 🟢 sim |
| Flexibilidade codec | 🟡 flags por tool | 🟢 encodebin |
| Deps | 🟢 poucas | 🟡 gstreamer stack |
| Multi-monitor | 🟡 manual (já corrigido) | 🟢 portal por-fonte |

## 5. Recomendação
1. **Fazer Tier 0 agora** — fix de deps + bugs de lifecycle. Esforço baixo, resolve "gravação não funciona por default".
2. **Tier 1 em seguida** — unificar seletores + wire de shares via PipeWire DBus.
3. **Avaliar Tier 2 como upgrade estratégico** — só se o objetivo for ser um shell "GNOME-grade" com streaming/câmera virtual. Se o objetivo é "bom e rápido como um Sway bem configurado", Tier 0+1 já entrega.

## 6. Referências das docs pesquisadas
- wl-screenrec (russelltg/wl-screenrec): GPU/dma-buf/vaapi, ~2.5% CPU; requer vaapi (Intel/Radeon, **não NVIDIA**); codecs avc/hevc/vp8/vp9/av1; suporta `ext-image-copy-capture-v1`.
- wf-recorder (ammen99/wf-recorder): ffmpeg, libx264 default, `-o`/`-g`/`-c`/`-C`/`-a`, áudio pulse/pipewire.
- grim (emersion/grim): `grim -o` / `grim -g` / `grim - | wl-copy`.
- XDPH (hyprwm/xdg-desktop-portal-hyprland): implementa ScreenCast portal; `custom_picker_binary`, `max_fps`, `force_shm`, token restore; **sem sinal de ciclo de vida de sessão**; window-sharing é exclusivo Hyprland.
- Astal (aylur.github.io/astal): **sem módulo de capture/recording** — shell precisa de tools externas ou portal+Gst.
- GNOME/ubuntu: recording nativo via mutter ScreenCast + PipeWire + GStreamer (equivalente ao Tier 2).

## 7. Status da implementação (2026-07-04)

**Decisão:** Tier 0 + Tier 1 aprovados (Tier 2 descartado). Tier 1.2 (share-tracking) decidido como **remoção de dead code** (API 100% sem callers/consumers; picker XDPH é binário separado que não reporta ao shell).

### Tier 0 — Confiabilidade (implementado)
- **Deps (flake.nix):** `wl-screenrec` + `wayfreeze` adicionados a `wrapperPackages` (antes só `wf-recorder` → gravação quebrada por default; freeze sempre pulado).
- **Freeze wiring (bug recém-descoberto):** `startFreeze()`/`stopFreeze()` não tinham callers (dead code). Agora ligados ao fluxo de área via setter `regionSelectorOpen`: `startFreeze()` ao abrir o seletor (frame estável p/ desenhar); `stopFreeze()` no cancelamento (guardado por `#freezeCapturePending`); no confirm, screenshot libera freeze só após grim pegar o frame (`.then`/`.catch`), recording libera logo após `startRecording` (gravação quer conteúdo ao vivo). Cobre ambos os entry points (`openRegionSelectorForCapture` e o path direto do `screenshot-overlay`).
- **gschema:** `recorder-backend` default `0→2` (auto); enum `RecorderBackend.AUTO = 2`.
- **Backend auto-detect:** `#resolveBackend(pref)` resolve AUTO → wl-screenrec se instalado, senão wf-recorder. Fallback de runtime: se wl-screenrec morrer <1s (sem vaapi) e pref=AUTO, re-tenta transparentemente com wf-recorder uma vez.
- **Lifecycle:** campos `#stopRequested`/`#recordingIsRetry`/`#recordingBackendName`; exit handler distingue stop voluntário de crash (`#stopRequested || durationMs>=1000`); notificações usam o nome real do backend (não hardcoded "wf-recorder"); `stopRecording` try/catch + escalada SIGTERM (igual `stopFreeze`/`dispose`); helper `#resetRecordingProcess()`.
- **Boundary de shares (bug #5):** antes de remover, `#recomputeShareBoundary()` recomputava union dos monitor-shares — mas como T1.2 removeu shares, isso foi removido junto. `showBoundary`/`hideBoundary` permanecem p/ area-recording.
- **Virtual monitor (bug #6):** `createVirtualMonitor` agora `async` + `execAsync` + retry polling `monitors all` (~1s) — não bloqueia o main loop e resolve a race de registro.

### Tier 1 — UX (T1.1 já funcional; T1.2 = remoção)
- **T1.1 (unificar seletores):** já implementado — `screenshot-overlay` (selectedMode/selectedTarget) cobre monitor/window/area visualmente; `region-selector` cobre área p/ screenshot E recording; `openRegionSelectorForCapture('screenshot'|'recording')` é o ponto único. Nada a fazer.
- **T1.2 (share tracking):** removido como dead code honesto — `ActiveShare`, `#activeShares`, `registerShare`/`unregisterShare`, `shareStarted`/`shareStopped`, getter `activeShares`, `#recomputeShareBoundary`, `notify('active-shares')`. O binário `share-picker-main.ts` (XDPH) permanece intocado como processo separado. Se no futuro quiser rastrear shares, re-introduzir via DBus picker→shell (Opção 2) ou monitor PipeWire (Opção 3).

### Verificação estática
- esbuild (transpile): OK, exit 0.
- eslint: 0 erros novos (único erro pré-existente: `catch (e)` não-usado em `startFreeze`).
- tsc --noEmit: **425 erros = baseline** (0 novos; todos pré-existentes gnim/astal type gaps).

### Pendente (requer `nix build` do usuário)
- Nova chave gschema `recording-format` + default alterado de `recorder-backend` exigem regeneração do schema.
- Novas deps (wl-screenrec/wayfreeze) exigem rebuild do flake.
- Teste de runtime: gravar em monitor/área/janela, WebM toggle, auto-fallback wl-screenrec→wf-recorder, stop rápido sem falso "Recording failed".

## 8. Pós-implementação — varredura de dead code + VM button (2026-07-04)

Após o Tier 0+1, uma auditoria de wiring revelou mais dead code (mesmo padrão de shares/freeze):
- **`getOutputs()`/`getWindows()`** — 0 callers; `getWindows` tinha bug de tipo real (`c.monitor >= 0` onde `Client.monitor` é `Monitor`). Removidos.
- **6 `@signal()` sem consumers** (`recordingStarted`/`recordingStopped`/`overlayShown`/`overlayHidden`/`freezeActivated`/`freezeDeactivated`) — a UI usa `createBinding` nas propriedades. Removidos + import `signal` + emits internos.
- **Virtual-monitor feature** — `createVirtualMonitor`/`removeVirtualMonitors`/getter + 2 chaves gschema, tudo sem callers. Decisão: **wirear** (não remover). Add botão de QS (Adw.ButtonContent, label/icon dinâmicos via binding `virtualMonitorActive` boolean derivado), lê resolução/fps do gschema, `#notify` nas falhas. Getter booleano derivado evita o type-gap do `createBinding` em propriedade `Array` (gnim overload não tipa Array; camelCase `virtualMonitorActive` é type-clean ao contrário do kebab `virtual-monitor-active` que herdava o mesmo TS2769 de `recording-elapsed`/`selected-mode`).

### Estado final estático
- esbuild: clean. eslint: 0 issues. tsc: **424 erros = baseline** (0 novos; -1 vs 425 pois removi o bug TS2365 `Monitor>=number`).
- 3 commits em `fix/review-sprint1`: `fix(types)` cairo, `fix(region-selector)` coords, `fix(capture)` overhaul.
