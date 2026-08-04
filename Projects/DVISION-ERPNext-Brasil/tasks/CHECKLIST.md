# Checklist — Próximas 2 semanas (Ago/2026)

Priorizado conforme seção 12 do plano. Status: `[ ]` pendente / `[x]` feito.

## Imediato (hoje–sexta)

- [ ] Verificar publicação do **ato conjunto RFB/CGIBS** (prometido fim jul/2026 — não publicado em 29/07)
- [ ] Se publicado, ajustar seção 2.1 e Fase 2 do plano conforme o texto

## Semana 1

- [ ] Contratar advogado — pacote: contrato de implantação + cláusula PI (invertendo art. 4º Lei 9.609/98) + DPA + termo A1 + NDA (**R$ 3–6 mil — único gasto que não espera cliente**)
- [ ] VPS Brasil (Hetzner ou similar) — produção (homelab = dev/staging)
- [ ] Criar repositório `erpnext_br_compliance` + CI
- [ ] Agente Fiscal v1 — 3 monitores com alerta: ENCAT/portal NF-e, ANPD, portal SVRS (tabelas cClassTrib)
- [ ] NF-e modelo 55 autorizando em homologação PR (nfelib + PyNFe + certificado A1 de teste) — "hello world" do core fiscal

## Semana 1–2

- [ ] Formalizar-se como encarregado/DPO (Res. CD/ANPD 18/2024)
- [ ] RoPA v1 + runbook de incidente de 1 página

## Semana 2

- [ ] Lista de 30 prospects (indústrias 20–80 func. — Londrina/Cambé/Arapongas/Apucarana; base CEMPRE: ~650 empresas)
- [ ] Mapear 10 contadores para o canal (comissão 10–15%)
- [ ] Agendar 5 conversas de discovery (meta: piloto 1 fechado até meados de setembro)
- [ ] Publicar 1º conteúdo: "Reforma Tributária: sua NF-e está pronta para 03/08/2026?"

## Mês 2 (Set/2026) — Piloto 1

- [ ] Fechar piloto 1 (ideal: metal-mecânica ou moveleira, CRT=3) — preço case R$ 8–12 mil + R$ 790–1.190/mês
- [ ] **Discovery — validar dor de conciliação bancária:** "Como vocês conciliam o extrato bancário hoje? Quantas horas/mês isso leva? Já tentaram automatizar?" (se dor alta → Open Finance é add-on vendável; se baixa → adiar Pluggy)
- [ ] Fase 1 fiscal: NFS-e do município, manifestação do destinatário, contingência SVRS
- [ ] RoPA + DPA assinado com o piloto; simulado de incidente (2h)

## Mês 3 (Out/2026) — Reforma no código

- [ ] Fase 2: campos IBS/CBS (NT 2025.002 v1.40) + Calculadora RFB
- [ ] v1.50 (combustíveis) antes de 03/11/2026; alíquotas LC 224 parametrizadas
- [ ] Piloto 1 em produção; começar case público
- [ ] Piloto 2 fechado (vertical diferente)

## Meses 4–6 (Nov/2026–Jan/2027) — Repetibilidade

- [ ] Template vertical v1; implantação-alvo ≤60h
- [ ] Agente de Suporte com base de conhecimento; deflexão medida desde o 1º ticket
- [ ] 3–4 clientes pagantes
- [ ] **Gate 1 (fim jan/2027):** ≥3 clientes ativos, ≥1 case público, implantação ≤80h, 0 incidentes graves → senão, corrigir antes de escalar

## Meses 7–9 (Fev–Abr/2027) — Canal e SPED

- [ ] Fase 3: EFD ICMS/IPI (geração) + EFD-Contribuições; CT-e se houver demanda
- [ ] Canal contador: 3–5 contadores com material + comissão; meta 30% dos leads
- [ ] 5–7 clientes
- [ ] **Gate 2 (fim abr/2027):** MRR ≥R$ 8 mil, churn <3%, suporte <2h/cliente/mês

## Meses 10–12 (Mai–Jul/2027) — Teto do modelo 1-pessoa

- [ ] 8–10 clientes; template vertical v2; horas/implantação ≤50h
- [ ] Decisão estruturada: contratar 1º colaborador (gatilhos) ou segurar crescimento
- [ ] Avaliações ano 2: ISO 27001 gap assessment formal; PAA; pack_agro se 2+ clientes agro
- [ ] **Gate 3 (jul/2027):** 10 clientes, NPS ≥8, MRR ≥R$ 13 mil, LTV:CAC medido ≥5× → plano ano 2