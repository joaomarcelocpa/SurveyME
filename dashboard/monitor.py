"""Metricas de acompanhamento da coleta e verificacao do banco. Funcoes puras, sem Streamlit."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd

import analysis as an

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import backup as bk  # noqa: E402

META = 60       # protocolo: meta de respostas
MINIMO = 50     # protocolo: minimo de respostas validas
COBERTURA_MIN = 10  # minimo desejavel por grupo comparado
TRIGGERS_ESPERADOS = {"responses_no_update_delete", "responses_no_truncate"}
TZ = "America/Sao_Paulo"


def local(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True).dt.tz_convert(TZ)


def acumulado(todos: pd.DataFrame) -> pd.DataFrame:
    """Respostas recebidas e validas acumuladas por hora."""
    if todos.empty:
        return pd.DataFrame(columns=["hora", "recebidas", "válidas"])
    d = todos.assign(hora=local(todos["created_at"]).dt.floor("h"))
    por = d.groupby("hora").agg(novas=("id", "size"), validas=("valida", "sum"))
    idx = pd.date_range(por.index.min(), por.index.max(), freq="h")
    por = por.reindex(idx, fill_value=0)
    return pd.DataFrame({"hora": por.index, "recebidas": por["novas"].cumsum().values,
                         "válidas": por["validas"].cumsum().astype(int).values, "novas na hora": por["novas"].values})


def rajadas(todos: pd.DataFrame, n: int = 5, janela_min: int = 5) -> pd.DataFrame:
    """Janelas com `n` ou mais respostas em ate `janela_min` minutos (possivel automacao ou compartilhamento em massa)."""
    if len(todos) < n:
        return pd.DataFrame(columns=["início", "respostas"])
    t = pd.to_datetime(todos["created_at"], utc=True).sort_values().reset_index(drop=True)
    saida, i = [], 0
    while i + n - 1 < len(t):
        if (t[i + n - 1] - t[i]).total_seconds() <= janela_min * 60:
            fim = i + n - 1
            while fim + 1 < len(t) and (t[fim + 1] - t[i]).total_seconds() <= janela_min * 60:
                fim += 1
            saida.append({"início": t[i].tz_convert(TZ), "respostas": fim - i + 1})
            i = fim + 1
        else:
            i += 1
    return pd.DataFrame(saida, columns=["início", "respostas"])


def duracao(todos: pd.DataFrame, min_s: float) -> dict:
    d = pd.to_numeric(todos.get("duration_s"), errors="coerce").dropna()
    if d.empty:
        return {"mediana": None, "p10": None, "p90": None, "abaixo_minimo": 0}
    return {"mediana": float(d.median()), "p10": float(d.quantile(.1)), "p90": float(d.quantile(.9)),
            "abaixo_minimo": int((d < min_s).sum())}


def cobertura(validos: pd.DataFrame, q: dict) -> pd.DataFrame:
    """Respostas validas por grupo comparado nas QPs, com situacao frente a COBERTURA_MIN."""
    linhas = []
    for rq in q["research_questions"]:
        if rq["test"] == "kruskal":
            g = rq["group"]
            for o in an.item_map(q)[g]["options"]:
                linhas.append((rq["id"], o["label"], int((validos[g] == o["value"]).sum())))
        elif rq["test"] == "mannwhitney":
            a, b = rq["groups"]
            ga = an.grupo_exclusivo(validos[rq["group"]], a, b)
            for nome, val in (("só " + a.replace("_", " "), a), ("só " + b.replace("_", " "), b)):
                linhas.append((rq["id"], nome, int((ga == val).sum())))
        else:
            linhas.append((rq["id"], "respostas com frequência e confiança", int(validos[rq["x"]].notna().sum())))
    out = pd.DataFrame(linhas, columns=["QP", "grupo", "n"])
    out["situação"] = ["ok" if n >= COBERTURA_MIN else "baixa" for n in out["n"]]
    return out


def saude_banco(url: str, tabela: str = "responses") -> dict:
    """Checagens somente-leitura do banco: conexao, contagem, travas de imutabilidade e privilegios do usuario."""
    import psycopg

    res = {"ok": False, "erro": None}
    try:
        t0 = time.perf_counter()
        with psycopg.connect(url, connect_timeout=10) as con, con.cursor() as cur:
            cur.execute(f"select count(*), max(created_at) from {tabela}")
            total, ultima = cur.fetchone()
            res["latencia_ms"] = round((time.perf_counter() - t0) * 1000)
            cur.execute("select tgname from pg_trigger where tgrelid = %s::regclass and not tgisinternal", (tabela,))
            triggers = {r[0] for r in cur.fetchall()}
            cur.execute("select has_table_privilege(current_user, %s, 'INSERT') or has_table_privilege(current_user, %s, 'UPDATE') "
                        "or has_table_privilege(current_user, %s, 'DELETE')", (tabela, tabela, tabela))
            pode_escrever = bool(cur.fetchone()[0])
        res.update(ok=True, total=int(total), ultima=ultima, triggers=sorted(triggers),
                   travas_ok=TRIGGERS_ESPERADOS <= triggers, usuario_pode_escrever=pode_escrever)
    except Exception as e:  # noqa: BLE001
        res["erro"] = type(e).__name__
    return res


def estado_backup(rows_df_count: int, d: Path | None = None) -> dict:
    """Resumo do ultimo backup local para exibir no monitor."""
    d = d or Path(os.environ.get("SURVEY_BACKUP_DIR") or Path.home() / "survey-backups").expanduser()
    m = bk.load_manifest(d) if d.exists() else []
    if not m:
        return {"existe": False, "pasta": str(d)}
    u = m[-1]
    return {"existe": True, "pasta": str(d), "gerado_em": u["gerado_em"], "total": u["total"], "arquivos": len(m),
            "atrasado_horas": round((pd.Timestamp.now(tz="UTC") - pd.Timestamp(u["gerado_em"])).total_seconds() / 3600, 1),
            "diferenca": rows_df_count - u["total"]}
