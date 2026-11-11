"""Funcoes de analise do survey. Tudo e derivado de questionnaire.json."""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pingouin as pg
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
Q_PATH = ROOT / "questionnaire.json"

MOTIVOS = ["fora da população", "incompleta", "falhou na atenção", "tempo muito curto", "duplicada"]


def load_questionnaire(path: Path = Q_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def item_map(q: dict) -> dict:
    return {i["id"]: i for i in q["items"]}


# ---------------------------------------------------------------- carga

def normalize_answers(answers: dict) -> dict:
    out = dict(answers)
    for k in ("Q7", "Q9"):  # multipla escolha: guardada como texto "a|b" (ordenado)
        if isinstance(out.get(k), list):
            out[k] = "|".join(sorted(out[k]))
    return out


def tem_opcao(s: pd.Series, valor: str) -> pd.Series:
    """True onde a resposta de multipla escolha (texto "a|b") inclui `valor`."""
    return s.fillna("").astype(str).str.split("|").apply(lambda v: valor in v)


def grupo_exclusivo(s: pd.Series, a: str, b: str) -> pd.Series:
    """Grupo `a` = marcou a e nao b; grupo `b` = marcou b e nao a; os demais ficam fora (NaN)."""
    ta, tb = tem_opcao(s, a), tem_opcao(s, b)
    out = pd.Series(np.nan, index=s.index, dtype=object)
    out[ta & ~tb] = a
    out[tb & ~ta] = b
    return out


def rows_to_df(rows: list[dict]) -> pd.DataFrame:
    recs = []
    for r in rows:
        a = r["answers"] if isinstance(r["answers"], dict) else json.loads(r["answers"])
        recs.append(
            {"id": str(r["id"]), "created_at": r["created_at"], "form_version": r["form_version"],
             "consent": r["consent"], **normalize_answers(a)}
        )
    df = pd.DataFrame(recs)
    if not df.empty:
        df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    return df


# ---------------------------------------------------------------- preparacao

def _empty(s: pd.Series) -> pd.Series:
    return s.isna() | (s.astype(str).str.strip() == "")


def classify(df: pd.DataFrame, q: dict, min_duration: float | None = None) -> pd.DataFrame:
    """Acrescenta `motivos` (lista) e `motivo` (primeiro, por prioridade). Nada e removido."""
    items = item_map(q)
    min_duration = q.get("min_duration_seconds", 60) if min_duration is None else min_duration
    d = df.copy()
    for it in q["items"]:
        if it["id"] not in d:
            d[it["id"]] = np.nan
    if "duration_s" not in d:
        d["duration_s"] = np.nan

    reasons: dict[str, pd.Series] = {}
    fora = ~d["consent"].fillna(False).astype(bool)
    for it in q["items"]:
        if it.get("role") == "screening":
            fora |= d[it["id"]] != it["pass_value"]
    reasons["fora da população"] = fora

    req = [i["id"] for i in q["items"] if i.get("required", True)]
    reasons["incompleta"] = pd.concat([_empty(d[c]) for c in req], axis=1).any(axis=1)

    att = next(i for i in q["items"] if i.get("role") == "attention")
    reasons["falhou na atenção"] = pd.to_numeric(d[att["id"]], errors="coerce") != att["expected"]
    reasons["tempo muito curto"] = pd.to_numeric(d["duration_s"], errors="coerce") < min_duration

    cols = [i["id"] for i in q["items"] if i["id"] in d]
    chave = d[cols].astype(object).fillna("").astype(str).apply(lambda r: "|".join(r), axis=1)
    ordem = d.sort_values("created_at") if "created_at" in d else d
    dup = pd.Series(False, index=d.index)
    for _, grupo in ordem.groupby(chave.loc[ordem.index]):
        if len(grupo) > 1 and "created_at" in grupo:
            t = grupo["created_at"].sort_values()
            ok = t.diff() <= pd.Timedelta(minutes=10)
            dup.loc[t.index[ok.values]] = True
    reasons["duplicada"] = dup

    d["motivos"] = [[m for m in MOTIVOS if reasons[m].iloc[i]] for i in range(len(d))]
    d["motivo"] = d["motivos"].apply(lambda m: m[0] if m else "")
    d["valida"] = d["motivo"] == ""
    return d


def flag_near_duplicates(df: pd.DataFrame, q: dict, janela_min: int = 60, tolerancia: int = 2) -> pd.Series:
    """Sinaliza (sem descartar) respostas quase iguais a outra anterior: mesmo perfil (itens de perfil),
    escalas de construto com soma de diferencas absolutas <= `tolerancia`, em ate `janela_min` minutos.
    Casos identicos ja sao descartados como `duplicada`; aqui so entram os quase iguais."""
    perfil = [i["id"] for i in q["items"] if i.get("role") == "profile" and i["id"] in df]
    escalas = [iid for c in q["constructs"].values() for iid in c["items"] if iid in df]
    flag = pd.Series(False, index=df.index)
    if df.empty or "created_at" not in df:
        return flag
    d = df.sort_values("created_at")
    num = d[escalas].apply(pd.to_numeric, errors="coerce")
    chave = d[perfil].fillna("").astype(object).astype(str).apply(lambda r: "|".join(r), axis=1)
    for _, grupo in d.groupby(chave):
        idx = list(grupo.index)
        for pos, j in enumerate(idx):
            for i in idx[:pos]:
                dt = (d.loc[j, "created_at"] - d.loc[i, "created_at"]).total_seconds() / 60
                if dt > janela_min:
                    continue
                dif = (num.loc[j] - num.loc[i]).abs().sum()
                if 0 < dif <= tolerancia:
                    flag.loc[j] = True
    return flag


def add_scores(df: pd.DataFrame, q: dict) -> pd.DataFrame:
    d = df.copy()
    items = item_map(q)
    for key, c in q["constructs"].items():
        cols = []
        for iid in c["items"]:
            s = pd.to_numeric(d[iid], errors="coerce")
            cols.append(q["likert_scale"] + 1 - s if items[iid].get("reverse") else s)
        d[key] = pd.concat(cols, axis=1).mean(axis=1, skipna=False)
    return d


def ordinal_codes(q: dict, iid: str, series: pd.Series) -> pd.Series:
    vals = [o["value"] for o in item_map(q)[iid]["options"]]
    return series.map({v: i + 1 for i, v in enumerate(vals)})


# ---------------------------------------------------------------- estatistica

def margin_of_error(p: float, n: int) -> float:
    """e = 1,96 * sqrt(p(1-p)/n)."""
    return float("nan") if n <= 0 else 1.96 * math.sqrt(p * (1 - p) / n)


def cronbach(df: pd.DataFrame, q: dict, construct: str) -> dict:
    items = item_map(q)
    cols = {}
    for iid in q["constructs"][construct]["items"]:
        s = pd.to_numeric(df[iid], errors="coerce")
        cols[iid] = q["likert_scale"] + 1 - s if items[iid].get("reverse") else s
    m = pd.DataFrame(cols).dropna()
    if len(m) < 3:
        return {"alpha": float("nan"), "ic": (float("nan"),) * 2, "n": len(m), "sem_item": {}}
    alpha, ic = pg.cronbach_alpha(data=m)
    sem = {}
    for c in m.columns:
        rest = m.drop(columns=c)
        sem[c] = float(pg.cronbach_alpha(data=rest)[0]) if rest.shape[1] > 1 else float("nan")
    return {"alpha": float(alpha), "ic": tuple(float(x) for x in ic), "n": len(m), "sem_item": sem}


def holm(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (m - rank) * pvals[i])
        adj[i] = min(1.0, run)
    return adj.tolist()


def spearman(x: pd.Series, y: pd.Series, n_boot: int = 2000, seed: int = 0) -> dict:
    d = pd.concat([x, y], axis=1).dropna()
    n = len(d)
    if n < 4:
        return {"n": n, "p": float("nan"), "efeito": float("nan"), "ic": (float("nan"),) * 2}
    rho, p = stats.spearmanr(d.iloc[:, 0], d.iloc[:, 1])
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        s = d.iloc[rng.integers(0, n, n)]
        if s.iloc[:, 0].nunique() > 1 and s.iloc[:, 1].nunique() > 1:
            boots.append(stats.spearmanr(s.iloc[:, 0], s.iloc[:, 1])[0])
    ic = tuple(np.percentile(boots, [2.5, 97.5])) if boots else (float("nan"),) * 2
    return {"n": n, "p": float(p), "efeito": float(rho), "ic": ic}


def kruskal(y: pd.Series, g: pd.Series) -> dict:
    d = pd.concat([y.rename("y"), g.rename("g")], axis=1).dropna()
    grupos = [v["y"].values for _, v in d.groupby("g") if len(v) > 0]
    n = len(d)
    if len(grupos) < 2 or n < 3:
        return {"n": n, "p": float("nan"), "efeito": float("nan"), "H": float("nan")}
    H, p = stats.kruskal(*grupos)
    return {"n": n, "p": float(p), "H": float(H), "efeito": float(H * (n + 1) / (n**2 - 1))}


def dunn(y: pd.Series, g: pd.Series) -> pd.DataFrame:
    """Post hoc de Dunn com correcao de Holm e correcao de empates."""
    d = pd.concat([y.rename("y"), g.rename("g")], axis=1).dropna()
    n = len(d)
    d["r"] = stats.rankdata(d["y"])
    _, cont = np.unique(d["y"], return_counts=True)
    tie = 1 - (cont**3 - cont).sum() / (n**3 - n) if n > 1 else 1
    sigma2 = (n * (n + 1) / 12) * tie
    s = d.groupby("g")["r"].agg(["mean", "count"])
    rows = []
    for a, b in itertools.combinations(s.index, 2):
        se = math.sqrt(sigma2 * (1 / s.loc[a, "count"] + 1 / s.loc[b, "count"]))
        z = (s.loc[a, "mean"] - s.loc[b, "mean"]) / se if se else float("nan")
        rows.append({"grupo_a": a, "grupo_b": b, "z": z, "p": 2 * stats.norm.sf(abs(z))})
    out = pd.DataFrame(rows)
    if not out.empty:
        out["p_holm"] = holm(out["p"].fillna(1).tolist())
    return out


def mannwhitney(y: pd.Series, g: pd.Series, a: str, b: str) -> dict:
    d = pd.concat([y.rename("y"), g.rename("g")], axis=1).dropna()
    xa, xb = d.loc[d.g == a, "y"], d.loc[d.g == b, "y"]
    n1, n2 = len(xa), len(xb)
    if n1 < 2 or n2 < 2:
        return {"n": n1 + n2, "n1": n1, "n2": n2, "p": float("nan"), "efeito": float("nan"), "U": float("nan")}
    U, p = stats.mannwhitneyu(xa, xb, alternative="two-sided")
    return {"n": n1 + n2, "n1": n1, "n2": n2, "U": float(U), "p": float(p), "efeito": float(2 * U / (n1 * n2) - 1)}


def answer_rqs(df: pd.DataFrame, q: dict) -> pd.DataFrame:
    """Executa os testes das QPs a partir do que esta declarado em questionnaire.json."""
    d = add_scores(df, q)
    linhas = []
    for rq in q["research_questions"]:
        t = rq["test"]
        if t == "spearman":
            x = ordinal_codes(q, rq["x"], d[rq["x"]])
            r = spearman(x, d[rq["y"]])
            nome, ef, ef_nome = "Spearman", r["efeito"], "ρ"
            det = f"IC95% bootstrap [{r['ic'][0]:.2f}; {r['ic'][1]:.2f}]"
        elif t == "kruskal":
            r = kruskal(d[rq["y"]], d[rq["group"]])
            nome, ef, ef_nome = "Kruskal-Wallis", r["efeito"], "ε²"
            det = f"H = {r['H']:.2f}"
        else:
            a, b = rq["groups"]
            g = d[rq["group"]]
            if item_map(q)[rq["group"]]["type"] == "multi":
                g = grupo_exclusivo(g, a, b)
            r = mannwhitney(d[rq["y"]], g, a, b)
            nome, ef, ef_nome = "Mann-Whitney", r["efeito"], "r (bisserial por postos)"
            det = f"n = {r['n1']} × {r['n2']}"
        linhas.append({"QP": rq["id"], "teste": nome, "n": r["n"], "p": r["p"], "efeito_nome": ef_nome,
                       "efeito": ef, "detalhe": det,
                       "margem_de_erro_pp": 100 * margin_of_error(0.5, r["n"])})
    out = pd.DataFrame(linhas)
    ps = out["p"].fillna(1).tolist()
    out["p_holm"] = holm(ps)
    out.loc[out["p"].isna(), "p_holm"] = float("nan")
    return out


def diverging(df: pd.DataFrame, q: dict, iids: list[str]) -> pd.DataFrame:
    """Percentuais por item para barras divergentes (neutro centrado em zero)."""
    k = q["likert_scale"]
    mid = (k + 1) / 2
    rows = []
    for iid in iids:
        s = pd.to_numeric(df[iid], errors="coerce").dropna()
        n = len(s)
        if n == 0:
            continue
        pct = {v: 100 * (s == v).sum() / n for v in range(1, k + 1)}
        rows.append({"item": iid, "n": n, **{str(v): pct[v] for v in pct}, "mid": mid})
    return pd.DataFrame(rows)
