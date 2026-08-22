from fastapi import APIRouter

from app.db import query

router = APIRouter(prefix="/gastos", tags=["gastos"])


@router.get("/serie-anual")
def gastos_serie_anual():
    rows = query(
        """
        SELECT ano_exercicio, proposito, SUM(valor_total) AS valor
        FROM gasto_ambiental_serie_anual
        WHERE dimensao='Mudança Climática' AND proposito IN ('Principal','Secundário Positivo')
        GROUP BY ano_exercicio, proposito
        ORDER BY ano_exercicio
        """
    )
    por_ano: dict[int, float] = {}
    for r in rows:
        por_ano[r["ano_exercicio"]] = por_ano.get(r["ano_exercicio"], 0) + r["valor"]
    pico = max(por_ano.values())
    serie = [
        {"ano": ano, "valor": valor, "pct_do_pico": round(100 * valor / pico, 1)}
        for ano, valor in sorted(por_ano.items())
    ]
    return {
        "dados": serie,
        "fonte": "view gasto_ambiental_serie_anual, dimensao='Mudança Climática', soma de Principal + "
                 "Secundário Positivo (exclui Secundário Negativo) por ano_exercicio, 2010-2023.",
    }


@router.get("/resumo")
def gastos_resumo():
    rows = query(
        """
        SELECT proposito, SUM(valor_total) AS valor
        FROM gasto_ambiental_serie_anual
        WHERE dimensao='Mudança Climática' AND proposito IN ('Principal','Secundário Positivo')
        GROUP BY proposito
        """
    )
    total = sum(r["valor"] for r in rows)
    principal = next((r["valor"] for r in rows if r["proposito"] == "Principal"), 0)
    return {
        "total_positivo": total,
        "principal": principal,
        "secundario_positivo": total - principal,
        "pct_principal": round(100 * principal / total, 2),
        "pct_secundario": round(100 * (total - principal) / total, 2),
        "alerta": "70,6% da categoria 'Redução do risco de desastres' é crédito/seguro agrícola e "
                  "programa nuclear mal classificados sob o mesmo rótulo - nunca citar o total bruto "
                  "sem abrir a composição (ver auditoria_ruido, id=1 e id=2).",
        "fonte": "view gasto_ambiental_serie_anual, dimensao='Mudança Climática', 2010-2023, valores "
                 "deflacionados dez/2023 (Painel de Gastos Climáticos, Tesouro/MF).",
    }


@router.get("/por-orgao")
def gastos_por_orgao(limit: int = 8):
    rows = query(
        "SELECT orgao, gasto_clima, gasto_desastres, gasto_biodiversidade FROM gasto_ambiental_por_orgao "
        "ORDER BY gasto_clima DESC LIMIT ?",
        (limit,),
    )
    return {
        "dados": rows,
        "fonte": "view gasto_ambiental_por_orgao - soma bruta por órgão orçamentário nas 3 dimensões "
                 "paralelas do Painel de Gastos Climáticos (Mudança Climática, Desastres, Biodiversidade), "
                 "2010-2023. Números brutos, sem o filtro de ruído - usar como visão geral de escala por "
                 "órgão, não como total climático 'limpo' (ver /gastos/resumo pra isso).",
    }
