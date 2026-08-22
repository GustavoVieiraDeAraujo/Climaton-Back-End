"""
API do Climaton Brasil sobre o banco unificado e auditado.
Fonte única de dados: dataset/clima_brasil_climate_scanner.sqlite (cópia read-only
de dataset_unificado/clima_brasil_climate_scanner.sqlite na raiz do projeto).
Todo endpoint devolve um campo "fonte" apontando pra tabela/view/query de origem -
nunca um número sem proveniência (ver LOG_MESTRE.md, regra de rigor com fontes).

Estrutura: app/db.py (acesso ao SQLite), app/constants.py (geografia + slugs de eixo),
app/routers/*.py (um módulo por domínio) - este arquivo só monta o FastAPI e inclui os routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import DB_PATH
from app.routers import capitais, chat, eixo, fontes, gastos, insights, territorios

app = FastAPI(
    title="Climaton Brasil API",
    description="API somente-leitura sobre o banco unificado (Painel ClimaBrasil, AdaptaBrasil, "
                 "Painel de Gastos Climáticos, Fundo Clima, SICONFI, ClimateScanner Global).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(territorios.router)
app.include_router(capitais.router)
app.include_router(gastos.router)
app.include_router(insights.router)
app.include_router(eixo.router)
app.include_router(chat.router)
app.include_router(fontes.router)


@app.get("/health")
def health():
    return {"status": "ok", "banco": str(DB_PATH.name), "existe": DB_PATH.exists()}
