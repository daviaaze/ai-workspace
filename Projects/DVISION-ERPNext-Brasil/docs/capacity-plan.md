# Plano de Capacidade — 1 founder até 10 clientes

## Matemática das horas (orçamento ~2.000h/ano)

| Demanda | Premissa | Carga anual (10 clientes) |
|---------|----------|---------------------------|
| Implantações novas | 60–80h (ano 1) → 40h (templates); 6–8 no ano 1 | 400–640h |
| Suporte recorrente | <2h/cliente/mês com deflexão L1 ≥60% | 240h |
| Core fiscal (build) | Fases 0–2 nos meses 1–5 | 400–500h |
| Manutenção fiscal contínua | Agente Fiscal executa; você revisa ~4h/semana | ~200h |
| Vendas/relacionamento | 2–4 reuniões/semana | ~300h |
| Gestão/overflow | buffer 15% | ~250h |
| **Total** | | **~1.800–2.100h — fecha, sem folga** |

**Conclusão:** 10 clientes é o teto real do modelo 1-pessoa. Depende de 2 alavancas:
1. Templates verticais derrubarem implantação de 80h → 40h
2. Deflexão de suporte ≥60%

Se qualquer uma falhar, o teto cai para 6–7 clientes.

## KPIs semanais (Agente Financeiro monta dashboard; 30 min/sexta)

1. Horas por implantação (alvo: ≤60h caindo para 40h)
2. Horas de suporte por cliente/mês (alvo: <2h)
3. Deflexão L1 (alvo: ≥60%)
4. Rejeições fiscais em produção (alvo: 0 por layout desatualizado)
5. MRR, churn mensal (gate: <3%), NPS (≥8)
6. Pipeline: leads qualificados/semana; discovery→proposta <24h

## Gatilhos de contratação

| Gatilho | Contratar | Perfil | Quando |
|---------|-----------|--------|--------|
| Suporte >25% do tempo por 4 semanas seguidas | 1º | Suporte N1/implantação júnior (remoto, PJ) | 7º–9º cliente |
| Implantação média >90h após 3 clientes na mesma vertical | **Revisar template antes de contratar** | — | — |
| Churn >3%/mês ou NPS <8 | Parar vendas, corrigir produto | — | — |
| Fila >2 clientes pagantes esperando >30 dias | 1º ou 2º | Dev Frappe júnior | 9º–10º cliente |
| 10 clientes ativos + 3 na fila | 2º | Customer success/implantação | Transição ano 2 |

**Gate para virar SaaS self-service:** ≥10 clientes, churn <3%/mês, suporte <2h/cliente/mês, NPS ≥8 — só então investir em onboarding sem humano.

## Custos reais ano 1 (projeção)

| Item | Valor | Periodicidade |
|------|-------|--------------|
| Frappe Cloud (Frankfurt) | US$ 40–150/mês | Mensal |
| Ferramentas IA/LLM | R$ 200–800/mês | Mensal |
| Certificado e-CNPJ A1 | R$ 100–400/ano | Anual |
| Advogado (pacote contratos) | R$ 3.000–6.000 | Uma vez |
| Contador DVISION | R$ 300–800/mês | Mensal |
| Seguro RC/E&O | ~R$ 620–920/mês | Mensal (a partir 3º–4º cliente) |
| **Total ano 1** | **~R$ 25–45 mil** | |