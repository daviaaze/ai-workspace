# Upgrade, Patches e Segurança — ERPNext

> **Propósito:** guia de upgrade path, patches de segurança e procedimentos de migração entre versões.

---

## 1. Upgrade Path v15 → v16

**Status:** 30/07/2026 — v15 e v16 coexistindo; v16 é a versão estável recomendada para novos projetos.

### Passos (baseado em discuss.frappe.io/t/159062 e tcbinfotech.com)

```bash
# 1. Instalar Node 24 (se ainda não tiver)
# 2. Instalar Python 3.14.2 (via pyenv)
# 3. Rebuild bench internal env com Python 3.14
# 4. Backup completo (banco + arquivos)
bench --site site.local backup

# 5. Mudar branch
bench switch-to-branch version-16 erpnext
bench switch-to-branch version-16 frappe

# 6. Atualizar
bench update --patch
bench build
bench migrate

# 7. Validar
bench --site site.local console
# Verificar se custom apps compilam
bench --site site.local run-tests

# 8. Se falhar: restaurar backup
bench --site site.local restore backup.sql.gz
```

### Cuidados Conhecidos
- **Custom apps podem quebrar** — testar em staging antes
- **Database migrations são irreversíveis** — backup obrigatório
- **Query Builder v16 tem breaking changes** em `get_list` e `get_all` (usar `frappe.qb`)
- **Customer List View vazia** após upgrade (issue #52095)
- **Frappe precisa ser atualizado junto com ERPNext**

## 2. Versões Atuais (Julho/2026)

| Produto | Versão | Data |
|---------|--------|------|
| ERPNext | v16.30.0 | 29/07/2026 |
| ERPNexr | v15.118.3 | ~29/07/2026 |
| Frappe | v16 (atualizar junto) | Atual |
| Frappe Framework | v16 | Atual |

## 3. Segurança

### Práticas Recomendadas
- **Frappe Cloud:** atualizações automáticas + patches de segurança gerenciados
- **Self-host:** `bench update` semanal + monitorar GitHub Security Advisories
- **Frappe Cloud tem RPO 24h** (backup diário), RTO <15min
- **Bench-exporter** para Prometheus (métricas de segurança: tentativas de login, falhas)

### Permissões (v16)
- Dashboard de Customer/Supplier só mostra empresas que o usuário pode acessar (#57440)
- `get_item_details` com verificação de permissão (#57551)
- Terms and Conditions com verificação de permissão (#57106)
- Frappe Cloud: OAuth2 + MCP com OAuth2

## 4. Deprecation Alerts (v16+)

O ERPNext v16 introduziu alertas de depreciação com data de remoção prevista. Quando uma feature está programada para ser removida, o sistema mostra warning ou error dependendo da proximidade da data.

**Monitorar:** releases notes de ERPNext e Frappe para features marcadas como deprecated.

## 5. Migração de Database

- `bench migrate` executa patches na ordem definida em `patches.txt`
- Patches de app customizado: `patches.txt` no diretório do app
- Formato: `app_name.patches.module.function_name`
- `bench --site site.local migrate` executa todos os patches pendentes