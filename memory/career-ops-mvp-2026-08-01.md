# CareerOps MVP v1 — memoria de retomada (01/ago/2026)

## O que e
Produto pessoal para pipeline de candidaturas do Davi (contratacao direta, USD 6-8k/mes).
Repositorio: `career-ops/` (pasta raiz do workspace).

## Estado atual
- MVP v1 funcional: tracker SQLite + CLI (setup/score/brief/pack/approve/applied/tracker/stats/review/scan/inbox)
- Discovery: scraper direto (httpx+BS4+JSON-LD) + RSS feeds + parser IMAP (configurar credenciais)
- JobSpy descontinuado (numpy 1.26.3 incompativel com stores Nix 3.11/3.14)
- Nao ha /mnt/agents/work — dados persistidos em career-ops/output/
- CV docx pipeline (Program.cs) nao esta neste repo — esta em docs/carrer/Kimi_Agent_cv/

## Pilotos
- Engine Senior Backend (Lodging): ciclo completo rodado em 01/ago/2026
  - score 10/10 -> pacote gerado -> aprovada -> submetida
  - caminho: career-ops/output/candidaturas/Engine-Senior-Software-Engineer-Backend-Lodging-2026-08-01/
- Scan real capturou vagas de TravelPerk, Hopper, Engine, Navan

## Pendencias (Davi)
- [ ] Confirmar se Step Functions e usado na Lux
- [ ] Stack do Contrate Quem Luta (MTST)
- [ ] TTV do Agent Platform ja passou de USD 3M?
- [ ] Origem da experiencia com Kafka e NestJS
- [ ] Nivel de espanhol

## Pendencias (MVP)
- [ ] Notificacoes por e-mail (SMTP) — configurar env CAREER_OPS_SMTP_PASSWORD
- [ ] Integrar gerador CV docx (atual: copia cv-mestre.md + placeholder)
- [ ] Filtro de "apenas backend/travel tech" no scraper
- [ ] Dedup por empresa+titulo (URL nao eh suficiente)
- [ ] Dashboard HTML estatico (v1.5)
- [ ] Ghost jobs detector
- [ ] Cron semanal/diario (documentado, nao registrado)

## Arquivos transferidos (base de conhecimento)
docs/carrer/Kimi_Agent_cv/agente-candidaturas/
  README.md, PERFIL.md, HABILIDADES.md, RESPOSTAS-TRIAGEM.md,
  REGRAS-DE-APLICACAO.md, PLANO-DE-CARREIRA.md, TRACKER.csv, PROMPT-DE-RETOMADA.md
docs/carrer/Kimi_Agent_cv/
  cv-mestre-davi-azevedo.md, pesquisa-mercado-metricas-portfolio.md,
  posicionamento-storytelling-contractor-europa.md,
  CV_Davi_Azevedo_PlanitEasy_v2.{docx,md}
docs/carrer/Kimi_Agent_cv/produto-carreira/PRD.md

## Stack
- Python 3.14 (venv do projeto), click, jinja2, pyyaml, httpx, beautifulsoup4, lxml, markdown2
- SQLite (tracker.db) + filesystem (candidaturas/)
- Comando: `career` (entry point CLI)

## Como retomar
1. source .venv/bin/activate
2. career setup      # verifica paths
3. career scan       # descobre vagas
4. career score --all
5. career pack <id>
6. career approve <id>   # acao humana
7. career applied <id>
8. career review

## Cron (registrado 01/ago/2026)
- systemd user timer em ~/.config/systemd/user/
- career-ops-weekly.timer: seg 08:00 (scan + score --all + review)
- career-ops-daily.timer: seg-sex 08:00 (review + inbox)
- systemctl --user daemon-reload && enable --now
- Verificar: systemctl --user list-timers career-ops*
