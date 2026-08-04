# Plataformas + Cache Distribuído — Análise Técnica e Legal

**Data:** 2026-07-06
**Perguntas:** (1) Atingir celulares, TVs, web, apps próprios? (2) Baratear com cache distribuído entre usuários?

---

## 1. PLATAFORMAS — Stremio já cobre tudo (grátis)

### 1.1 Plataformas suportadas pelo Stremio (hoje, 2026)

| Plataforma | Status Stremio | Como instalar |
|---|---|---|
| **Android (celular)** | ✅ Nativo | Play Store |
| **Android TV / Google TV** | ✅ Nativo (5.0+) | Play Store na TV |
| **Samsung Tizen** | ✅ Nativo (modelos 2021+) | Smart Hub |
| **LG webOS** | ✅ Nativo (modelos 2020+) | LG Content Store |
| **Fire TV / Fire Stick** | ✅ Sideload (APK Android) | Downloader app |
| **iPhone / iPad (iOS)** | ✅ Nativo | App Store |
| **Apple TV (tvOS)** | ⚠️ Limitado | AirPlay do iPhone, ou sideload complexo |
| **Windows** | ✅ Nativo | .exe / Store |
| **macOS** | ✅ Nativo | .dmg |
| **Linux** | ✅ Nativo | .deb / Flatpak / Snap |
| **Roku** | ❌ Não suportado | Sem app |
| **Web (navegador)** | ✅ Nativo | web.stremio.com |

**Conclusão:** se o produto for "Stremio + TorBox + nosso addon", **você atinge celular, TV e web sem escrever uma linha de código de player**. Stremio resolve a distribuição de plataforma.

### 1.2 Onde Stremio NÃO chega (gaps)

| Gap | Solução |
|---|---|
| **Apple TV (tvOS)** nativo | AirPlay do iPhone (aceitável), ou app próprio |
| **Roku** | Sem solução via Stremio — mercado BR pequeno |
| **TVs antigas (<2020)** | Android TV box (Mi Box, TCL) — R$ 200-400 |
| **Consoles (PS/Xbox)** | Sem app — mercado marginal no BR pra isso |

### 1.3 App próprio — vale a pena?

**Prós de um app próprio:**
- Controle total da experiência (onboarding, branding)
- Não depende do Stremio (risco de bloqueio)
- Pode bundlear TorBox + biblioteca DP + addon num só lugar
- Push notifications, analytics

**Contras:**
- **Custo alto:** R$ 30-100k+ pra fazer app multiplataforma decente
- **Manutenção:** cada plataforma tem peculiaridades, updates constantes
- **Tizen/webOS são difíceis** (SDKs proprietários, processos de aprovação)
- **App Store / Play Store podem recusar** apps de pirataria (risco de ban)
- **TorBox já tem API oficial** (`@torbox/torbox-api` no npm) — tecnicamente viável
- **Referência:** existe app "STREAMED" (chandradev28/streamed.app) que integra TorBox em Flutter — prova que é possível

### 1.4 Stack de app próprio (se quiser)

| Plataforma | Tecnologia | Custo |
|---|---|---|
| Celular (Android+iOS) | Flutter ou React Native | Médio |
| Android TV | Flutter/React Native for TV | Médio |
| Samsung Tizen | Tizen Web API (JavaScript) | Alto (SDK fechado) |
| LG webOS | webOS TV SDK (JS) | Alto |
| Apple TV (tvOS) | Swift / React Native tvOS | Médio-alto |
| Web | React/Next.js | Baixo |
| Desktop | Electron (do web) | Baixo |

**Veredito app próprio:** NÃO na Fase 1. Use Stremio. Considere app próprio só na Fase 3+ (500+ usuários, validou produto-mercado) e só se Stremio se tornar um gargalo.

### 1.5 Estratégia de plataformas recomendada

```
Fase 1 (MVP):     Stremio em tudo (celular, Android TV, Tizen, webOS, web, iOS)
                  Biblioteca DP: web app responsivo (PWA)
Fase 2:           App Android próprio (só billing + onboarding + biblioteca DP)
                  Stremio continua sendo o player
Fase 3 (se validar): App player próprio multiplataforma (opcional, caro)
```

---

## 2. CACHE DISTRIBUÍDO — o gancho jurídico sério

### 2.1 A pergunta reformulada

> "Se os usuários fizessem cache de parte do conteúdo, dá pra baratear?"

A resposta depende de **qual conteúdo** e **como** o cache é distribuído. Existem 3 modelos, com legalidades opostas:

### 2.2 Os 3 modelos de cache

#### Modelo A — Cache pessoal no dispositivo do usuário (tipo Plex/Jellyfin)

**Como funciona:** usuário baixa uma vez, fica no disco dele, assiste offline depois.

**Legalidade:** 🟢 **Legal** — é cópia para uso pessoal. O usuário é responsável pelo que baixa.

**Economia:** 🔴 **Zero economia no TorBox.** Você ainda paga R$ 15/usuário/mês pela conta TorBox. O cache local só economiza banda do TorBox (que já é marginal). Não barateia o custo principal.

#### Modelo B — Cache P2P entre usuários (tipo Popcorn Time / WebTorrent)

**Como funciona:** usuário A assiste, pedaços do arquivo ficam no app; usuário B pega do usuário A em vez do servidor. Mesh network.

**Legalidade:** 🔴🔴 **ILEGAL — criminal.** Isso é distribuição P2P de obra protegida.

**Economia:** 🟢 **Grande economia** — não precisa TorBox pra conteúdo popular, usuários se servem entre si.

**Por que é ilegal:**
- **Lei 9.610/98 Art. 5 VI:** "reprodução" = "armazenamento permanente ou temporário por meios eletrônicos" — redistribuir P2P é distribuição
- **Art. 184 CP:** "oferecer ao público obra protegida" — crime, pena 2-4 anos
- **Popcorn Time foi processado** nos EUA e Brasil — operadores e usuários processados
- **TorrentFreak:** juiz inicialmente permitiu usuário continuar torrenting, mas operadores foram condenados
- No Brasil, estúdios processaram Popcorn Time e usuários (Tecnoblog reportou)
- **Usuário deixa de ser "consumidor pra uso pessoal"** (baixo risco) **e vira "distribuidor"** (criminal)
- Você, operando a mesh, é **co-autor** da distribuição

**Veredito Modelo B:** NÃO FAÇA. Transforma o modelo inteiro em Popcorn Time — criminal, enforcement ativo, destrói a defesa legal do "sou só revendedor/indexador".

#### Modelo C — Cache P2P SÓ para domínio público (a jogada legal) ⭐

**Como funciona:** a biblioteca de domínio público (Machado de Assis, cinema mudo, Carlos Gomes) é distribuída via P2P mesh entre usuários. Conteúdo protegido continua via TorBox (centralizado, pago).

**Legalidade:** 🟢 **100% LEGAL.** Domínio público = livre para distribuir, copiar, redistribuir. Lei 9.610/98 Art. 41. Ninguém tem direitos a proteger.

**Economia:** 🟡 **Economia parcial.** Reduz custo de banda do servidor da biblioteca DP (que cresce com usuários). Não reduz custo do TorBox (que é o item principal, R$ 15/usuário).

### 2.3 A verdade sobre "baratear"

Aqui está o ponto honesto que precisa ser claro:

| Custo | Valor | Cache distribuído ajuda? |
|---|---|---|
| **TorBox por usuário** | R$ 15/mês | 🔴 **NÃO** — TorBox cobra por conta, independente de cache |
| **Banda do addon** | ~R$ 0-2/usuário | 🟡 Sim (P2P DP) |
| **Banda biblioteca DP** | ~R$ 0-1/usuário | 🟢 Sim (P2P DP, grande economia em escala) |
| **Infra fixa (VPS)** | R$ 120/mês | 🔴 Não |

**O custo dominante é o TorBox (R$ 15/usuário), e cache distribuído NÃO reduz isso.** TorBox cobra por conta ativa, não por banda consumida.

### 2.4 O que REALMENTE barateia o TorBox

Para reduzir o custo do TorBox (o item caro), as alavancas são:

| Alavanca | Economia | Risco |
|---|---|---|
| **Escala no Partner Program** (desconto crescente) | 10% → 15%+ | Baixo |
| **Plano annual prepaid** (se TorBox oferecer) | ~20% | Baixo |
| **Usuários no free tier do TorBox** (10GB/download) | Total (grátis) | Médio — limitado, não serve pra série/filme grande |
| **Self-hosted debrid cooperativo** (você opera) | Total (só custo infra) | 🔴 ALTO — vira você o operador do debrid, criminal |
| **Substituir TorBox por AllDebrid bulk** | ~20% | Baixo |

### 2.5 Self-hosted debrid cooperativo — a tentação perigosa

A ideia óbvia pra baratear: "por que pagar TorBox se posso rodar meu próprio debrid cache?"

**Como funcionaria:** você aluga servidor com storage, usuários mandam torrents, você cacheia, serve via stream.

**Legalidade:** 🔴 **VOCÊ VIRA O REAL-DEBRID.** Isso é exatamente o modelo que analisamos antes e descartamos — reprodução (Lei 9.610/98 Art. 5 VI), criminal (Art. 184 CP), ANCINE bloqueia. Todo o escudo jurídico de "sou só revendedor" desaparece.

**Não faça.** O ponto de revender TorBox é exatamente NÃO ser o operador do debrid.

---

## 3. ESTRATÉGIA RECOMENDADA

### 3.1 Plataformas: Stremio-first

```
Fase 1:  Stremio em todas plataformas (celular, TV, web) — custo zero
         Biblioteca DP como PWA (web responsivo)
Fase 2:  App Android próprio (billing + biblioteca DP + onboarding)
         Stremio permanece o player
Fase 3:  App player próprio só se Stremio virar gargalo (caro, opcional)
```

### 3.2 Cache: híbrido legal

```
Biblioteca Domínio Público:  P2P mesh entre usuários (WebTorrent)
                              → 100% legal, economiza banda em escala
                              → Diferencial técnico: "nossa biblioteca DP é distribuída"

Conteúdo protegido (TorBox):  Cache no TorBox (centralizado)
                              → Não tentar P2P aqui (criminal)
                              → Reduzir custo via escala Partner Program

Cache pessoal (opcional):     Usuário pode baixar pra offline no próprio dispositivo
                              → Legal, bom pra UX, não economiza TorBox
```

### 3.3 O que NÃO fazer

| Ideia | Por que não |
|---|---|
| P2P mesh para conteúdo protegido | Criminal (Popcorn Time model) |
| Self-hosted debrid cooperativo | Você vira o operador, criminal |
| Compartilhar contas TorBox entre usuários | Viola termos do TorBox, abuse system, ban |
| Cache redistributivo entre usuários (protegido) | Distribuição sem licença, criminal |

---

## 4. CENÁRIO OTIMIZADO DE CUSTO (com P2P DP)

### Sem P2P (modelo atual)

| Item | 100 usuários | 1.000 usuários |
|---|---|---|
| TorBox (R$ 15/usuário) | R$ 1.500 | R$ 15.000 |
| Infra (VPS + banda DP) | R$ 200 | R$ 800 |
| **Total variável** | R$ 1.700 | R$ 15.800 |

### Com P2P na biblioteca DP

| Item | 100 usuários | 1.000 usuários |
|---|---|---|
| TorBox (R$ 15/usuário) | R$ 1.500 | R$ 15.000 |
| Infra (VPS + banda DP via P2P) | R$ 150 | R$ 300 |
| **Total variável** | R$ 1.650 | R$ 15.300 |

**Economia:** marginal (R$ 500/mês em 1.000 usuários). **O TorBox domina o custo.**

### Conclusão honesta

**Cache distribuído NÃO barateia significativamente** porque o custo dominante é o TorBox (por conta), não banda. A única forma de baratear de verdade é:

1. **Escala no Partner Program** (10% → 15% desconto)
2. **Plano anual** (se disponível)
3. **Free tier do TorBox** para usuários leves (10GB/download)

O P2P faz sentido para a **biblioteca domínio público** não por economia, mas por:
- **Diferencial técnico** ("biblioteca distribuída, resiliente")
- **Resiliência** (servidor cai, biblioteca continua no ar via mesh)
- **Story de marketing** ("rede comunitária de cultura livre")

---

## 5. RESPOSTA DIRETA

### Atingir celulares, TVs, web?
**Sim, sem custo.** Stremio já está em Android, Android TV, Samsung Tizen, LG webOS, iOS, Windows, macOS, Linux, web. Você só precisa do addon. App próprio é caro e desnecessário na Fase 1.

### Apps próprios?
**Viável mas NÃO recomendado agora.** Custo R$ 30-100k+, manutenção alta, risco de ban nas lojas. Faça só na Fase 3 se Stremio virar gargalo. TorBox tem API oficial, tecnicamente possível (referência: app STREAMED em Flutter).

### Cache distribuído pra baratear?
**Não barateia o custo principal (TorBox).** O TorBox cobra por conta, não por banda. P2P mesh economiza banda da biblioteca DP (marginal). Para conteúdo protegido, P2P é **criminal** (Popcorn Time). A única economia real vem de escala no Partner Program.

### A jogada inteligente
- **P2P para domínio público** → legal, diferencial técnico, resiliência
- **TorBox centralizado para protegido** → seguro, legal
- **Escala Partner Program** → economia real (10-15% desconto)
- **Stremio em tudo** → zero custo de plataforma

---

## Fontes
- Stremio Smart TV: https://stremio.zendesk.com/hc/en-us/articles/360021473791-Smart-TV
- Stremio LG TV: https://blog.stremio.com/stremio-is-now-available-on-lg-tvs-for-models-2020/
- Stremio downloads: https://www.stremio.com/downloads
- TorBox API npm: https://registry.npmjs.org/@torbox/torbox-api
- STREAMED app (TorBox integration Flutter): https://github.com/chandradev28/streamed.app
- React Native TV (Callstack): https://www.callstack.com/blog/cross-platform-tv-apps-with-react-native-for-tvos-android-tv-and-tizen
- Popcorn Time Brazil lawsuit: https://tecnoblog.net/noticias/popcorn-time-e-seus-usuarios-levam-processo-por-pirataria-de-filmes/
- Popcorn Time US users sued: https://torrentfreak.com/movie-studio-sues-popcorn-time-users-in-the-u-s-150819
- Popcorn Time operator convicted: https://torrentfreak.com/movie-companies-sue-popcorn-time-operator-in-us-court-190102
- ISP P2P caching legal analysis: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1670289
- Plex legal/licensing: https://support.plex.tv/articles/is-plex-legal/
