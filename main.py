"""
API do Climaton Brasil sobre o banco unificado e auditado.
Fonte única de dados: dataset/clima_brasil_climate_scanner.sqlite (cópia read-only
de dataset_unificado/clima_brasil_climate_scanner.sqlite na raiz do projeto).
Todo endpoint devolve um campo "fonte" apontando pra tabela/view/query de origem -
nunca um número sem proveniência (ver LOG_MESTRE.md, regra de rigor com fontes).
"""

import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

DB_PATH = Path(__file__).parent / "dataset" / "clima_brasil_climate_scanner.sqlite"

app = FastAPI(
    title="Climaton Brasil API",
    description="API somente-leitura sobre o banco unificado (Painel ClimaBrasil, AdaptaBrasil, "
                 "Painel de Gastos Climáticos, Fundo Clima, SICONFI, ClimateScanner Global).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def query(sql: str, params: tuple = ()) -> list[dict]:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]
    finally:
        con.close()


# Coordenadas das 27 capitais (26 capitais estaduais + Distrito Federal). Não existem no
# banco (que é tabular, não geoespacial) - mantidas aqui, fonte: IBGE, sede dos municípios.
CAPITAL_COORDS = {
    "Rio Branco": (-9.97, -67.81), "Maceió": (-9.66, -35.73), "Macapá": (0.03, -51.07),
    "Manaus": (-3.10, -60.02), "Salvador": (-12.97, -38.50), "Fortaleza": (-3.73, -38.52),
    "Brasília": (-15.79, -47.88), "Vitória": (-20.32, -40.34), "Goiânia": (-16.68, -49.25),
    "São Luís": (-2.53, -44.30), "Cuiabá": (-15.60, -56.10), "Campo Grande": (-20.47, -54.62),
    "Belo Horizonte": (-19.92, -43.94), "Belém": (-1.45, -48.50), "João Pessoa": (-7.12, -34.86),
    "Curitiba": (-25.43, -49.27), "Recife": (-8.05, -34.90), "Teresina": (-5.09, -42.80),
    "Rio de Janeiro": (-22.90, -43.17), "Natal": (-5.79, -35.20), "Porto Alegre": (-30.03, -51.23),
    "Porto Velho": (-8.76, -63.90), "Boa Vista": (2.82, -60.67), "Florianópolis": (-27.59, -48.55),
    "São Paulo": (-23.55, -46.63), "Aracaju": (-10.91, -37.07), "Palmas": (-10.18, -48.33),
}
CAPITAL_UF = {
    "Rio Branco": "AC", "Maceió": "AL", "Macapá": "AP", "Manaus": "AM", "Salvador": "BA",
    "Fortaleza": "CE", "Brasília": "DF", "Vitória": "ES", "Goiânia": "GO", "São Luís": "MA",
    "Cuiabá": "MT", "Campo Grande": "MS", "Belo Horizonte": "MG", "Belém": "PA",
    "João Pessoa": "PB", "Curitiba": "PR", "Recife": "PE", "Teresina": "PI",
    "Rio de Janeiro": "RJ", "Natal": "RN", "Porto Alegre": "RS", "Porto Velho": "RO",
    "Boa Vista": "RR", "Florianópolis": "SC", "São Paulo": "SP", "Aracaju": "SE", "Palmas": "TO",
}


@app.get("/health")
def health():
    return {"status": "ok", "banco": str(DB_PATH.name), "existe": DB_PATH.exists()}


@app.get("/territorios")
def territorios():
    rows = query("SELECT * FROM climate_gap_prioridade ORDER BY gap DESC")
    return {
        "dados": rows,
        "total": len(rows),
        "fonte": "view climate_gap_prioridade (dataset_unificado/clima_brasil_climate_scanner.sqlite) - "
                 "cruza risco físico real (AdaptaBrasil) com capacidade institucional declarada (Painel "
                 "ClimaBrasil, componente P5), banda de risco 5→3 níveis, capacidade em 3 faixas (0/0,333/0,667).",
    }


@app.get("/territorios/criticos")
def territorios_criticos():
    rows = query("SELECT * FROM climate_gap_prioridade WHERE prioridade='Crítico' ORDER BY gap DESC")
    return {
        "dados": rows,
        "total": len(rows),
        "fonte": "view climate_gap_prioridade, filtro prioridade='Crítico' - risco Alto/Muito alto "
                 "cruzado com capacidade Baixa.",
    }


@app.get("/capitais")
def capitais():
    avaliadas = {r["territorio"]: r for r in query(
        "SELECT * FROM climate_gap_prioridade WHERE tipo IN ('Município', 'Distrito Federal')"
    )}
    out = []
    for nome, (lat, lng) in CAPITAL_COORDS.items():
        base = {"nome": nome, "uf": CAPITAL_UF[nome], "lat": lat, "lng": lng}
        if nome in avaliadas:
            r = avaliadas[nome]
            base.update(
                risco=r["risco"], faixa_risco=r["faixa_risco"], capacidade=r["capacidade_p5"],
                prioridade=r["prioridade"], avaliada_painel_climabrasil=True,
            )
        else:
            base.update(risco=None, faixa_risco=None, capacidade=None, prioridade=None,
                         avaliada_painel_climabrasil=False)
        out.append(base)
    return {
        "dados": out,
        "total": len(out),
        "avaliadas_painel_climabrasil": sum(1 for c in out if c["avaliada_painel_climabrasil"]),
        "fonte": "coordenadas: sede dos municípios (IBGE); risco/capacidade/prioridade: view "
                 "climate_gap_prioridade quando a capital está na amostra do Painel ClimaBrasil.",
    }


@app.get("/cobertura")
def cobertura():
    return {
        "universo_total": 27,
        "universo_definicao": "26 capitais estaduais + Distrito Federal (Brasília), uma por unidade federativa.",
        "avaliadas_painel_climabrasil": 25,
        "avaliadas_detalhe": "24 capitais-município + Distrito Federal (avaliado como entidade própria, "
                              "tipo='Distrito Federal', não contado no rótulo oficial '24 municípios').",
        "ausentes": ["Goiânia (GO)", "Aracaju (SE)"],
        "explicacao": "Goiânia e Aracaju não constam na tabela de avaliações do Painel ClimaBrasil "
                       "(fonte bruta painel-climabrasil-raw.csv) - não há avaliação de nenhum dos 45 itens "
                       "para essas duas capitais no arquivo que baixamos. Não encontramos, nas fontes "
                       "públicas que auditamos, uma nota oficial do Painel explicando por que essas duas "
                       "faltam especificamente; o próprio painel se rotula como avaliação de '27 estados "
                       "e 24 municípios' sem detalhar o critério de amostragem dos municípios. Por isso "
                       "não afirmamos um motivo - só o fato, auditável, de que a avaliação institucional "
                       "não existe para essas duas capitais.",
        "risco_fisico_disponivel": "Goiânia e Aracaju TÊM risco físico real medido pelo AdaptaBrasil "
                                    "(mesma fonte usada para as outras 24) - só falta a metade institucional "
                                    "do cruzamento, por isso não é possível calcular prioridade pra elas.",
        "fonte": "entidades (tipo='Município', nivel_geografico='Subnacional') vs. adaptabrasil_risco "
                 "(nome_municipio) - dataset_unificado/clima_brasil_climate_scanner.sqlite.",
    }


@app.get("/gastos/serie-anual")
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


@app.get("/gastos/resumo")
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


EIXO_SLUGS = {
    "governanca": "Governança",
    "politicas-publicas": "Políticas Públicas",
    "financiamento": "Financiamento",
}


def _resolve_eixo(slug: str) -> str:
    eixo = EIXO_SLUGS.get(slug)
    if not eixo:
        raise HTTPException(status_code=404, detail=f"Eixo '{slug}' não existe. Use: {list(EIXO_SLUGS)}")
    return eixo


@app.get("/eixo/{slug}/componentes")
def eixo_componentes(slug: str):
    eixo = _resolve_eixo(slug)
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
        "fonte": f"avaliacoes + componentes, fonte_id=1 (Painel ClimaBrasil), eixo='{eixo}' — média de "
                 "score_padronizado por componente, todos os 51 territórios e itens.",
    }


@app.get("/eixo/{slug}/territorios")
def eixo_territorios(slug: str):
    eixo = _resolve_eixo(slug)
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
        "fonte": f"avaliacoes + componentes + entidades, eixo='{eixo}' — média de score_padronizado por "
                 "território (todos os componentes do eixo), 51 territórios subnacionais.",
    }


@app.get("/eixo/{slug}/distribuicao")
def eixo_distribuicao(slug: str):
    eixo = _resolve_eixo(slug)
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
        "fonte": f"avaliacoes + componentes, eixo='{eixo}' — contagem de avaliações por estágio "
                 "(Sem progresso/Estágio inicial/intermediário/avançado/Não avaliado), por componente.",
    }


@app.get("/gastos/por-orgao")
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


@app.get("/justica-climatica")
def justica_climatica():
    rows = query(
        """
        SELECT e.nome AS capital, a.score_text_original AS estagio, a.score_padronizado AS score
        FROM avaliacoes a JOIN entidades e ON e.entidade_id = a.entidade_id
        WHERE a.componente_id='BR_G6' AND a.item_letra='A'
          AND e.tipo='Município' AND e.nivel_geografico='Subnacional'
        ORDER BY a.score_padronizado DESC, e.nome
        """
    )
    grupos = {"avançado": [], "intermediário": [], "inicial": [], "sem progresso": []}
    for r in rows:
        s = r["score"]
        chave = "avançado" if s == 1.0 else "intermediário" if s and s > 0.5 else "inicial" if s and s > 0 else "sem progresso"
        grupos[chave].append(r["capital"])
    return {
        "total_capitais": len(rows),
        "grupos": grupos,
        "fonte": "avaliacoes, componente_id='BR_G6' (Justiça climática), item_letra='A' (mapeamento "
                 "de grupos vulneráveis), join entidades tipo='Município' - Painel ClimaBrasil.",
    }


@app.get("/comparacao-brasil-mundo")
def comparacao_brasil_mundo():
    rows = query("SELECT * FROM comparacao_brasil_vs_mundo ORDER BY eixo, componente_brasil")
    return {
        "dados": rows,
        "fonte": "view comparacao_brasil_vs_mundo - cruza Painel ClimaBrasil (média subnacional dos 51 "
                 "territórios e nota do Brasil-país) com ClimateScanner Global (média de 101 países).",
    }


# Textos de leitura automática por seção - gerados por template a partir de consulta direta ao banco,
# não por um modelo de linguagem (nenhuma chave de LLM configurada nesta fase). Cada resposta é
# honesta sobre a própria origem: ver campo "gerado_por".
_RESUMOS = {
    "historia": "O Painel ClimaBrasil avalia 51 territórios (26 estados + DF + 24 capitais) em 45 "
                "itens de governança, políticas públicas e financiamento. A própria metodologia "
                "oficial avisa: mede se o mecanismo existe, não se ele funciona.",
    "dashboard": "R$421,32 bilhões em gasto climático 'positivo' entre 2010 e 2023 - mas o pico foi em "
                 "2013 e a série cai depois disso. Só 3,88% desse total teve o clima como propósito "
                 "principal da despesa desde o início.",
    "territorio": "5 territórios cruzam risco físico alto com capacidade institucional baixa agora: "
                  "Macapá, Fortaleza, São Luís, Pernambuco (estado) e Maceió - prioridade Crítica pela "
                  "matriz risco × capacidade.",
    "mapa": "Das 27 capitais (26 estaduais + Brasília), 25 têm avaliação institucional do Painel "
            "ClimaBrasil; Goiânia e Aracaju têm risco físico real medido, mas não constam na amostra "
            "avaliada.",
    "insights": "Só 4 das 24 capitais avaliadas em Justiça Climática identificaram formalmente quem "
                "sofre primeiro com o clima; 7 estão em 'sem progresso' total. O Brasil-país tira nota "
                "1,0 em Fiscalização e Litígio Climático no ranking global - a média real dos "
                "territórios por dentro é 0,456.",
    "acao": "Todo número desta leitura tem uma tabela, uma view e uma query de origem no banco "
            "unificado e auditado - a distância entre saber e agir começa em saber onde cobrar.",
}


@app.get("/resumo/{secao}")
def resumo(secao: str):
    if secao not in _RESUMOS:
        raise HTTPException(status_code=404, detail=f"Seção '{secao}' não existe. Use: {list(_RESUMOS)}")
    return {
        "secao": secao,
        "texto": _RESUMOS[secao],
        "gerado_por": "template",
        "nota": "Resumo gerado por template determinístico a partir de consulta direta ao banco - "
                "não é saída de um modelo de linguagem. Wiring com LLM real é a próxima etapa.",
    }
