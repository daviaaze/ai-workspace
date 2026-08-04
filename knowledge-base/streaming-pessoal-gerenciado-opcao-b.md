# Opção B: Streaming Pessoal Gerenciado — Análise Legal + Infra + Investimento

**Data:** 2026-07-06
**Modelo:** Serviço gerenciado de Jellyfin/Plex + stack *arr (automação de biblioteca pessoal)
**Princípio:** O usuário é dono do conteúdo e da sourcing; a plataforma só fornece infraestrutura + automação

---

## 1. ANÁLISE LEGAL

### 1.1 O modelo em uma frase

> "Você nos paga para hospedar e manter o Jellyfin + Sonarr/Radarr para você.
> Você conecta seus próprios indexadores, sua própria VPN/debrid, sua própria biblioteca.
> Nós não tocamos, não hospedamos, não distribuímos conteúdo — só rodamos o software."

### 1.2 Enquadramento jurídico

**Classificação: Provedor de Aplicação de Internet (PAI) — especificamente Provedor de Hospedagem (IaaS/PaaS)**

O serviço se enquadra como **provedor de hospedagem de aplicações**, não como provedor de conteúdo. Você fornece infraestrutura computacional + automação de deploy, o usuário é o controlador dos dados e do conteúdo.

### 1.3 O que a legislação brasileira diz

#### Marco Civil da Internet (Lei 12.965/2014)
- **Art. 18**: provedores de conexão não respondem por conteúdo de terceiro
- **Art. 19** (pós-STF Tema 987, jun/2025): regime de **notice and takedown** — você precisa remover conteúdo ilícito após notificação, mas **não precisa monitorar proativamente**
- **Art. 21**: já aplicava notice and takedown para nudez não consensual — agora é a regra geral

#### Decreto 12.975/2026 (vigência 20/jul/2026)
- **Art. 16-A**: representante legal no Brasil (obrigatório) ← ✅ você é brasileiro, resolve
- **Art. 16-B**: dever de cuidado para **conteúdo criminoso grave** (terrorismo, CSAM, discurso de ódio) — **NÃO se aplica a direitos autorais**
- **Art. 16-O**: exceções para e-mail, mensageria — não relevante aqui
- **Art. 16-P**: critérios diferenciados para **pequenos provedores** ← ✅ importante, reduz carga
- **Fiscalização**: ANPD

#### Lei de Direitos Autorais (9.610/98)
- **Art. 5, VI**: reprodução = armazenamento permanente ou temporário
- ⚠️ **Se VOCÊ cacheia/reproduz obra = infrator direto**
- ✅ **Se o USUÁRIO baixa e armazena no próprio espaço = responsabilidade do usuário**

#### ANCINE — Lei 14.815/2024 + IN 174/2026
- ANCINE age contra **serviços dedicados à pirataria** e **intermediários**
- Define "intermediário" na cadeia de pirataria
- ⚠️ Um provedor de hospedagem PODE ser notificado como intermediário
- ✅ Mas se você coopera com notice and takedown, risco é controlável

### 1.4 O precedente ElfHosted (gringo, mas referência)

ElfHosted opera exatamente esse modelo e estruturou a defesa legal assim:

1. **"Hosting-only service"** — declaração clara de que só fornece infraestrutura
2. **"Common carrier"** — se posiciona como operadora neutra
3. **No-piracy policy** explícita — proíbe sourcing talk, links, redistribuição
4. **User responsibility clause** — usuário garante ter direitos sobre o conteúdo
5. **Indemnity clause** — usuário indeniza a plataforma por claims
6. **Takedown compliance** — coopera com DMCA/DSA notices
7. **Jurisdição**: Nova Zelândia (foro neutro)

### 1.5 O precedente EnxadaHost (brasileiro, referência direta)

A EnxadaHost (BR, CNPJ, termos de uso públicos) estrutura assim:

1. **"Provedora de infraestrutura tecnológica de hospedagem"** — não exerce controle editorial
2. **IaaS explícito** — "responsabilidade começa e termina na disponibilização dos recursos computacionais"
3. **Cliente é controlador dos dados** (LGPD) — EnxadaHost é operadora
4. **Proibição de cyberlocker/torrent massivo** nos termos — **importante**: eles vedam uso como repositório de arquivos massivo e distribuição torrent
5. **Indenização** — cliente indeniza por violações de IP
6. **Combate a abusos graves** — remove conteúdo por notificação de autoridade

### 1.6 ⚠️ O ponto crítico — onde a EnxadaHost alerta

A EnxadaHost **vede explicitamente** em seus termos:
- "repositório ou sistema de armazenamento de arquivos, como cyberlocker"
- "distribuição massiva de arquivos para download por outros websites, como content delivery"
- "torrent, cyberlocker"

**Isso significa que um provedor de hospedagem brasileiro SE protege vedando esses usos.** Se você for montar um serviço, precisa de termos igualmente restritivos OU uma estrutura que não caracterize "distribuição massiva".

### 1.7 Veredito Legal da Opção B

| Aspecto | Status |
|---|---|
| **Modelo "hospedagem + automação" em si** | ✅ **Viável** — é IaaS/PaaS, tem safe harbor do Marco Civil |
| **Você hospedar Jellyfin + Sonarr/Radarr** | ✅ **Legal** — software de propósito geral |
| **Usuário baixar conteúdo no próprio espaço** | ⚠️ **Risco do usuário**, não seu — mas precisa de termos claros |
| **Você fornecer indexadores pré-configurados** | 🔴 **Risco alto** — pode configurar "intermediário" na pirataria |
| **Você fazer cache/streaming** | 🔴 **Ilegal** — não faça isso |
| **Notice and takedown funcionar** | ✅ **Sim** — basta cooperar com notificações |
| **ANCINE poder notificar** | ⚠️ **Sim** — mas cooperação resolve a maioria dos casos |
| **Responsabilidade penal (Art. 184 CP)** | ✅ **Baixa** — você não reproduz, o usuário reproduz |

#### Condições para viabilidade:
1. **Termos de serviço sólidos** (copiar estrutura EnxadaHost + ElfHosted)
2. **NÃO pré-configurar indexadores piratas** — deixar usuário configurar
3. **Política de takedown clara e rápida** (24-48h)
4. **Representante legal no Brasil** (você mesmo)
5. **LGPD compliance** — você é operador, usuário é controlador
6. **Proibir redistribuição pública** da biblioteca do usuário
7. **Consultar advogado especialista** antes de launch

---

## 2. INFRAESTRUTURA NECESSÁRIA

### 2.1 Arquitetura do serviço

```
Usuário final
    │
    ├─ Acesso via Jellyfin (web/app/TV)
    │
    ▼
[Servidor do usuário — VPS dedicado ou container]
    │
    ├─ Jellyfin          → player
    ├─ Sonarr/Radarr     → automação
    ├─ Prowlarr          → agregador de indexers (usuario configura)
    ├─ qBittorrent       → download (VPN do usuário ou própria)
    ├─ FlareSolverr      → bypass Cloudflare
    └─ Storage           → biblioteca de mídia
    │
    ▼
[Plataforma de gerenciamento (você)]
    ├─ Painel de controle (deploy, billing, suporte)
    ├─ Automação (Docker/K8s, backups, updates)
    ├─ Billing (PIX, cartão)
    └─ Monitoramento
```

### 2.2 Dois modelos de deploy

#### Modelo A: VPS por usuário (ElfHosted-style)
- Cada usuário tem sua própria VPS/containers
- Isolamento total
- Storage: o usuário traz (rclone/Google Drive) OU você fornece storage extra
- Custo por usuário: R$ 30-80/mês (VPS small)

#### Modelo B: Multi-tenant (mais econômico)
- Um cluster K8s grande, namespaces por usuário
- Storage compartilhado (com quotas)
- Mais barato por usuário, mas complexidade técnica maior
- Risco: um usuário problemático afeta outros

**Recomendação:** Começar com Modelo A (VPS por usuário) — mais simples, mais seguro legalmente (isolamento reforça "não sou provedor de conteúdo").

### 2.3 Requisitos por usuário (estimativa)

| Recurso | Mínimo | Recomendado | Notas |
|---|---|---|---|
| CPU | 2 vCPU | 4 vCPU | Transcoding é CPU-intensivo |
| RAM | 4 GB | 8 GB | Jellyfin + arr stack |
| Storage | 100 GB | 1-4 TB | Biblioteca de mídia |
| Banda | 1 TB/mês | 5-10 TB/mês | Streaming é o gargalo |
| Upload | 100 Mbps | 1 Gbps | Transcode direto dispensa, indireto precisa |

---

## 3. ESTIMATIVA DE INVESTIMENTO

### 3.1 Custos de infraestrutura (por mês)

#### Opção 1: Hetzner (Alemanha — melhor custo-benefício, latência ok para BR)

| Recurso | Spec | Preço (EUR) | Preço (R$ aprox) |
|---|---|---|---|
| CPX21 (por usuário) | 3 vCPU, 4GB, 80GB | €6.55/mês | ~R$ 35 |
| CX22 (por usuário) | 2 vCPU, 4GB, 80GB | €4.55/mês | ~R$ 25 |
| Storage Box 1TB (compartilhado) | 1TB | €3.81/mês | ~R$ 20 |
| Dedicated (gerenciamento) | AX41-NVMe | €35/mês | ~R$ 190 |
| Banda | 20TB incluído | — | — |

#### Opção 2: Brasil (data center nacional — baixa latência)

| Recurso | Spec | Preço (R$) |
|---|---|---|
| VPS Storage 2TB (OTHHost) | 2TB, 4GB | ~R$ 80-150/mês |
| VPS Storage 4TB | 4TB, 8GB | ~R$ 200-350/mês |
| VPS comum 4GB | 4GB, 2vCPU | ~R$ 40-80/mês |

#### Opção 3: Híbrido (recomendado)
- **Compute no Brasil** (VPS comum, baixa latência para o usuário assistir)
- **Storage no Hetzner** (Storage Box, barato, montado via rclone/SMB)
- Banda: Hetzner dá 20TB incluído, Brasil cobra tráfego

### 3.2 Custo por usuário ativo (Modelo A — VPS por usuário)

| Item | Custo/mês (R$) |
|---|---|
| VPS CX22 Hetzner (2vCPU, 4GB) | 25 |
| Storage 1TB (Storage Box compartilhado, ~1/5 usuários) | 4 |
| Banda (incluso Hetzner até 20TB) | 0 |
| Gateway de pagamento (PIX) | 1 |
| **Custo marginal por usuário** | **~30** |

### 3.3 Custos fixos (plataforma)

| Item | Custo inicial (R$) | Custo/mês (R$) |
|---|---|---|
| Desenvolvimento (painel, automação, site) | 15.000-40.000 | — |
| Servidor de gerenciamento | — | 100-300 |
| Domínio + DNS | 100/ano | — |
| Gateway PIX (Mercado Pago/Stripe) | 0 setup | 1-2% por transação |
| Email transacional (SendGrid/Postmark) | — | 50-150 |
| Monitoring (Grafana/UptimeRobot) | — | 0-100 |
| Advogado (parecer + termos) | 5.000-15.000 | — |
| Contador (CNPJ, fiscal) | 2.000 | 300-800 |
| Marketing inicial | 2.000-5.000 | — |
| **Total setup** | **25.000-60.000** | **500-1.500** |

### 3.4 Unit economics (por usuário)

| Métrica | Valor |
|---|---|
| Preço sugerido (planos) | R$ 39-79/mês |
| Custo marginal | ~R$ 30/mês |
| **Margem por usuário** | **R$ 9-49/mês** |
| CAC estimado (marketing orgânico + comunidade) | R$ 20-50 |
| Payback CAC | 1-3 meses |
| LTV (12 meses @ R$ 59, 80% retenção) | ~R$ 566 |
| LTV/CAC | 11-28x |

### 3.5 Break-even

| Cenário | Usuários para break-even fixo |
|---|---|
| Custo fixo R$ 1.000/mês, margem R$ 20/usuário | 50 usuários |
| Custo fixo R$ 1.500/mês, margem R$ 29/usuário (plano R$ 59) | 52 usuários |
| Custo fixo R$ 2.000/mês, margem R$ 29/usuário | 69 usuários |

**Break-even: ~50-70 usuários pagantes.** Mercado potencial: 50k+ usuários BR órfãos do RD.

### 3.6 Investimento total para MVP

| Fase | Valor (R$) |
|---|---|
| Setup legal (advogado, CNPJ, termos) | 7.000-20.000 |
| Desenvolvimento MVP (painel + automação + site) | 15.000-40.000 |
| Infra inicial (3 meses, 50 usuários) | 5.000-10.000 |
| Marketing + comunidade inicial | 2.000-5.000 |
| Reserva (3 meses operação) | 5.000-10.000 |
| **Total MVP** | **34.000-85.000** |

**Cenário enxuto (bootstrapped, você desenvolve):** R$ 15.000-30.000
**Cenário com outsourced dev:** R$ 50.000-85.000

---

## 4. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| ANCINE notifica como intermediário | Média | Médio | Takedown em 24h, cooperação |
| Usuário redistribui biblioteca publicamente | Alta | Médio | Proibir nos termos, detectar, suspender |
| Data center BR fecha conta por torrent | Média | Alto | Usar Hetzner (tolerante) ou proibir torrent direto, só debrid/VPN |
| Concorrência (ElfHosted entra no BR) | Baixa | Médio | Foco em PT-BR, PIX, suporte local |
| LGPD non-compliance | Baixa | Alto | Termos claros, DPO,EncCrypt |
| STF/Congresso muda regra de plataformas | Média | Médio | Acompanhar, adaptar termos |

---

## 5. ROADMAP SUGERIDO

### Fase 0 — Validação legal (1-2 semanas)
1. Consultar advogado especialista em direito digital (orçar parecer)
2. Validar modelo de termos (baseado em EnxadaHost + ElfHosted)
3. Decidir estrutura: VPS por usuário vs multi-tenant

### Fase 1 — MVP (1-2 meses)
1. CNPJ + contador
2. Painel mínimo (deploy VPS, billing PIX, suporte)
3. 5-10 beta testers (comunidade Stremio/Jellyfin BR)
4. Termos de serviço + LGPD

### Fase 2 — Launch (mês 3)
1. Site + pricing
2. Marketing em comunidades (Reddit r/pirataria, Discord)
3. Onboarding guiado (tutoriais PT-BR)

### Fase 3 — Escala (mês 4-6)
1. Automação avançada (backups, updates)
2. Add-ons (metadata PT-BR, indexadores BR como opcional)
3. Parcerias (criadores de conteúdo, YouTubers tech BR)

---

## 6. DIFERENCIAIS COMPETITIVOS (vs ElfHosted)

| Diferencial | ElfHosted | Você (BR) |
|---|---|---|
| Idioma | Inglês | **PT-BR nativo** |
| Pagamento | Cartão/cripto | **PIX** |
| Suporte | Discord inglês | **Suporte em português** |
| Latência | Europa | **Brasil (opcional)** |
| Tutoriais | Inglês | **PT-BR com contexto BR** |
| Indexadores BR | Genéricos | **Opcional: GuIndex, DF Indexer** |
| Comunidade | Global | **Comunidade BR (Reddit, Discord)** |
| Preço | $9-29 USD (~R$ 50-160) | **R$ 39-79** |

---

## 7. CONCLUSÃO

**Veredito: Opção B é viável legalmente e financeiramente.**

- **Legal:** Modelo de hospedagem + automação tem safe harbor, desde que com termos sólidos e notice and takedown funcionando
- **Investimento:** R$ 15-85k dependendo do caminho (bootstrapped vs outsourced)
- **Break-even:** ~50-70 usuários
- **Mercado:** 50k+ potenciais
- **Diferencial:** PT-BR, PIX, comunidade local, preço acessível

**Próximos passos recomendados:**
1. Orçar parecer jurídico com advogado especialista (IBDDIG, Patricia Peck, ou escritório tech)
2. Validar termos com base EnxadaHost + ElfHosted
3. Decidir: bootstrapped (você dev) vs outsourced
4. Se GO, montar MVP com 5-10 beta testers da comunidade

---

## Fontes
- ElfHosted ToS: https://docs.elfhosted.com/legal/terms-of-service/
- ElfHosted No-piracy: https://store.elfhosted.com/legal/no-piracy-policy/
- ElfHosted pricing: https://docs.elfhosted.com/pricing/
- EnxadaHost ToS: https://enxadahost.com/termos-de-uso.pdf
- Hetzner Storage Box: https://www.hetzner.com/storage/storage-box/
- Hetzner Cloud: https://www.hetzner.com/cloud
- Elestio Jellyfin: https://elest.io/open-source/jellyfin/resources/plans-and-pricing
- OTHHost VPS Storage: https://othhost.com.br/vps-storage
- STF Tema 987: https://noticias.stf.jus.br/postsnoticias/stf-define-parametros-para-responsabilizacao-de-plataformas-por-conteudos-de-terceiros/
- Decreto 12.975/2026: https://planalto.gov.br/ccivil_03/_ato2023-2026/2026/decreto/d12975.htm
- Marco Civil: https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2014/lei/l12965.htm
- ANCINE IN 174/2026: https://www.gov.br/ancine/pt-br/acesso-a-informacao/legislacao/instrucoes-normativas/instrucao-normativa-174
