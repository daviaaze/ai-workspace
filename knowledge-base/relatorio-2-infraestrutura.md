# Relatório 2: Estruturação de Infraestrutura
# Dados reais de precificação, capacidade e arquitetura

**Data:** 2026-07-06
**Metodologia:** Preços oficiais de provedores (Hetzner, TorBox), dados de capacidade técnica documentados
**Escopo:** Infraestrutura necessária para servir um serviço de streaming com indexador agregador, addon Stremio, e revenda de debrid

---

## SUMÁRIO

1. [Infraestrutura base — Hetzner Cloud](#1-infraestrutura-base--hetzner-cloud)
2. [Debrid — TorBox Partner Program](#2-debrid--torbox-partner-program)
3. [Infraestrutura complementar — FlareSolverr, Redis, Storage](#3-infraestrutura-complementar)
4. [Custo total mensal por escala](#4-custo-total-mensal-por-escala)
5. [Comparação com alternativas](#5-comparação-com-alternativas)
6. [Arquiteturas possíveis](#6-arquiteturas-possíveis)

---

## 1. Infraestrutura Base — Hetzner Cloud

### 1.1 Precificação (efetiva 15/jun/2026)

**Fonte:** costgoat.com/pricing/hetzner (última atualização: 29/jun/2026) + hetzner.com/cloud/regular-performance

#### Instâncias Cost-Optimized (CX — vCPU compartilhadas Intel/AMD)

| Instância | vCPU | RAM | SSD | Tráfego | Preço/mês (EUR) | Preço/mês (R$, ~5.60) |
|---|---|---|---|---|---|---|
| **CX23** | 2 | 4 GB | 40 GB | 20 TB | €5.49 | ~R$ 31 |
| **CX33** | 4 | 8 GB | 80 GB | 20 TB | €8.49 | ~R$ 48 |
| **CX43** | 8 | 16 GB | 160 GB | 20 TB | €15.99 | ~R$ 90 |
| **CX53** | 16 | 32 GB | 320 GB | 20 TB | €29.49 | ~R$ 165 |

#### Instâncias Regular Performance (CPX — AMD EPYC compartilhadas)

| Instância | vCPU | RAM | SSD | Tráfego | Preço/mês (EUR) | Preço/mês (R$) |
|---|---|---|---|---|---|---|
| **CPX11** | 2 | 2 GB | 40 GB | 20 TB | €4.99 | ~R$ 28 |
| **CPX21** | 3 | 4 GB | 80 GB | 20 TB | €7.99 | ~R$ 45 |
| **CPX31** | 4 | 8 GB | 160 GB | 20 TB | €13.99 | ~R$ 78 |
| **CPX41** | 8 | 16 GB | 240 GB | 20 TB | €27.49 | ~R$ 154 |

**Nota sobre o aumento de preços (15/jun/2026):** CX/CAX subiram 30-40%, CPX/CCX mais que dobraram em relação a 2025. Para novas instâncias, usar estes valores.

#### Storage Box (armazenamento adicional)

| Capacidade | Preço/mês (EUR) | Preço/mês (R$) |
|---|---|---|
| **1 TB** | €3.81 | ~R$ 21 |
| **5 TB** | €12.68 | ~R$ 71 |
| **10 TB** | €20.82 | ~R$ 117 |

Acessível via FTP, SFTP, SCP, RSYNC, WebDAV, Samba. RAID com checksum. Snapshots.

#### Add-ons

| Add-on | Custo |
|---|---|
| IPv4 | €0.50/mês por instância (~R$ 2.80) |
| Backups automáticos | 20% do custo da instância |
| Block Storage | €0.0572/GB/mês (~R$ 0.32/GB) |
| Snapshots | €0.0143/GB/mês (~R$ 0.08/GB) |
| Tráfego excedente (EU) | €1/TB (~R$ 5.60/TB) |
| Load Balancer | €5.39/mês (~R$ 30) |

### 1.2 Capacidade de banda

- Conexão do host: **10 Gbit redundante** (compartilhada entre instâncias)
- Banda esperada por instância: **~300-500 Mbits** (sem garantia contratual)
- Tráfego incluído: **20 TB/mês** em todas as instâncias Alemanha/Finlândia

**Stream de vídeo típico (1080p, ~8 Mbps):**
- 1 usuário assistindo 2h/dia = 30 × 2 × 3600 × 8 / 8 / 1024² = ~0.21 TB/mês
- 20 TB suporta ~95 usuários assistindo 2h/dia em 1080p (sem transcoding)
- Com 300 Mbps, ~37 streams simultâneos (8 Mbps cada)

**Para o addon/indexador (não serve vídeo, só metadados):**
- Metadados são leves (KB por request)
- 20 TB é mais que suficiente para milhões de requisições de metadados
- O gargalo é CPU/RAM para scraping, não banda

---

## 2. Debrid — TorBox Partner Program

### 2.1 Precificação de revenda

**Fonte:** support.torbox.app/en/articles/14426727-torbox-partners-pricing (oficial)

#### Account Reseller

| Usuários cumulativos | Desconto sobre MSRP | Custo TorBox Essential (~$3/mês) |
|---|---|---|
| **1-19** | 0% (sem Partner Program, usuário paga direto) | $3.00 |
| **20** | 10% | $2.70 |
| **50** | (não especificado — provável 10-12%) | ~$2.55-2.70 |
| **100** | (não especificado — escala negociada) | ~$2.25-2.55 |
| **(escala maior)** | Verificar diretamente com TorBox | Negociado |

**Regra documentada:** "Discount amounts are based purely on how many accounts you have cumulatively on your vendor." Ou seja, o desconto escala com volume mas os tiers exatos acima de 10% não estão publicados — são negociados.

#### Voucher Reseller

- **Desconto flat: 15%** (independente do volume)
- Faturamento mensal, CSV com vouchers gerados e resgatados
- "More custom work, and more stringent on-boarding, as well as negotiation of fees"

### 2.2 Custo de revenda por usuário (planos TorBox)

| Plano | MSRP (~USD) | Custo revenda 10% desc | Custo revenda 15% desc (voucher) | R$ (10% desc, ~5.60) | R$ (15% desc) |
|---|---|---|---|---|---|
| **Essential** | $3/mês | $2.70 | $2.55 | ~R$ 15.10 | ~R$ 14.30 |
| **Standard** | $5/mês | $4.50 | $4.25 | ~R$ 25.20 | ~R$ 23.80 |
| **Pro** | $10/mês | $9.00 | $8.50 | ~R$ 50.40 | ~R$ 47.60 |

*Cotação USD→BRL estimada em R$ 5.60. Varia conforme câmbio do dia.*

### 2.3 Mecânica de cobrança (Partner Program)

- **Billing:** 7 dias antes do vencimento da conta vendor (ciclo de 31 dias)
- **Você paga TorBox:** por número de usuários ativos na data do faturamento
- **Responsabilidade:** se usuário não te pagar, você ainda deve ao TorBox se não remover o usuário antes do faturamento
- **Sem negociação de valores de fatura:** "There is no negotiation on invoice amounts, and you are expected to pay within 7 days"

### 2.4 TorBox Free Tier (usuários não pagantes)

- 10 GB por download
- Downloads limitados
- **Não gera custo para o revendedor** (contas free não são faturadas)
- Pode ser usado como trial ou plano gratuito

---

## 3. Infraestrutura Complementar

### 3.1 FlareSolverr / Solvearr (bypass Cloudflare)

Indexadores brasileiros (BLUDV, COMANDO, STARCK, etc.) frequentemente usam Cloudflare.

**Alternativas auto-hospedadas:**
- **FlareSolverr** (Python, original, comunidade ativa)
- **Solvearr** (nabil-ak/Solvearr, compatível Prowlarr/Sonarr/Radarr)
- **FlareSolverr-Go** e **FlareSolverr-RS** (implementações alternativas)

**Requisitos para FlareSolverr:**
- ~512 MB RAM por instância
- ~1 vCPU
- Usa Chrome headless → consumo de RAM variável
- Para 1.000 usuários de addon: estima-se 1-2 instâncias FlareSolverr

### 3.2 Redis / Meilisearch (cache e busca)

- **Redis:** cache de metadados, resultados de scraping. ~100-200 MB RAM para catálogo de milhares de itens
- **Meilisearch:** busca full-text em metadados. ~200-500 MB RAM

### 3.3 Storage para biblioteca de domínio público

- Catálogo inicial: ~500 obras (literatura, cinema mudo, música)
- Tamanho médio: livros ~1 MB, filmes ~2 GB, áudio ~100 MB
- Estimativa total: ~100-500 GB para catálogo inicial
- **Storage Box 1 TB:** €3.81/mês (~R$ 21) — mais que suficiente
- Ou armazenar no próprio VPS (Storage Box só se precisar de mais espaço)

---

## 4. Custo Total Mensal por Escala

### 4.1 Cenário mínimo (MVP — até 50 usuários)

| Componente | Recurso | Custo mensal (R$) |
|---|---|---|
| VPS addon/indexador | CX23 (2 vCPU, 4GB, 40GB, 20TB) | 31 |
| FlareSolverr | No mesmo VPS ou CX23 separado | 0-31 |
| Storage Box | 1 TB (biblioteca DP) | 21 |
| TorBox Essential (revenda) | ~20 usuários × R$ 15.10 | 302 |
| Domínio + DNS | | 5 |
| Email transacional | SendGrid free tier ou similar | 0 |
| Monitoring | UptimeRobot free tier ou similar | 0 |
| **Total mensal (50 usuários)** | | **~359-390** |

### 4.2 Cenário intermediário (200 usuários)

| Componente | Recurso | Custo mensal (R$) |
|---|---|---|
| VPS addon/indexador | CX33 (4 vCPU, 8GB, 80GB, 20TB) | 48 |
| FlareSolverr | CX23 separado | 31 |
| Redis/Meilisearch | No VPS addon (upgrade RAM) | 0 |
| Storage Box | 1 TB | 21 |
| TorBox Essential (revenda) | 200 × R$ 15.10 (mantendo 10% desc) | 3.020 |
| Domínio + DNS | | 5 |
| Email transacional | Plano pago (~10k emails/mês) | 50 |
| Monitoring | Plano pago | 50 |
| **Total mensal (200 usuários)** | | **~3.225** |

### 4.3 Cenário escala (1.000 usuários)

| Componente | Recurso | Custo mensal (R$) |
|---|---|---|
| VPS addon/indexador | CX43 (8 vCPU, 16GB, 160GB, 20TB) | 90 |
| FlareSolverr × 2 | 2 × CX23 | 62 |
| Redis (dedicado) | CX23 separado | 31 |
| Storage Box | 5 TB (biblioteca expandida) | 71 |
| TorBox Essential (revenda) | 1.000 × ~R$ 14.30 (15% desc voucher) | 14.300 |
| Load Balancer | Hetzner LB | 30 |
| Domínio + DNS | | 5 |
| Email transacional | Plano médio | 100 |
| Monitoring | Plano pago | 100 |
| **Total mensal (1.000 usuários)** | | **~14.789** |

### 4.4 Custo por usuário (visão resumida)

| Escala | Infra (fixo) | TorBox (por usuário) | Total | Custo/usuário |
|---|---|---|---|---|
| 50 usuários | ~R$ 88 | R$ 302 | R$ 390 | R$ 7.80 |
| 200 usuários | ~R$ 205 | R$ 3.020 | R$ 3.225 | R$ 16.13 |
| 1.000 usuários | ~R$ 489 | R$ 14.300 | R$ 14.789 | R$ 14.79 |

**Observação:** O TorBox domina o custo (>90% do custo total em escala). A infraestrutura própria (VPS, storage, DNS) é marginal — menos de R$ 500/mês mesmo com 1.000 usuários.

---

## 5. Comparação com Alternativas

### 5.1 Infraestrutura no Brasil (alternativa ao Hetzner)

| Provedor | Recurso similar | Preço (R$) |
|---|---|---|
| **OTHHost VPS Storage** | 2TB, 4GB | ~80-150/mês |
| **Hostinger VPS** | 4GB, 2 vCPU, 100GB | ~60-100/mês |
| **Locaweb VPS** | 4GB, 2 vCPU | ~100-200/mês |

**Trade-off:** Brasil = latência menor para usuário BR, mas custo 3-8× maior e banda muito mais restrita. Hetzner Alemanha = latência ~200ms para BR (aceitável para addon, ruim para streaming de vídeo), mas custo baixo e 20 TB de tráfego incluso.

### 5.2 Addon sem debrid (usuário faz P2P direto)

| Componente | Custo |
|---|---|
| Infra addon | Igual (R$ 31-90/mês) |
| TorBox | R$ 0 (eliminado) |
| **Custo total** | **R$ 31-90/mês independente da escala** |

**Implicação:** sem TorBox, o custo marginal por usuário é **zero**. Mas o usuário precisa de VPN própria (R$ 30-50/mês), expõe IP no swarm, não tem cache, velocidade depende de seeders.

### 5.3 Self-hosted debrid (NÃO recomendado — ver Relatório 1)

Se você operasse seu próprio cache (servidor com qBittorrent + storage servindo streams):

| Componente | Custo |
|---|---|
| Storage | €0.0572/GB/mês × 10 TB = €572/mês (~R$ 3.200) |
| Banda | 20 TB incluído (CX) ou excedente €1/TB |
| TorBox | R$ 0 (eliminado) |
| **Custo total** | **R$ 3.200+/mês (storage) + R$ 90 (compute)** |

**Custo por usuário (1.000 usuários):** ~R$ 3.30/usuário (vs R$ 14.30 do TorBox). **Mais barato, mas ilegal (Art. 184 CP).**

---

## 6. Arquiteturas Possíveis

### 6.1 Arquitetura A — Addon centralizado + TorBox revenda

```
[Usuário Stremio]
       │
       ▼
[Addon (seu)] ──── scrapeia ────► [Indexadores BR (BLUDV, COMANDO, etc.)]
       │                                  │
       │                                  ▼
       │                          [FlareSolverr (bypass CF)]
       │
       ▼
[Torrentio / addon retorna links]
       │
       ▼
[TorBox (cache + stream)]
       │
       ▼
[Stream para usuário]
```

**Vantagens:** simples, uma VPS serve milhares de usuários, TorBox lida com tráfego de vídeo
**Desvantagens:** dependência do TorBox, custo por usuário elevado (R$ 15)

### 6.2 Arquitetura B — Addon + P2P (domínio público) + TorBox (protegido)

```
[Usuário Stremio]
       │
       ├── Conteúdo DP ────► [P2P WebTorrent mesh]
       │                          usuários seed entre si
       │
       └── Conteúdo protegido ──► [TorBox cache + stream]
```

**Vantagens:** conteúdo DP não usa banda do servidor, resiliência
**Desvantagens:** complexidade técnica adicional, DP é fração pequena do uso

### 6.3 Arquitetura C — Addon multi-debrid (fallback)

```
[Usuário Stremio]
       │
       ▼
[Addon] ────► TorBox (primário)
       │
       └──► AllDebrid (fallback, se TorBox falhar)
```

**Vantagens:** redundância, negociação com múltiplos parceiros
**Desvantagens:** complexidade de billing, múltiplas integrações

---

## 7. Observações sobre os Dados

### 7.1 O que está confirmado
- Preços Hetzner são oficiais (costgoat.com compila do site oficial, verificado contra hetzner.com)
- TorBox Partner pricing é do help center oficial (support.torbox.app)
- TorBox planos MSRP verificados em múltiplas fontes

### 7.2 O que NÃO está confirmado (falta dado)
- **Tiers exatos de desconto do TorBox Partner acima de 10%** — o help center diz que escala com volume mas não publica a tabela completa. É negociado caso a caso.
- **TorBox Essential MSRP exato em USD** — as fontes variam entre $2.99 e $3.00. Usado $3.00 como estimativa conservadora.
- **Disponibilidade do TorBox Partner Program** — "application only" e requer projeto existente com usuários. Não é garantido.

### 7.3 Variáveis que afetam o custo real
- **Câmbio EUR→BRL e USD→BRL** — volátil, afeta tanto infra (EUR) quanto TorBox (USD)
- **Aumentos do Hetzner** — histórico de aumento (jun/2026 foi o mais recente)
- **Tráfego excedente** — Hetzner inclui 20 TB. Se o addon/indexador exceder (improvável), cobra €1/TB
- **TorBox pode aumentar preços unilateralmente** ou alterar Partner Program
- **Fiscalidade:** impostos brasileiros sobre importação de serviços (IOF, PIS/COFINS, ISS) não incluídos

---

## Conclusões do Relatório 2

1. **Infra própria é barata.** Uma VPS de R$ 31-90/mês serve o addon/indexador para milhares de usuários.

2. **O TorBox é o custo dominante.** R$ 14-15/usuário/mês, representando >90% do custo total em qualquer escala acima de 50 usuários.

3. **Eliminar o TorBox reduziria o custo a quase zero por usuário,** mas exigiria operar cache próprio (ilegal — ver Relatório 1) ou fazer P2P mesh (ilegal — ver Relatório 1).

4. **A margem de revenda é fina.** A R$ 19/mês (Essential) com custo TorBox de R$ 15, a margem bruta é R$ 4/usuário. Para margens melhores, é necessário: (a) escala para desconto maior no Partner Program, (b) preço mais alto (R$ 29+), ou (c) upsell de planos superiores.

5. **A infraestrutura escala quase sem custo adicional.** De 50 para 1.000 usuários, o custo de infra própria salta de R$ 88 para R$ 489 — apenas R$ 401 a mais para 20× mais usuários.
