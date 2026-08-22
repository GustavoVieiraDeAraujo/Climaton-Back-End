"""Client fino do LLM. Único lugar que fala com o modelo.

Histórico da escolha de provedor (documentado porque já mudamos várias vezes nesta sessão):
  1) Groq (gpt-oss-120b) - usuário não conseguiu criar conta.
  2) Gemini (gemini-2.5-flash-lite) - conta criada, mas BLOQUEADO. Investigação completa
     (2ª rodada, com mais tempo): o Google está no meio de uma migração de formato de
     chave (Standard "AIzaSy..." -> Auth "AQ...") com rollout quebrado em ago/2026.
     Testado com TRÊS abordagens diferentes, todas com o mesmo erro 401
     ACCESS_TOKEN_TYPE_UNSUPPORTED / UNAUTHENTICATED:
       a) curl cru no endpoint nativo (v1beta) com `?key=` e com header `x-goog-api-key`;
       b) curl cru no endpoint compatível com OpenAI
          (https://generativelanguage.googleapis.com/v1beta/openai/);
       c) SDK oficial `google-genai` (pip install google-genai), `client.models.generate_content`,
          testado com `api_version` v1beta e v1 - mesmo erro exato vindo do SDK oficial,
          confirmando que NÃO é um problema do nosso código/shim OpenAI, é o backend do
          Google rejeitando esse formato de chave em qualquer via de acesso.
     Não dava pra confiar nisso a horas da apresentação. Gerar uma chave nova em formato
     antigo via Google Cloud Console (em vez do fluxo rápido do AI Studio) ou usar Vertex AI
     com service account exigiria login interativo no navegador (fora do alcance do agente
     que fez essa investigação) - documentado como pendência manual, não testado.
  3) OpenRouter (nvidia/nemotron-3-super-120b-a12b:free) - funcionou, mas free tier
     apertado (20 RPM / 50 RPD) - risco real de estourar rate limit numa demo ao vivo
     com vários jurados testando ao mesmo tempo.
  4) Cerebras (openai/gpt-oss-120b) - alternativa de cota maior, cogitada mas nunca
     testada de ponta a ponta (exigia criar conta nova).
  5) claude-cli (ESCOLHA ATUAL) - usa a assinatura do Claude Code (CLI `claude -p`) já
     logada na máquina do usuário, em vez de qualquer API paga/limitada por token. Sem
     rate limit de free tier, sem chave de API pra gerenciar. Trade-off assumido: o
     `claude -p` não fala tool-calling no formato OpenAI, então não há mais um loop de
     tool-calling de verdade - os dados de app/tools.py são todos pré-buscados no SQLite
     local e injetados como contexto no prompt (ver `_contexto_dados_cli`), e o CLI só
     redige a resposta final. SDK da OpenAI e os outros provedores foram removidos: essa
     é a única via agora. Se o binário `claude` não estiver no PATH do processo do
     backend, defina CLAUDE_CLI_COMMAND no .env com o caminho completo.
"""

import json
import os
import subprocess

from dotenv import load_dotenv

load_dotenv()

CLAUDE_CLI_COMMAND = os.environ.get("CLAUDE_CLI_COMMAND", "claude")
CLAUDE_CLI_TIMEOUT = int(os.environ.get("CLAUDE_CLI_TIMEOUT", "60"))


# Espelho de RELATOS em components/sections/relatos-section.tsx (Climaton-Front-End) -
# seção 06 do site, protótipo declarado: "DADOS SIMULADOS - NÃO SÃO RELATOS REAIS". Não
# vem do SQLite (não é dado auditado) - mantido em sincronia manual com o front-end, já
# que só existe pra essa demonstração. Se a lista de lá mudar, atualize aqui também.
_RELATOS_COMUNIDADE = [
    {"cidade": "Macapá", "uf": "AP", "bairro": "Zona Norte", "tipo": "Rachadura em encosta", "ha": "há 2 dias", "texto": "Rachadura grande se abrindo numa encosta perto de casas - moradores dizem que está crescendo a cada chuva."},
    {"cidade": "Macapá", "uf": "AP", "bairro": "Beirol", "tipo": "Erosão avançando", "ha": "há 6 dias", "texto": "Barranco do rio perdendo terreno rápido, árvores da margem já estão caindo."},
    {"cidade": "Fortaleza", "uf": "CE", "bairro": "Praia de Iracema", "tipo": "Avanço do mar", "ha": "há 4 dias", "texto": "Água chegando mais perto das casas a cada maré alta - ninguém veio medir até agora."},
    {"cidade": "Fortaleza", "uf": "CE", "bairro": "Barra do Ceará", "tipo": "Drenagem entupida", "ha": "há 1 dia", "texto": "Bueiro cheio de lixo há semanas - primeira chuva forte alaga a rua de novo."},
    {"cidade": "São Luís", "uf": "MA", "bairro": "Vila Palmeira", "tipo": "Encosta instável", "ha": "há 3 dias", "texto": "Terra escorregando aos poucos atrás de casa, ninguém veio olhar ainda."},
    {"cidade": "São Luís", "uf": "MA", "bairro": "Anjo da Guarda", "tipo": "Maré subindo", "ha": "há 5 dias", "texto": "Água chegando mais alto que no ano passado, na mesma maré de sempre."},
    {"cidade": "Maceió", "uf": "AL", "bairro": "Jacintinho", "tipo": "Rio acima do normal", "ha": "há 2 dias", "texto": "Rio mais cheio que o normal pra essa época do ano, sem obra de contenção à vista."},
    {"cidade": "Maceió", "uf": "AL", "bairro": "Bebedouro", "tipo": "Rachadura em muro", "ha": "há 7 dias", "texto": "Muro de contenção perto da escola com rachadura visível - área ainda não foi isolada."},
    {"cidade": "Rio de Janeiro", "uf": "RJ", "bairro": "Rocinha", "tipo": "Trinca em barreira", "ha": "há 3 dias", "texto": "Trinca crescendo na barreira de contenção - moradores já avisaram e esperam resposta."},
    {"cidade": "Porto Alegre", "uf": "RS", "bairro": "Sarandi", "tipo": "Nível do rio subindo", "ha": "há 4 dias", "texto": "Guaíba subindo de novo, na mesma velocidade do início de 2024."},
]


def _contexto_dados_cli() -> str:
    """Pré-busca TODOS os dados que as tools de app/tools.py exporiam - substitui o
    tool-calling de verdade (que o `claude -p` não fala no formato OpenAI) por um
    contexto estático. Consultas locais no SQLite, então rodar todas de uma vez a
    cada mensagem é barato (ver app/tools.py pros mesmos dados/fontes usados pelas
    outras rotas)."""
    from app.constants import EIXO_SLUGS
    from app.tools import (
        get_cobertura, get_comparacao_brasil_mundo, get_eixo_dados, get_gastos_resumo,
        get_gastos_serie_anual, get_justica_climatica, get_territorios_criticos,
    )

    dados = {
        "territorios_criticos": get_territorios_criticos(),
        "gastos_resumo": get_gastos_resumo(),
        "gastos_serie_anual": get_gastos_serie_anual(),
        "justica_climatica": get_justica_climatica(),
        "comparacao_brasil_mundo": get_comparacao_brasil_mundo(),
        "cobertura": get_cobertura(),
        "eixos": {slug: get_eixo_dados(slug) for slug in EIXO_SLUGS},
        "relatos_da_comunidade": {
            "aviso": "DADOS SIMULADOS - NÃO SÃO RELATOS REAIS. Protótipo de uma funcionalidade "
                     "futura (seção 06 do site), escrito só pra esta demonstração - não vem de "
                     "nenhum canal de denúncia existente. SEMPRE avise que é simulado se for "
                     "citar algum desses relatos, nunca apresente como dado auditado real.",
            "dados": _RELATOS_COMUNIDADE,
            "fonte": "components/sections/relatos-section.tsx - protótipo, dado simulado.",
        },
    }
    return json.dumps(dados, ensure_ascii=False)


def chat_completion(messages: list[dict]) -> str:
    """Monta o prompt (contexto de dados + histórico + pergunta) e chama `claude -p`.
    Devolve o texto final já pronto pra mostrar ao usuário."""
    partes = [f"[DADOS DISPONÍVEIS - JSON, única fonte de números permitida]\n{_contexto_dados_cli()}"]
    for m in messages:
        if m["role"] == "system":
            partes.append(f"[INSTRUÇÕES]\n{m['content']}")
        elif m["role"] == "user":
            partes.append(f"[USUÁRIO] {m['content']}")
        elif m["role"] == "assistant" and m.get("content"):
            partes.append(f"[VOCÊ] {m['content']}")
    partes.append(
        "Responda só com a mensagem final em português do Brasil, 2-4 frases, direto, sem "
        "markdown e sem repetir o JSON de dados. Baseie qualquer número exclusivamente no "
        "JSON de dados acima - nunca invente estatística."
    )
    prompt = "\n\n".join(partes)

    try:
        resultado = subprocess.run(
            [CLAUDE_CLI_COMMAND, "-p", prompt, "--output-format", "json"],
            capture_output=True, encoding="utf-8", timeout=CLAUDE_CLI_TIMEOUT,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"CLI '{CLAUDE_CLI_COMMAND}' não encontrada no PATH do processo do backend. Se "
            "`claude` funciona no seu terminal mas não aqui, defina CLAUDE_CLI_COMMAND no "
            ".env com o caminho completo do binário."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Claude CLI demorou demais pra responder (ver CLAUDE_CLI_TIMEOUT).") from exc

    if resultado.returncode != 0:
        raise RuntimeError(f"Claude CLI falhou: {(resultado.stderr or resultado.stdout).strip()[:300]}")

    try:
        envelope = json.loads(resultado.stdout)
        return envelope.get("result") or ""
    except json.JSONDecodeError:
        return resultado.stdout.strip()
