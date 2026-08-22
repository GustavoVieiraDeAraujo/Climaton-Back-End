# ClimatonBrasil API

API somente-leitura em FastAPI sobre o banco unificado e auditado do **ClimatonBrasil 2026** (hackathon do TCU), cruzando Painel ClimaBrasil, AdaptaBrasil, Painel de Gastos Climáticos, Fundo Clima, SICONFI e ClimateScanner Global num único SQLite (`dataset/clima_brasil_climate_scanner.sqlite`). Todo endpoint devolve um campo `fonte` apontando pra tabela/view/query de origem - nunca um número sem proveniência. Inclui também o back-end do assistente de IA do site, que responde perguntas em linguagem natural usando os mesmos dados.

> **Front-End:** [Climaton-Front-End](https://github.com/GustavoVieiraDeAraujo/Climaton-Front-End)

---

## Sumario

- [Colaboradores](#colaboradores)
- [Tecnologias](#tecnologias)
- [Funcionalidades](#funcionalidades)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Requisitos](#requisitos)
- [Configuracao](#configuracao)
- [Como Executar](#como-executar)
- [Arquitetura](#arquitetura)
- [Modelo de Dados](#modelo-de-dados)
- [Endpoints da API](#endpoints-da-api)

---

## Colaboradores

| Nome |
| --- |
| Gustavo Vieira de Araújo |
| Iverson Cintra de Andrade Ferreira |
| Thayna Gonçalves Dutra |
| Dryeli da Silva Bandeira |

---

## Tecnologias

| Tecnologia | Uso |
| --- | --- |
| Python | Linguagem do back-end |
| FastAPI | Framework HTTP, definição de rotas, validação de corpo de requisição via Pydantic |
| Uvicorn | Servidor ASGI usado em desenvolvimento (`--reload`) |
| SQLite | Banco somente-leitura, acessado sem ORM (`sqlite3` da stdlib, `app/db.py`) |
| python-dotenv | Carrega `.env` (configuração da CLI do Claude Code) |
| Claude Code CLI (`claude -p`) | Motor do assistente de IA - roda em cima da assinatura já logada na máquina, não é uma API paga/limitada por token (ver [Como funciona o assistente de IA](#endpoints-da-api)) |

---

## Funcionalidades

| Funcionalidade | Implementacao |
| --- | --- |
| Territórios e prioridade climática | `app/routers/territorios.py`, view `climate_gap_prioridade` (risco físico x capacidade institucional, 51 territórios) |
| Capitais com coordenadas reais | `app/routers/capitais.py`, coordenadas fixas (`CAPITAL_COORDS`, sede dos municípios via IBGE) cruzadas com risco/prioridade quando a capital está na amostra |
| Cobertura da amostra | `GET /cobertura`, explica por que só 25 das 27 capitais têm avaliação institucional (Goiânia e Aracaju ficam de fora) |
| Gastos climáticos | `app/routers/gastos.py` - série anual, resumo com alerta de ruído, ranking por órgão, e o achado central do site (recuperação de desastres vs. prevenção real) |
| Filtro de ruído documentado | Categoria bruta "Redução do risco de desastres" tem 70,6% de crédito/seguro agrícola e programa nuclear mal classificados - excluído via filtro de palavra-chave na ação, com a auditoria completa registrada na tabela `auditoria_ruido` |
| Justiça climática | `GET /justica-climatica`, agrupa as 24 capitais avaliadas por estágio (avançado/intermediário/inicial/sem progresso), com aviso explícito contra somar estágios parciais como se fossem conclusão |
| Comparação Brasil x Mundo | `GET /comparacao-brasil-mundo`, cruza a nota do Brasil-país no ClimateScanner Global com a média real dos 51 territórios subnacionais |
| Dados por eixo (Governança / Políticas Públicas / Financiamento) | `app/routers/eixo.py` - componentes, territórios, distribuição por estágio e quebra por macrorregião IBGE |
| Regiões (macrorregiões IBGE) | `GET /eixo/{slug}/regioes`, mapeamento fixo território→UF→região (`app/constants.py`) aplicado sobre a média de cada eixo |
| Créditos das fontes | `GET /fontes`, expõe as 6 bases originais do dataset unificado com ressalva de qualidade (atualidade/confiabilidade/completude) de cada uma |
| Assistente de IA (chat) | `POST /chat` - atalho local pra pedidos de navegação óbvios ("me leva pro mapa"), e pra tudo o mais chama `claude -p` com todo o contexto de dados relevante pré-buscado do SQLite e injetado no prompt |
| CORS liberado para o front-end local | `main.py`, origens `localhost:3000`/`3001` e `127.0.0.1:3000` |

---

## Estrutura do Projeto

| Diretorio / Arquivo | Descricao |
| --- | --- |
| `main.py` | Ponto de entrada FastAPI: monta CORS e inclui todos os routers |
| `app/db.py` | Único ponto de acesso ao SQLite - função `query(sql, params)`, sem ORM |
| `app/constants.py` | Dados de referência que não vêm do banco: coordenadas e UF das 27 capitais, mapeamento estado→UF e UF→macrorregião IBGE, slugs dos 3 eixos |
| `app/llm_client.py` | Cliente do assistente de IA - monta o prompt (dados + histórico + pergunta) e chama `claude -p` via `subprocess`; docstring do módulo documenta a investigação completa de provedores de LLM tentados antes desta escolha |
| `app/tools.py` | Funções de dado reaproveitadas pelo `llm_client.py` pra pré-buscar o contexto do chat - cada uma espelha a query do router correspondente, nunca duplica lógica de SQL |
| `app/routers/territorios.py` | `GET /territorios`, `GET /territorios/criticos` |
| `app/routers/capitais.py` | `GET /capitais`, `GET /cobertura` |
| `app/routers/gastos.py` | `GET /gastos/serie-anual`, `/resumo`, `/por-orgao`, `/desastres-prevencao-vs-recuperacao` |
| `app/routers/insights.py` | `GET /justica-climatica`, `/comparacao-brasil-mundo`, `/resumo/{secao}` |
| `app/routers/eixo.py` | `GET /eixo/{slug}/componentes`, `/territorios`, `/regioes`, `/distribuicao` |
| `app/routers/fontes.py` | `GET /fontes` |
| `app/routers/chat.py` | `POST /chat` |
| `dataset/clima_brasil_climate_scanner.sqlite` | Cópia read-only do banco unificado usada pela API |

---

## Requisitos

| Dependencia | Versao | Instalacao |
| --- | --- | --- |
| Python | 3.12 (testado) | [python.org](https://www.python.org/) |
| Dependências do projeto | conforme `requirements.txt` (`fastapi`, `uvicorn[standard]`, `python-dotenv`) | `pip install -r requirements.txt` |
| Claude Code CLI | logada com uma assinatura ativa | [claude.com/claude-code](https://claude.com/claude-code) - necessário só pra `POST /chat` responder; o resto da API funciona sem ela |

```bash
pip install -r requirements.txt
```

---

## Configuracao

Não há variáveis obrigatórias - o `.env` só existe pra configurar a CLI do Claude Code, e todas têm um valor padrão pensado pra rodar localmente.

| Variável | Padrão | Uso |
| --- | --- | --- |
| `CLAUDE_CLI_COMMAND` | `claude` | Comando/caminho do binário da CLI; só precisa mudar se `claude` não estiver no `PATH` do processo do back-end |
| `CLAUDE_CLI_TIMEOUT` | `60` | Timeout em segundos pra cada chamada de `claude -p` no `POST /chat` |

```bash
# .env (já coberto pelo .gitignore)
CLAUDE_CLI_COMMAND=claude
CLAUDE_CLI_TIMEOUT=60
```

---

## Como Executar

```bash
# instala as dependências
pip install -r requirements.txt

# sobe a API com reload automático em http://localhost:8000
uvicorn main:app --reload --port 8000
```

A documentação interativa (Swagger) fica disponível em `http://localhost:8000/docs`, e `GET /health` confirma se o banco foi encontrado.

---

## Arquitetura

| Camada | Responsabilidade |
| --- | --- |
| `main.py` | Monta a aplicação FastAPI, CORS e os routers |
| Routers (`app/routers/*.py`) | Um módulo por domínio; cada função monta a query SQL, roda via `app/db.py` e devolve `dados` + `fonte` |
| `app/db.py` | Camada fina sobre `sqlite3` - abre/fecha a conexão a cada chamada, sem pool nem ORM |
| `app/constants.py` | Geografia e mapeamentos fixos que não existem no banco tabular (coordenadas, UF, macrorregião) |
| Assistente de IA (`app/routers/chat.py` → `app/llm_client.py` → `app/tools.py`) | Sem tool-calling de verdade: `tools.py` pré-busca todos os dados relevantes do SQLite, `llm_client.py` serializa isso como contexto JSON no prompt e chama `claude -p`, que só redige a resposta final em linguagem natural |
| Banco (`dataset/clima_brasil_climate_scanner.sqlite`) | Fonte única de verdade, somente leitura, compartilhada por toda a API |

---

## Modelo de Dados

Principais tabelas/views do banco unificado usadas pela API:

| Tabela / View | Conteúdo |
| --- | --- |
| `entidades` | Os 51 territórios subnacionais (26 estados, 24 capitais-município, Distrito Federal) + países do ClimateScanner Global |
| `componentes` | As dimensões avaliadas por eixo (ex.: `BR_G1`-`BR_G7` Governança, `BR_P1`-`BR_P5` Políticas Públicas, `BR_F1`-`BR_F3` Financiamento) |
| `avaliacoes` | Uma linha por território x componente x item, com `score_padronizado` (0 / 0,333 / 0,666 / 1,0) e a evidência textual do avaliador |
| `climate_gap_prioridade` | View que cruza risco físico real (AdaptaBrasil) com capacidade institucional declarada (Painel ClimaBrasil) e calcula a prioridade (Crítico/Alto/Médio/Baixo) |
| `adaptabrasil_risco` | Risco físico climático por município, direto do AdaptaBrasil (MCTI) |
| `gastos_climaticos` | Despesa federal 2010-2023, linha a linha (ação x órgão x ano), classificada por propósito e categoria em 3 dimensões paralelas (Mudança Climática, Desastres, Biodiversidade) |
| `gasto_ambiental_serie_anual` / `gasto_ambiental_por_orgao` | Agregações de `gastos_climaticos` por ano e por órgão orçamentário |
| `auditoria_ruido` | Registro auditável dos problemas de classificação encontrados em `gastos_climaticos` (ex.: crédito agrícola classificado como prevenção de desastres) e o tratamento aplicado |
| `comparacao_brasil_vs_mundo` | Média subnacional (51 territórios) x nota do Brasil-país x média mundial (101 países), por componente |
| `fontes` / `qualidade_fontes` | Proveniência de cada uma das 6 bases originais e ressalva de qualidade (atualidade/confiabilidade/completude) de cada uma |
| `fundo_clima_projetos` | Projetos financiados com recursos não reembolsáveis do Fundo Nacional sobre Mudança do Clima, 2011-2025 |
| `siconfi_rreo` | Execução orçamentária geral (RREO) dos 26 estados + DF, exercício 2024, sem classificação climática própria |

---

## Endpoints da API

| Método | Rota | Descrição |
| --- | --- | --- |
| `GET` | `/health` | Confirma se o processo subiu e se o arquivo do banco foi encontrado |
| `GET` | `/territorios` | Os 51 territórios com risco, capacidade e prioridade |
| `GET` | `/territorios/criticos` | Só os territórios em prioridade Crítica |
| `GET` | `/capitais` | As 27 capitais com coordenadas reais, risco e prioridade (quando avaliada) |
| `GET` | `/cobertura` | Por que só 25 das 27 capitais têm avaliação institucional completa |
| `GET` | `/gastos/serie-anual` | Gasto climático "positivo" por ano, 2010-2023 |
| `GET` | `/gastos/resumo` | Total positivo, quanto é propósito Principal vs. Secundário, com alerta de ruído |
| `GET` | `/gastos/por-orgao?limit=8` | Ranking de órgãos por gasto, nas 3 dimensões paralelas (clima/desastres/biodiversidade) |
| `GET` | `/gastos/desastres-prevencao-vs-recuperacao` | O achado central do site: quanto foi gasto em resposta/recuperação de desastres vs. prevenção real (com o filtro de ruído aplicado), total e série anual |
| `GET` | `/justica-climatica` | As 24 capitais avaliadas, agrupadas por estágio de identificação de grupos vulneráveis |
| `GET` | `/comparacao-brasil-mundo` | Brasil-país x média subnacional x média mundial, por componente |
| `GET` | `/resumo/{secao}` | Resumo textual gerado por template determinístico para uma seção do site |
| `GET` | `/eixo/{slug}/componentes` | Média de cada componente do eixo (`slug` = `governanca`, `politicas-publicas` ou `financiamento`) |
| `GET` | `/eixo/{slug}/territorios` | Ranking dos 51 territórios pela média do eixo |
| `GET` | `/eixo/{slug}/regioes` | Média do eixo agrupada pelas 5 macrorregiões do IBGE |
| `GET` | `/eixo/{slug}/distribuicao` | Contagem de avaliações por estágio, por componente do eixo |
| `GET` | `/fontes` | As 6 bases originais do dataset, com crédito e ressalva de qualidade |
| `POST` | `/chat` | Assistente de IA - recebe `{ "message": "...", "history": [...] }`, devolve `{ "reply", "actions", "fontes", "resolvido_localmente" }` |

Exemplo de chamada ao assistente de IA:

```json
POST /chat
{
  "message": "quais territórios estão em prioridade crítica?",
  "history": []
}
```

```json
→ 200 OK
{
  "reply": "Macapá, Fortaleza, São Luís, Pernambuco e Maceió estão em prioridade Crítica agora...",
  "actions": [],
  "fontes": [],
  "resolvido_localmente": false
}
```

Pedidos de navegação simples ("me leva pro mapa") são resolvidos localmente, sem chamar a CLI:

```json
→ 200 OK
{
  "reply": "Beleza, indo pra seção de mapa.",
  "actions": [{ "type": "scroll_to_section", "target": "mapa" }],
  "fontes": [],
  "resolvido_localmente": true
}
```

---

> Documentacao gerada com auxilio de IA. Ferramenta de IA usada no desenvolvimento deste projeto: [Claude Code](https://claude.com/claude-code) (Anthropic). O assistente de IA do próprio site (`POST /chat`) também usa a Claude Code CLI em runtime, ver [Tecnologias](#tecnologias).
