from fastapi import APIRouter

from app.db import query

router = APIRouter(tags=["territorios"])


@router.get("/territorios")
def territorios():
    rows = query("SELECT * FROM climate_gap_prioridade ORDER BY gap DESC")
    return {
        "dados": rows,
        "total": len(rows),
        "fonte": "view climate_gap_prioridade (dataset_unificado/clima_brasil_climate_scanner.sqlite) - "
                 "cruza risco físico real (AdaptaBrasil) com capacidade institucional declarada (Painel "
                 "ClimaBrasil, componente P5), banda de risco 5→3 níveis, capacidade em 3 faixas (0/0,333/0,667).",
    }


@router.get("/territorios/criticos")
def territorios_criticos():
    rows = query("SELECT * FROM climate_gap_prioridade WHERE prioridade='Crítico' ORDER BY gap DESC")
    return {
        "dados": rows,
        "total": len(rows),
        "fonte": "view climate_gap_prioridade, filtro prioridade='Crítico' - risco Alto/Muito alto "
                 "cruzado com capacidade Baixa.",
    }
