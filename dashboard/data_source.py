"""Leitura dos dados brutos: PostgreSQL (usuario somente leitura) ou CSV local de desenvolvimento."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from analysis import rows_to_df

TABELAS_PERMITIDAS = {"responses", "responses_dev"}


def load_raw() -> pd.DataFrame:
    fonte = os.environ.get("SURVEY_SOURCE", "db")
    if fonte.startswith("csv:"):
        df = pd.read_csv(Path(fonte[4:]))
        df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
        return df
    import psycopg

    tabela = os.environ.get("SURVEY_TABLE", "responses")
    if tabela not in TABELAS_PERMITIDAS:
        raise ValueError("Tabela nao permitida")
    url = os.environ["DATABASE_URL_RO"]
    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute(f"select id, created_at, form_version, consent, answers from {tabela} order by created_at")
        cols = [c.name for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return rows_to_df(rows)
