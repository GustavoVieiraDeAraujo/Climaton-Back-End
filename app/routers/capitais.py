from fastapi import APIRouter

from app.constants import CAPITAL_COORDS, CAPITAL_UF
from app.db import query

router = APIRouter(tags=["capitais"])


@router.get("/capitais")
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


@router.get("/cobertura")
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
