# Análise Legal: Serviço Debrid/Caching de Torrents no Brasil

**Data:** 2026-07-06
**Contexto:** Viabilidade legal de um serviço brasileiro estilo Real-Debrid (cache + streaming de torrents)
**Status:** Pesquisa — NÃO é parecer jurídico formal. Consultar advogado especialista em direito digital.

---

## Marco Regulatório Relevante

### 1. Marco Civil da Internet (Lei 12.965/2014)
- **Provedor de conexão**: ISP (Vivo, Claro, etc.)
- **Provedor de aplicação (PAI)**: qualquer entidade que forneça funcionalidades acessíveis via internet
- **Art. 19** (alterado pelo STF): exigia ordem judicial prévia para responsabilizar PAI por conteúdo de terceiro

### 2. STF — Tema 987 (26/jun/2025)
- Declarou **inconstitucionalidade parcial e progressiva** do Art. 19
- Novo regime: **notice and takedown** passa a ser regra ampla
- Dever de cuidado para falhas sistêmicas em crimes graves (terrorismo, discurso de ódio, CSAM, etc.)
- Foco: **plataformas de conteúdo gerado por usuários** (redes sociais, fóruns, etc.)
- Transito em julgado: 17/jun/2026

### 3. Decreto 12.975/2026 (vigência: 20/jul/2026)
- Regulamenta responsabilidade de PAIs
- **Art. 16-A**: representante legal no Brasil obrigatório
- **Art. 16-B**: dever de cuidado para **conteúdo CRIMINOSO** (não direitos autorais diretamente)
- **Art. 16-O**: exceções para e-mail, mensageria, comunicação em grupo restrito
- **Art. 16-P**: critérios diferenciados para pequenos provedores
- Fiscalização: **ANPD**

### 4. Lei de Direitos Autorais (Lei 9.610/1998)
- **Art. 5, VI**: "reprodução" = cópia incluindo **armazenamento permanente ou temporário por meios eletrônicos**
- **Art. 5, XII**: "distribuição" e "comunicação ao público" também protegidos
- → Caching de torrent = **reprodução** sob a lei brasileira

### 5. Código Penal — Art. 184
- **Violação de direito autoral é CRIME** no Brasil
- Pena: 2 a 4 anos (tipo básico), mais para casos qualificados

### 6. ANCINE — Lei 14.815/2024 + IN 174/2026
- ANCINE tem competência expressa para **determinar suspensão de uso não autorizado** de obras audiovisuais
- **Não precisa de ordem judicial** — ação administrativa direta
- Pode bloquear domínios, URLs, IPs (via ANATEL)
- Notifica mecanismos de busca, meios de pagamento
- Define "serviço dedicado à pirataria" e "intermediários"

### 7. ANATEL — Bloqueios (AnaBlock)
- Centenas de ordens de bloqueio ativas
- Foco: IPTV, stream-ripping, sites de filme pirata
- Execução pelas operadoras

---

## Análise: Classificação de um serviço Debrid

### O que é um debrid:
1. Cacheia torrents nos próprios servidores (= **reprodução**)
2. Streama o conteúdo para usuários (= **distribuição/comunicação ao público**)
3. NÃO hospeda conteúdo gerado por usuários
4. NÃO é intermediário passivo — ele **reproduz ativamente**

### Classificação legal:
- Seria **Provedor de Aplicação de Internet (PAI)**
- MAS não é intermediário de conteúdo de terceiro — é **provedor de conteúdo** que reproduz obras protegidas
- Marco Civil (safe harbor) **NÃO protege infrator direto**

---

## Veredito Preliminar

### Serviço de cache + streaming de torrents (estilo Real-Debrid):
- ❌ **Infringimento direto de direitos autorais** (Lei 9.610/98, Art. 5 VI)
- ❌ **Responsabilidade penal** (Art. 184 CP)
- ❌ **Ação administrativa da ANCINE** (bloqueio sem necessidade de judicial)
- ❌ **Não há safe harbor do Marco Civil** — ele é para intermediários, não infratores diretos
- ❌ **Não é área cinzenta** — é claramente ilegal

### Indexador puro (só metadata/magnet, sem hospedar arquivos):
- ⚠️ **Área mais cinzenta** — não reproduz a obra, apenas indexa
- ⚠️ Mas IN 174/2026 define "intermediários" na cadeia de pirataria
- ⚠️ ANCINE pode notificar/bloquear
- Risco menor que debrid, mas não zero

### Serviço de ferramentas (VPN, cliente torrent, automação):
- ✅ **Legal** — ferramentas de propósito geral não são ilegais
- ✅ VPN, qBittorrent, Sonarr/Radarr são softwares legítimos

---

## Modelos de Negócio Potencialmente Viáveis

1. **Serviço de VPN brasileiro** com foco em P2P (servidores BR, PIX, suporte pt-BR)
2. **Plataforma de automação** (Jellyfin + arr stack gerenciado — "streaming pessoal como serviço")
3. **Indexador** com modelo claro de motor de busca (risco intermediário, precisa de defesa técnica)
4. **Agregador de streaming legal** (cataloga serviços gratuitos/legais BR — Pluto TV, Globoplay grátis, etc.)
5. **Ferramentas para comunidade** (add-ons, metadata, organização de biblioteca)

---

## Recomendação

1. **NÃO** montar serviço de cache+streaming — exposição civil, penal e administrativa clara
2. Se quiser explorar o mercado, focar em **ferramentas/automação** ou **VPN**
3. Consultar advogado especialista em direito digital/IP antes de qualquer estruturação
4. Referências: IBDDIG (Instituto Brasileiro de Direito Digital), Patricia Peck Pinheiro, escritórios como Trench Rossi

---

## Fontes Principais
- STF Tema 987: https://noticias.stf.jus.br/postsnoticias/stf-define-parametros-para-responsabilizacao-de-plataformas-por-conteudos-de-terceiros/
- Decreto 12.975/2026: https://planalto.gov.br/ccivil_03/_ato2023-2026/2026/decreto/d12975.htm
- Lei 9.610/98: https://www.planalto.gov.br/ccivil_03/leis/l9610.htm
- ANCINE IN 174/2026: https://www.gov.br/ancine/pt-br/acesso-a-informacao/legislacao/instrucoes-normativas/instrucao-normativa-174
- Lei 14.815/2024: https://www.planalto.gov.br/ccivil_03/_Ato2023-2026/2024/Lei/L14815.htm
- Conjur análise ANCINE: https://www.conjur.com.br/2026-mai-19/o-combate-a-pirataria-audiovisual-no-brasil-e-o-novo-papel-da-ancine/
- Trench Rossi STF: https://www.trenchrossi.com/alertas-legais/stf-estabelece-que-o-artigo-19-do-marco-civil-da-internet-e-parcialmente-inconstitucional-criando-um-novo-regime-de-responsabilidade-civil/
