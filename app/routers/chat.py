"""Endpoint do assistente de IA. Modelo é a assinatura do Claude Code via CLI (`claude -p`,
ver app/llm_client.py) - sem tool-calling de verdade, o contexto de dados é todo
pré-buscado e injetado no prompt em cada chamada.

Antes de gastar uma chamada de CLI, tenta resolver navegação simples localmente."""

import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.llm_client import chat_completion

router = APIRouter(tags=["chat"])

SYSTEM_PROMPT = (
    "Você é o assistente de IA do Climaton Brasil, um site que mostra dados climáticos brasileiros "
    "auditados (Painel ClimaBrasil, AdaptaBrasil, Gastos Climáticos, SICONFI). Responda sempre em "
    "português do Brasil, de forma direta e curta (2-4 frases). Baseie qualquer número "
    "exclusivamente no JSON de dados fornecido no contexto - nunca invente estatística. Se a "
    "pergunta não tiver nada a ver com os dados do site, diga isso educadamente e ofereça ajudar "
    "com o que o site cobre."
)

# Atalho de economia: pedidos de navegação óbvios resolvem sem chamar o modelo. Ids batem
# com o `id=` real das <section> em Climaton-Front-End/components/sections/*.tsx.
_PADRAO_NAVEGACAO = re.compile(
    r"\b(abr[ae]|v[aá]|leva|mostra|ir\s+para|ver)\b.*\b"
    r"(hist[oó]ria|dashboard|painel|territ[oó]rio|priorid|mapa|relatos?|cobertura|insights?|"
    r"compara[cç][aã]o|a[cç][aã]o|fontes|in[ií]cio)\b",
    re.IGNORECASE,
)
_MAPA_PALAVRA_SECAO = {
    "hist": "historia", "dashboard": "dashboard", "painel": "dashboard", "territ": "territorio",
    "priorid": "prioridades", "mapa": "mapa", "relato": "relatos", "cobertura": "cobertura",
    "insight": "insights", "compara": "comparacao", "acao": "acao", "ação": "acao",
    "fontes": "fontes", "inicio": "inicio", "início": "inicio",
}


def _secao_por_palavra(texto: str) -> str | None:
    texto = texto.lower()
    for chave, secao in _MAPA_PALAVRA_SECAO.items():
        if chave in texto:
            return secao
    return None


class Mensagem(BaseModel):
    role: str
    text: str


class PedidoChat(BaseModel):
    message: str
    history: list[Mensagem] = []


@router.post("/chat")
def chat(pedido: PedidoChat):
    # 1) atalho local, sem gastar chamada de CLI
    if _PADRAO_NAVEGACAO.search(pedido.message):
        secao = _secao_por_palavra(pedido.message)
        if secao:
            return {
                "reply": f"Beleza, indo pra seção de {secao}.",
                "actions": [{"type": "scroll_to_section", "target": secao}],
                "fontes": [], "resolvido_localmente": True,
            }

    # 2) LLM (Claude Code via CLI)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in pedido.history[-6:]:  # não manda histórico longo
        messages.append({"role": "user" if m.role == "user" else "assistant", "content": m.text})
    messages.append({"role": "user", "content": pedido.message})

    try:
        texto = chat_completion(messages)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not texto:
        texto = "Não consegui formular uma resposta clara agora - tenta reformular a pergunta?"

    return {"reply": texto, "actions": [], "fontes": [], "resolvido_localmente": False}
