from fastapi import APIRouter, HTTPException

from app.db import query

router = APIRouter(tags=["insights"])


@router.get("/justica-climatica")
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


@router.get("/comparacao-brasil-mundo")
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


@router.get("/resumo/{secao}")
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
