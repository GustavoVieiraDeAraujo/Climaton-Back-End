from fastapi import APIRouter

from app.db import query

router = APIRouter(tags=["fontes"])


@router.get("/fontes")
def fontes():
    bases = query("SELECT fonte_id, codigo, nome, descricao, arquivo_origem FROM fontes ORDER BY fonte_id")
    qualidade = query("SELECT fonte_codigo, dimensao, classificacao, resumo FROM qualidade_fontes")
    por_codigo: dict[str, list[dict]] = {}
    for q in qualidade:
        por_codigo.setdefault(q["fonte_codigo"], []).append(
            {"dimensao": q["dimensao"], "classificacao": q["classificacao"], "resumo": q["resumo"]}
        )
    for b in bases:
        b["qualidade"] = por_codigo.get(b["codigo"], [])
    return {
        "dados": bases,
        "fonte": "tabelas fontes e qualidade_fontes, dataset_unificado/clima_brasil_climate_scanner.sqlite "
                 "- registro oficial de proveniência de cada base usada na construção do banco unificado.",
    }
