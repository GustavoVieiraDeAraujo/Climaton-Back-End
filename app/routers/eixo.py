from fastapi import APIRouter

from app.constants import regiao_do_territorio, resolve_eixo
from app.db import query

router = APIRouter(prefix="/eixo/{slug}", tags=["eixo"])


@router.get("/componentes")
def eixo_componentes(slug: str):
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
    return {
        "eixo": eixo,
        "dados": rows,
        "fonte": f"avaliacoes + componentes, fonte_id=1 (Painel ClimaBrasil), eixo='{eixo}' - média de "
                 "score_padronizado por componente, todos os 51 territórios e itens.",
    }


@router.get("/territorios")
def eixo_territorios(slug: str):
    eixo = resolve_eixo(slug)
    rows = query(
        """
        SELECT e.nome AS territorio, e.tipo, ROUND(AVG(a.score_padronizado), 3) AS media
        FROM avaliacoes a
        JOIN componentes c ON c.componente_id = a.componente_id
        JOIN entidades e ON e.entidade_id = a.entidade_id
        WHERE c.eixo = ? AND a.fonte_id = 1 AND a.score_padronizado IS NOT NULL
          AND e.nivel_geografico = 'Subnacional'
        GROUP BY e.entidade_id, e.nome, e.tipo ORDER BY media DESC
        """,
        (eixo,),
    )
    return {
        "eixo": eixo,
        "dados": rows,
        "total": len(rows),
        "fonte": f"avaliacoes + componentes + entidades, eixo='{eixo}' - média de score_padronizado por "
                 "território (todos os componentes do eixo), 51 territórios subnacionais.",
    }


@router.get("/regioes")
def eixo_regioes(slug: str):
    eixo = resolve_eixo(slug)
    rows = query(
        """
        SELECT e.nome AS territorio, e.tipo, ROUND(AVG(a.score_padronizado), 3) AS media
        FROM avaliacoes a
        JOIN componentes c ON c.componente_id = a.componente_id
        JOIN entidades e ON e.entidade_id = a.entidade_id
        WHERE c.eixo = ? AND a.fonte_id = 1 AND a.score_padronizado IS NOT NULL
          AND e.nivel_geografico = 'Subnacional'
        GROUP BY e.entidade_id, e.nome, e.tipo
        """,
        (eixo,),
    )
    por_regiao: dict[str, list[float]] = {}
    for r in rows:
        regiao = regiao_do_territorio(r["territorio"], r["tipo"])
        if regiao:
            por_regiao.setdefault(regiao, []).append(r["media"])
    ordem = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
    dados = [
        {"regiao": regiao, "media": round(sum(v) / len(v), 3), "n_territorios": len(v)}
        for regiao in ordem if (v := por_regiao.get(regiao))
    ]
    return {
        "eixo": eixo,
        "dados": dados,
        "fonte": f"avaliacoes + componentes + entidades, eixo='{eixo}' - média de score_padronizado por "
                 "território, agrupada por macrorregião IBGE (mapeamento fixo território->UF->região, "
                 "não vem do banco - ver app/constants.py).",
    }


@router.get("/distribuicao")
def eixo_distribuicao(slug: str):
    eixo = resolve_eixo(slug)
    rows = query(
        """
        SELECT c.codigo,
               COALESCE(a.score_text_original, 'Não avaliado') AS estagio,
               COUNT(*) AS n
        FROM avaliacoes a JOIN componentes c ON c.componente_id = a.componente_id
        WHERE c.eixo = ? AND a.fonte_id = 1
        GROUP BY c.codigo, estagio ORDER BY c.codigo
        """,
        (eixo,),
    )
    return {
        "eixo": eixo,
        "dados": rows,
        "fonte": f"avaliacoes + componentes, eixo='{eixo}' - contagem de avaliações por estágio "
                 "(Sem progresso/Estágio inicial/intermediário/avançado/Não avaliado), por componente.",
    }
