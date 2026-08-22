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


# Filtro de exclusão de ruído documentado em auditoria_ruido (id=1): a categoria bruta "3. Redução
# do risco de desastres" tem 70,6% do valor composto por crédito/seguro agrícola (PRONAF/PROAGRO)
# e programa nuclear mal classificados sob o mesmo rótulo de "prevenção" - mesmo filtro de palavra-
# chave na ação usado no resto do backend pra essa categoria.
_FILTRO_RUIDO_DESASTRES = (
    "LOWER(acao) LIKE '%indeniza%' OR LOWER(acao) LIKE '%restitui%' OR LOWER(acao) LIKE '%nuclear%' "
    "OR LOWER(acao) LIKE '%radiof%' OR LOWER(acao) LIKE '%combust%' OR LOWER(acao) LIKE '%prêmio%' "
    "OR LOWER(acao) LIKE '%premio%'"
)


@router.get("/desastres-prevencao-vs-recuperacao")
def gastos_desastres_prevencao_vs_recuperacao():
    def soma(where: str) -> float:
        r = query(f"SELECT SUM(despesa_deflacionada) AS v FROM gastos_climaticos WHERE {where}")
        return r[0]["v"] or 0.0

    resposta_recuperacao = soma("impacto_desastres='Positivo' AND categoria_desastres LIKE '4.%'")
    reducao_risco_bruto = soma("impacto_desastres='Positivo' AND categoria_desastres LIKE '3.%'")
    reducao_risco_limpo = soma(
        f"impacto_desastres='Positivo' AND categoria_desastres LIKE '3.%' AND NOT ({_FILTRO_RUIDO_DESASTRES})"
    )
    compreensao_e_governanca = soma(
        "impacto_desastres='Positivo' AND (categoria_desastres LIKE '1.%' OR categoria_desastres LIKE '2.%')"
    )
    prevencao_total = reducao_risco_limpo + compreensao_e_governanca

    # Mesma decomposição, ano a ano - alimenta o heatmap de calendário na seção História.
    # reducao_risco aqui já soma o filtro de ruído (3, limpo) + compreensão/governança (1+2),
    # pra bater exatamente com prevencao_total acima.
    recuperacao_por_ano = {
        r["ano_exercicio"]: r["v"] for r in query(
            "SELECT ano_exercicio, SUM(despesa_deflacionada) AS v FROM gastos_climaticos "
            "WHERE impacto_desastres='Positivo' AND categoria_desastres LIKE '4.%' "
            "GROUP BY ano_exercicio"
        )
    }
    prevencao_por_ano = {
        r["ano_exercicio"]: r["v"] for r in query(
            f"SELECT ano_exercicio, SUM(despesa_deflacionada) AS v FROM gastos_climaticos "
            f"WHERE impacto_desastres='Positivo' AND ("
            f"  (categoria_desastres LIKE '3.%' AND NOT ({_FILTRO_RUIDO_DESASTRES}))"
            f"  OR categoria_desastres LIKE '1.%' OR categoria_desastres LIKE '2.%'"
            f") GROUP BY ano_exercicio"
        )
    }
    anos = sorted(set(recuperacao_por_ano) | set(prevencao_por_ano))
    serie_anual = [
        {
            "ano": ano,
            "recuperacao": recuperacao_por_ano.get(ano, 0.0),
            "prevencao": prevencao_por_ano.get(ano, 0.0),
        }
        for ano in anos
    ]

    return {
        "resposta_recuperacao": resposta_recuperacao,
        "reducao_risco_bruto": reducao_risco_bruto,
        "reducao_risco_limpo": reducao_risco_limpo,
        "compreensao_e_governanca": compreensao_e_governanca,
        "prevencao_total": prevencao_total,
        "razao_recuperacao_por_prevencao": round(resposta_recuperacao / prevencao_total, 2) if prevencao_total else None,
        "serie_anual": serie_anual,
        "alerta": "categoria bruta 'Redução do risco de desastres' (reducao_risco_bruto) tem 70,6% de "
                  "crédito/seguro agrícola e programa nuclear mal classificados sob o mesmo rótulo - "
                  "excluído aqui via filtro de palavra-chave na ação (mesmo tratamento do auditoria_ruido "
                  "id=1). prevencao_total usa reducao_risco_limpo, não o bruto.",
        "fonte": "gastos_climaticos, categoria_desastres (1. Compreensão do risco, 2. Governança do risco, "
                 "3. Redução do risco, 4. Resposta e recuperação de desastres), impacto_desastres='Positivo', "
                 "2010-2023, dataset_unificado/clima_brasil_climate_scanner.sqlite.",
    }
