# Base de Conhecimento — Agente de Candidaturas (Davi Azevedo)

Esta pasta contém tudo que um agente (IA ou humano) precisa para **descobrir, avaliar, preparar e submeter candidaturas** em nome do Davi, de forma consistente e segura.

## Arquivos

| Arquivo | Função | Quando o agente usa |
|---|---|---|
| `PERFIL.md` | Identidade, contatos, disponibilidade, restrições | Preenchimento de formulários, triagem geográfica |
| `HABILIDADES.md` | Matriz de skills com anos de experiência e evidências | Fit score, CV tailoring, respostas técnicas |
| `RESPOSTAS-TRIAGEM.md` | Respostas prontas para perguntas de screening | Formulários, e-mails de recrutador, calls |
| `REGRAS-DE-APLICACAO.md` | Critérios de fit, red flags, limites e workflow de aprovação | Decisão de aplicar ou descartar; antes de qualquer envio |
| `PLANO-DE-CARREIRA.md` | Lacunas de skill, certificações (ROI), materiais de estudo, roadmap 12 meses | Revisão trimestral; ao concluir qualquer cert/skill |
| `TRACKER.csv` | Registro de candidaturas | Atualizar a cada ação |

## Arquivos externos (repositório existente)

- `/mnt/agents/output/cv-mestre-davi-azevedo.md` — banco completo de bullets, métricas validadas (com fonte+data), histórias STAR, regras de adaptação por tipo de vaga
- `/mnt/agents/output/Davi_Azevedo_CV_PlanitEasy.docx` — CV atual (variante travel tech)
- `/mnt/agents/output/posicionamento-storytelling-contractor-europa.md` — posicionamento, headline, template de intro letter
- `/mnt/agents/output/pesquisa-mercado-metricas-portfolio.md` — dados de mercado, rates, plano de portfólio GitHub

## Workflow padrão (semi-autônomo)

1. **Descobrir** vagas nas fontes listadas em `REGRAS-DE-APLICACAO.md`
2. **Pontuar** fit 1–10 contra `HABILIDADES.md` + critérios de `REGRAS-DE-APLICACAO.md`
3. **Preparar** pacote (CV adaptado + cover letter + respostas de triagem) para vagas ≥ 7
4. **APROVAÇÃO HUMANA** — Davi revisa e aprova cada pacote (obrigatório)
5. **Submeter** e registrar no `TRACKER.csv`
6. **Follow-up** conforme cadência definida nas regras

> Nunca submeter sem aprovação. Nunca inventar métricas. Nunca violar as regras de confidencialidade (NDA) definidas em `REGRAS-DE-APLICACAO.md`.

Última atualização: 02/ago/2026
