# Roadmap DVISION ERPNext Brasil

Roadmap faseado com base no plano de 30/07/2026. Cada fase tem prazo, escopo e justificativa.

## Fase 0 — Fundação (Semanas 1–4, Ago/2026)

**Escopo:**
- App Frappe esquelético (`erpnext_br_compliance`)
- NF-e modelo 55 saída (CRT=1 e CRT=3, venda interna simples) em **homologação**
- DANFE PDF (BrazilFiscalReport)
- Gestão de certificado A1 do cliente com alerta de vencimento

**Por quê:** Documento de maior volume e menor complexidade; prova a cadeia inteira (XML → assinatura → SEFAZ → DANFE).

## Fase 1 — Operação mínima do piloto (Semanas 5–10, Ago–Set/2026)

**Escopo:**
- NFS-e padrão nacional (fallback para provedor do município do piloto)
- Manifestação do destinatário
- Contingência SVRS
- Cancelamento / CC-e / inutilização

**Por quê:** Tudo que um piloto indústria/serviços precisa para operar de verdade.

## Fase 2 — Reforma Tributária (Out–Nov/2026)

**Escopo:**
- Campos IBS/CBS (NT 2025.002 v1.40) em produção
- Integração Calculadora de Tributos RFB (Docker)
- Atualização v1.50 (combustíveis) até 03/11/2026
- LC 224 (alíquotas PIS/COFINS recomposição) parametrizada

**Por quê:** Cliente CRT=3 só pode entrar em produção com isso; prazo legal duro.

## Fase 3 — Expansão DF-e + SPED (Dez/2026–Mar/2027)

**Escopo:**
- CT-e / MDF-e (se cliente com transporte)
- Geração de EFD ICMS/IPI (sem Bloco K inicialmente)
- EFD-Contribuições
- BP-e se varejo

**Por quê:** Abre verticais comércio/transporte; SPED é o que o contador-parceiro mais pede.

## Fase 4 — Verticalização + avançado (Abr–Jul/2027)

**Escopo:**
- Bloco K (quando cliente indústria LR/LP exigir)
- ICMS-ST / MVA por UF
- DIFAL automático
- NFP-e + Funrural (pack_agro)
- Avaliação de homologação PAA

**Por quê:** Só com 2+ clientes pagantes por vertical — regra de produto, não entusiasmo.

## Cadência regulatória permanente

Desde o início, o **Agente Fiscal** mantém:
- Toda NT nova vira issue em ≤48h
- Patch de layout em ≤5 dias úteis
- Teste de homologação antes de cada release
- Release notes para clientes em linguagem de contador