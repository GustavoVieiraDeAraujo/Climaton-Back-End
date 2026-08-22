"""Dados de referência que não vêm do banco (geografia, mapeamento de slugs de URL)."""

from fastapi import HTTPException

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

EIXO_SLUGS = {
    "governanca": "Governança",
    "politicas-publicas": "Políticas Públicas",
    "financiamento": "Financiamento",
}


def resolve_eixo(slug: str) -> str:
    eixo = EIXO_SLUGS.get(slug)
    if not eixo:
        raise HTTPException(status_code=404, detail=f"Eixo '{slug}' não existe. Use: {list(EIXO_SLUGS)}")
    return eixo
