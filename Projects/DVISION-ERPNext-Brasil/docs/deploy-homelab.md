# Deploy — Homelab: Dify + n8n + Frappe Bench + PostHog

> **Como ativar a stack de fábrica no homelab DVISION.**
> OmniRoute já está rodando. Só falta ativar Dify, n8n, Frappe bench e PostHog teste.

---

## 1. Ativar os Serviços no NixOS

```bash
cd ~/nixfiles
git add -A
git commit -m "feat: add dify, n8n, frappe-bench, posthog services for DVISION factory"
sudo nixos-rebuild switch --flake .#dvision-homelab
```

Isso ativa:
- ✅ **Dify** → `https://dify.local.daviaaze.com`
- ✅ **n8n** → `https://n8n.local.daviaaze.com`
- ✅ **Frappe Bench dev** → `https://dev-erpnext.local.daviaaze.com`
- ✅ **Frappe Bench staging** → `https://staging-erpnext.local.daviaaze.com`
- ✅ **PostHog (teste)** → `https://posthog.local.daviaaze.com`
- ✅ **Traefik** → rotas configuradas para todos os novos serviços

### Se encontrar erro de assertions (VFIO)
Erro conhecido, pré-existente. Ignorar e aplicar com `--show-trace`:
```bash
sudo nixos-rebuild switch --flake .#dvision-homelab 2>&1 | grep -v "vfio"
```

---

## 2. Decisão de Hosting ERPNext

| Ambiente | Onde | Finalidade |
|----------|------|------------|
| **Dev** | Homelab `frappe-bench` | Codar `erpnext_br_compliance`, testar NF-e homologação SEFAZ |
| **Staging** | Homelab `frappe-bench` (porta 8001) | Validar com cliente piloto antes de produção |
| **Produção** | **VPS Brasil** (Hetzner/qualquer) | Clientes pagantes |
| **PostHog** | Homelab (teste) + Hetzner VPS (produção) | Product analytics, feature usage, funis |

### Por que VPS Brasil em vez de Frappe Cloud?

| Fator | Frappe Cloud Frankfurt | VPS Brasil |
|-------|----------------------|------------|
| **Latência pra cliente** | 150–200ms (Alemanha) | **<10ms** |
| **Custo com 10 clientes** | $250–500/mês (10 sites) | **~$50–100/mês** (1 VPS, 10 benches) |
| **App custom `erpnext_br_compliance`** | Requer plano ≥$25/mês | ✅ **Sem restrição** |
| **DevOps** | Zero (eles fazem) | **Você já tem** (homelab NixOS) |
| **LGPD / ANPD 32/2026** | ✅ Adequação UE | ✅ **Dados no Brasil = sem transferência internacional** |
| **Upgrade v16→v17** | 1 clique | 4h anuais (você) |
| **Backup** | ✅ Incluso | Você faz (já tem no homelab) |

**Raciocínio:** Você já opera o homelab com NixOS, Docker, Traefik, backups. O custo real do seu DevOps é marginal porque você **já** mantém servidores. Frappe Cloud faria sentido se você não tivesse essa skill — mas você tem.

### E quando Frappe Cloud faz sentido?

- Se um cliente **exigir** managed hosting com SLA
- Se você quiser terceirizar upgrades major (v16→v17)
- Se o custo do seu tempo se tornar >$50/h (escala 20+ clientes)

Nesses casos, Frappe Cloud Frankfurt entra como **opção premium**, não como default.

---

## 3. Primeiro Setup — Dify

1. Acessar `https://dify.local.daviaaze.com`
2. Criar conta admin
3. **LLM Provider:**
   - **OmniRoute:** Endpoint `http://dvision-homelab:20128/v1`, API Key da sua chave OmniRoute
   - **Ollama:** Endpoint `http://dvision-homelab:11434`
4. Criar modelo `gemma4-12b` via Ollama como modelo padrão dos agentes
5. **Importar knowledge base:** subir os arquivos de `knowledge/` como documentos RAG
6. Criar os 7 agentes da fábrica (Fiscal, Produto, Compliance, Comercial, Suporte, Financeiro, Growth)

---

## 4. Primeiro Setup — n8n

1. Acessar `https://n8n.local.daviaaze.com`
2. Criar conta admin
3. **Workflows sugeridos (criar no Agente Fiscal do Dify, deploy no n8n):**
   - **Monitor SEFAZ:** check `https://github.com/frappe/erpnext/releases` + discuss.frappe.io a cada 6h
   - **Monitor ANPD:** check `https://www.gov.br/anpd` por novas resoluções
   - **Monitor Frappe Releases:** `https://github.com/frappe/erpnext/releases` → webhook → Dify
   - **Faturamento:** gerar invoice mensal dos clientes
   - **SEO/Content:** publicar posts no blog via API

---

## 5. Primeiro Setup — Frappe Bench Dev

### 5.1 Clonar o app fiscal
```bash
# No homelab
cd /var/lib/frappe-bench/apps
git clone git@github.com:dvision/erpnext_br_compliance.git
```

### 5.2 Iniciar o bench
```bash
sudo systemctl start frappe-bench
```

### 5.3 Criar site de dev
```bash
docker exec -it frappe-bench-backend-1 bench new-site dev.erpnext.local.daviaaze.com \
  --admin-password admin \
  --mariadb-root-password frappe
```

### 5.4 Instalar app fiscal
```bash
docker exec -it frappe-bench-backend-1 bench \
  --site dev.erpnext.local.daviaaze.com \
  install-app erpnext_br_compliance
```

### 5.5 Configurar homologação SEFAZ
```bash
docker exec -it frappe-bench-backend-1 bench \
  --site dev.erpnext.local.daviaaze.com \
  console
# No console:
frappe.set_value("Configuracao Fiscal", "1", "ambiente", "2")  # 2=homologação
```

### 5.6 Helper script
O módulo cria um comando `frappe-bench` no PATH:
```bash
frappe-bench dev.erpnext.local.daviaaze.com console
frappe-bench dev.erpnext.local.daviaaze.com run-tests
```

---

## 6. PostHog

### 6.1 Teste local (homelab)
Já incluso no `nixos-rebuild`: `https://posthog.local.daviaaze.com`

### 6.2 Produção (Hetzner VPS separada)

| Item | Configuração |
|------|-------------|
| **Host** | Hetzner VPS (CX22, ~€7/mês) |
| **Stack** | Docker Compose: PostHog + ClickHouse + Redis |
| **URL** | `https://posthog.daviaaze.com` |
| **Custo** | ~R$ 45/mês (infra) + R$ 0 licença |
| **Eventos** | Product analytics do ERPNext (feature usage, funis, erros) |

**Setup rápido na VPS:**
```bash
git clone https://github.com/PostHog/posthog
cd posthog
cp .env.example .env
# Configurar CLICKHOUSE, REDIS, SECRET_KEY
docker compose up -d
```

---

## 7. Arquitetura Final

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       dvision-homelab (NixOS)                            │
│       Traefik · Tailscale · Docker · Backup · Monitoring                 │
│                                                                          │
│  https://dify.local.daviaaze.com           (Dify - 7 agentes)            │
│  https://n8n.local.daviaaze.com            (n8n - cron/monitores)        │
│  https://dev-erpnext.local.daviaaze.com    (Frappe bench DEV)            │
│  https://staging-erpnext.local.daviaaze.com (Frappe bench STAGING)       │
│  https://posthog.local.daviaaze.com        (PostHog TESTE)               │
│  https://omniroute.local.daviaaze.com      (OmniRoute - gateway LLM)     │
│  https://ollama.local.daviaaze.com         (Ollama - LLM local)          │
│  https://grafana.local.daviaaze.com        (Grafana + Prometheus)        │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                       VPS Brasil (Hetzner/qualquer)                      │
│                                                                          │
│  https://erpnext.cliente.daviaaze.com    (ERPNext PRODUÇÃO - cliente 1)  │
│  https://erpnext.cliente2.daviaaze.com   (ERPNext PRODUÇÃO - cliente 2)  │
│  ... até 10 clientes por VPS                                             │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                       Hetzner VPS (separada)                             │
│                                                                          │
│  https://posthog.daviaaze.com            (PostHog PRODUÇÃO)              │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Comandos Úteis

```bash
# Ver logs do Dify
journalctl -u dify -f

# Ver logs do n8n
journalctl -u docker-n8n -f

# Ver logs do Frappe bench
journalctl -u frappe-bench -f

# Ver logs do PostHog
journalctl -u posthog -f

# Acessar console do Frappe
frappe-bench dev.erpnext.local.daviaaze.com console

# Rebuild após mudanças
sudo nixos-rebuild switch --flake .#dvision-homelab
```