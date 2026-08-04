# O que falta no Stremio? — Pesquisa da Comunidade

Pesquisei o que a comunidade do Stremio mais pede (GitHub issues, stremio-features, stremio-core, stremio-bugs, stremio-web, stremio-shell) e organizei por relevância.

---

## 🔥 Top 10 Mais Pedidos (por reações)

| # | Feature | ⭐ | O que é |
|---|---|---|---|
| 1 | **Skip Intro / SponsorBlock** | 57+16 | Pular intro, recap, créditos automaticamente (#770, #1608) |
| 2 | **Descrições maiores na Android TV** | 68 | Texto cortado, não dá pra ler sinopse completa (#1556) |
| 3 | **Botão de atualizar app nas settings (Android TV)** | 64 | Precisa ir na Play Store manualmente (#1691) |
| 4 | **Night mode / stereo downmix** | 61 | Diálogo baixo vs explosões altas, precisa de downmix (#313) |
| 5 | **Calendário na Android TV e Web** | 44 | Ver lançamentos futuros (tipo Netflix "Coming Soon") (#430) |
| 6 | **Media keys pause/play (em outra janela)** | 38 | Teclado multimídia não funciona fora da janela (#341) |
| 7 | **Preload / buffer / download offline** | 36 | Baixar conteúdo pra assistir sem internet (#138) |
| 8 | **Remover Cinemeta oficial** | 34 | Catálogo padrão poluído, querem só addons escolhidos (#567) |
| 9 | **Override do streaming server URL no mobile** | 28 | Android não deixa configurar servidor próprio (#415) - **relevante pra nós** |
| 10 | **Addons rastrearem progresso de playback** | 26 | Addon poder saber quando algo foi assistido (#824) |

---

## 🎬 Player & Playback

| Pedido | ⭐ | Detalhe |
|---|---|---|
| Zoom to fill (ultrawide) | 24 | Cortar barras pretas em vídeos ultrawide (#633) |
| Picture-in-Picture (mobile) | 24 | Assistir em janela flutuante (#471, #721) |
| Controle de delay de áudio | 23 | Sincronia áudio-vídeo (#215) |
| Suporte a capítulos | 18 | Navegar por capítulos do vídeo (#356) |
| Controle de velocidade | 12+14 | Acelerar/desacelerar reprodução (#154, #255) |
| Multi-legendas simultâneas | 22 | 2 legendas ao mesmo tempo (#186) |
| Configurar fonte/cor/posição das legendas | 14 | Personalização visual (#65, #228) |
| **Preferir áudio original + legenda traduzida** | 10 | LG - Preferred Audio Language (#1096) |
| Suporte a Dolby Atmos/Vision | 3 | Codecs avançados (#676, #1046) |

---

## 🧩 Addons & Catálogo

| Pedido | ⭐ | Detalhe |
|---|---|---|
| **Self-hosting do backend** | 17 | Poder hospedar própria conta/sincronia (#506) - **fechado, rejeitado** |
| **Proxy own connections** | 47 | Proxy todo tráfego via Stremio Service (#59) |
| SOCKS5 support | 23 | Proxy SOCKS5 para torrents (#353) |
| Bind traffic to specific interface | 12 | Escolher interface de rede (#986) |
| Esconder addons adultos | 13 | Filtro parental (#1331) |
| Reordenar addons | 14 | Arrastar pra mudar ordem (#639) |
| Addon modificar UI | 13 | Addon poder alterar a interface (#1002) |
| Separar Cinemeta em 2 (meta + catálogos) | 14 | Poder usar metadados sem catálogo deles (#608) |
| Perfis por conta | 8 | Múltiplos perfis na mesma conta (#841) |

---

## 📚 Biblioteca & Organização

| Pedido | ⭐ | Detalhe |
|---|---|---|
| **Esconder assistidos** | 25 | Filtro "hide watched" (#96) |
| **Pastas na biblioteca** | 15 | Agrupar filmes/séries em pastas (#83) |
| **Download offline** | 16 | Baixar pra assistir sem internet (#1290) |
| **Auto-download next episode** | 21 | Pré-baixar próximo episódio (#240) |
| Quick account switching | 15 | Trocar de conta rápido (#929) |
| "More like this" | 20 | Recomendações similares (#361) |
| Ordenar library por ano | 14 | Data de lançamento (#449) |
| Favoritos / Watch Later | 9 | Lista separada (#972) |
| Archive movies/series | 11 | Arquivar sem remover da biblioteca (#217) |

---

## 📱 Android TV / Mobile

| Pedido | ⭐ | Detalhe |
|---|---|---|
| Descrições maiores (ATV) | 68 | #1 mais votado — texto cortado |
| Botão de atualizar (ATV) | 64 | Sem update checker |
| Calendário (ATV + Web) | 44 | Lançamentos futuros |
| Override server URL (mobile) | 28 | **Não consegue usar servidor próprio** |
| PiP (mobile) | 24 | Picture-in-picture |
| "See All" button (ATV) | 15 | Ver todos os filmes de uma categoria |
| Catálogos na home (ATV) | 10 | Escolher quais catálogos aparecem (#325) |
| iOS/tvOS app | 14 | Stremio Lite chegou mas ainda limitado |

---

## 🌐 Integrações

| Pedido | ⭐ | Detalhe |
|---|---|---|
| **Trakt Scrobbling** | 6+12 | Sincronizar watch history com Trakt (#864, #1476) |
| **SIMKL integration** | 15 | Integração com SIMKL (#201) |
| Xbox app | 14 | Stremio no Xbox (#1737) |
| Tizen (Samsung TV) | 11+13 | App nativo para TVs Samsung (#86, #434, #462) |
| Chromecast | 16 | Casting sumiu em algumas versões (#1329) |
| MPRIS support (Linux) | 10 | Controle multimídia no Linux (#1048) |

---

## 🐛 Bugs Críticos (mais reportados)

| Bug | ⭐ | Detalhe |
|---|---|---|
| YouTube search HTTP 500 | 17 | Pesquisa do YouTube quebrada |
| Chromecast missing | 16 | Casting não funciona mais |
| LG Preferred Audio Language | 10 | Não respeita idioma preferido |
| Buffering no Vidaa (Hisense) | 11 | Travamentos em TVs Hisense |
| Stremio v6 freeze no Linux | 7 | Congela durante playback |
| Arquivos não carregam (ATV) | 7 | "Files not loading" |
| Legendas embutidas não aparecem | 6 | Embedded subs ignorados |
| Memory leak (LG) | 6 | Vazamento de memória |
| RD/TB links não funcionam (Tizen) | 6 | Real Debrid/TorBox quebrado em TVs Samsung |
| Legendas somem aleatoriamente | 8 | Subtitles randomly disappear |

---

## 💡 Oportunidades para o Setup Homelab

Baseado no que a comunidade mais pede, aqui estão as oportunidades que **o nosso setup self-hosted pode resolver**:

### 1. Skip Intro ✅ (JÁ FEITO)
- 57+16⭐ — segundo feature mais pedido
- **Nós já temos**: ffmpeg silencedetect + HLS seek + stream alternativo
- **Melhoria**: usar SponsorBlock API pública em vez de ffmpeg (mais rápido, curado pela comunidade)

### 2. Proxy / Binding de Rede
- 47⭐ + 23⭐ + 12⭐ = **82⭐ combinados**
- **Nós podemos**: o torrentio-prober roda no mesmo host, mas dava pra adicionar suporte a proxy socks5 nas torrents do stremio server

### 3. Preload / Buffer Inteligente
- 36⭐ + 21⭐ = 57⭐
- **Nós já temos**: prewarm do vencedor na race, mas dava pra expandir pra pré-baixar episódios seguintes
- **Pin automático** quando salva série na biblioteca

### 4. Override Server URL no Mobile
- 28⭐ — comunidade inteira querendo
- **Nós temos**: servidor próprio rodando, mas o app mobile não deixa configurar URL customizada fácil
- **Solução**: criar um addon de streaming que redireciona pro nosso servidor (addon de url, não infoHash)

### 5. Trakt Scrobbling
- 6+12⭐
- **Oportunidade**: addon que faz scrobble manual via API do Trakt, já que o oficial do Stremio é instável

### 6. SponsorBlock
- 16⭐ específico, mas relacionado ao skip intro
- **Nós podemos**: addon que consulta API do SponsorBlock e retorna timestamps pra pular (intros, recaps, "like and subscribe", etc.)

### 7. Self-Hosting (rejeitado pelo Stremio, mas desejado)
- 17⭐ — fechado/rejeitado, mas a demanda existe
- **Nós já temos**: servidor stremio próprio, torrentio próprio, tracker-bot próprio
- **Falta**: gerenciamento de conta/sincronia self-hosted (mais complexo)

### 8. Catálogo Customizado
- 34⭐ querem remover Cinemeta
- **Oportunidade**: fazer um addon de catálogo que usa nossos próprios indexers (Prowlarr) e mostra só o que tem seeders

---

## 📊 Prioridade Recomendada

| Prioridade | O que fazer | Impacto |
|---|---|---|
| 1 | **SponsorBlock integration** | Skip intro mais preciso, curado pela comunidade, sem ffmpeg pesado |
| 2 | **Pre-warm + Pin automático** | Baixar automático ao salvar série — playback instantâneo |
| 3 | **Prowlarr Source** | Coverage real, seeders, menos streams mortos |
| 4 | **Trakt Scrobbling Addon** | Sincronizar watch history — comunidade quer muito |
| 5 | **Proxy/Binding** | Privacidade + contornar ISP blocker |
| 6 | **Catálogo customizado (Prowlarr)** | "Netflix" próprio com só o que tem seeders |

Quer que eu mergulhe em algum desses específicos? O SponsorBlock é o de maior impacto agora — API pública, gratuito, e substitui nosso ffmpeg pesado por timestamps curados.