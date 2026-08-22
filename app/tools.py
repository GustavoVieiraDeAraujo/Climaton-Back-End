"""Funções de dado do chatbot. Cada uma reusa exatamente a mesma query dos routers
correspondentes (app/routers/*.py), nunca duplicar lógica de SQL, só reexpor pro
modelo. São chamadas direto (pré-busca, sem tool-calling) por
app/llm_client.py::_contexto_dados_cli antes de cada chamada ao `claude -p`."""

from app.constants import resolve_eixo
from app.db import query


def get_territorios_criticos() -> dict:
    rows = query("SELECT * FROM climate_gap_prioridade WHERE prioridade='Crítico' ORDER BY gap DESC")
    return {
        "dados": rows,
        "fonte": "view climate_gap_prioridade, filtro prioridade='Crítico' - risco Alto/Muito alto "
                 "cruzado com capacidade Baixa.",
    }


def get_gastos_resumo() -> dict:
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
        "pct_principal": round(100 * principal / total, 2) if total else 0,
        "alerta": "70,6% da categoria 'Redução do risco de desastres' é crédito/seguro agrícola e "
                  "programa nuclear mal classificados sob o mesmo rótulo - nunca citar o total bruto "
                  "sem abrir a composição.",
        "fonte": "view gasto_ambiental_serie_anual, dimensao='Mudança Climática', 2010-2023.",
    }


def get_gastos_serie_anual() -> dict:
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
    return {
        "dados": [{"ano": ano, "valor": valor} for ano, valor in sorted(por_ano.items())],
        "fonte": "view gasto_ambiental_serie_anual, soma Principal + Secundário Positivo por ano.",
    }


def get_justica_climatica() -> dict:
    rows = query(
        """
        SELECT e.nome AS capital, a.score_text_original AS estagio, a.score_padronizado AS score
        FROM avaliacoes a JOIN entidades e ON e.entidade_id = a.entidade_id
        WHERE a.componente_id='BR_G6' AND a.item_letra='A'
          AND e.tipo='Município' AND e.nivel_geografico='Subnacional'
        ORDER BY a.score_padronizado DESC, e.nome
        """
    )
    grupos: dict[str, list[str]] = {"avançado": [], "intermediário": [], "inicial": [], "sem progresso": []}
    for r in rows:
        s = r["score"]
        chave = "avançado" if s == 1.0 else "intermediário" if s and s > 0.5 else "inicial" if s and s > 0 else "sem progresso"
        grupos[chave].append(r["capital"])
    return {
        "total_capitais": len(rows), "grupos": grupos,
        "interpretacao_importante": (
            f"CUIDADO ao resumir: só as {len(grupos['avançado'])} capitais em 'avançado' "
            f"identificaram formalmente os grupos vulneráveis por completo. 'Intermediário' e "
            f"'inicial' são progresso PARCIAL, não identificação concluída - NÃO some avançado + "
            f"intermediário + inicial e chame isso de 'já identificaram'. As "
            f"{len(grupos['sem progresso'])} capitais em 'sem progresso' não fizeram nada disso."
        ),
        "fonte": "avaliacoes, componente_id='BR_G6' item_letra='A' (Justiça climática, mapeamento de "
                 "grupos vulneráveis) - Painel ClimaBrasil.",
    }


def get_comparacao_brasil_mundo() -> dict:
    rows = query("SELECT * FROM comparacao_brasil_vs_mundo ORDER BY eixo, componente_brasil")
    return {
        "dados": rows,
        "fonte": "view comparacao_brasil_vs_mundo - Painel ClimaBrasil (subnacional + Brasil-país) x "
                 "ClimateScanner Global (101 países).",
    }


def get_eixo_dados(slug: str) -> dict:
    eixo = resolve_eixo(slug)
    rows = query(
        """
        SELECT c.codigo, c.nome, ROUND(AVG(a.score_padronizado), 3) AS media, COUNT(*) AS n_avaliacoes
        FROM avaliacoes a JOIN componentes c ON c.componente_id = a.componente_id
        WHERE c.eixo = ? AND a.fonte_id = 1 AND a.score_padronizado IS NOT NULL
        GROUP BY c.codigo, c.nome ORDER BY c.codigo
        """,
        (eixo,),
    )
    return {"eixo": eixo, "dados": rows, "fonte": f"avaliacoes + componentes, eixo='{eixo}' (Painel ClimaBrasil)."}


def get_cobertura() -> dict:
    return {
        "universo_total": 27,
        "avaliadas_painel_climabrasil": 25,
        "ausentes": ["Goiânia (GO)", "Aracaju (SE)"],
        "explicacao": "Goiânia e Aracaju não constam na avaliação do Painel ClimaBrasil - têm risco "
                      "físico medido (AdaptaBrasil), mas não têm a metade institucional do cruzamento.",
        "fonte": "entidades vs. adaptabrasil_risco.",
    }


