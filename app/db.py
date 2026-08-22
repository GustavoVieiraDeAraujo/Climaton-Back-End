"""Camada fina de acesso ao banco. Único lugar que abre o arquivo .sqlite."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "dataset" / "clima_brasil_climate_scanner.sqlite"


def query(sql: str, params: tuple = ()) -> list[dict]:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]
    finally:
        con.close()
