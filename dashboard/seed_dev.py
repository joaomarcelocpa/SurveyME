"""Gera dados SINTETICOS para testar o dashboard localmente.

Nao representam coleta real e nunca devem ir ao banco de producao.
Por padrao grava em dashboard/data/seed_dev.csv. Com --db insere em `responses_dev`
(usa DATABASE_URL_DEV; a tabela `responses` nunca e tocada).
"""
from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from analysis import load_questionnaire, item_map, normalize_answers

OUT = Path(__file__).resolve().parent / "data" / "seed_dev.csv"


def gerar(n: int = 80, seed: int = 7) -> list[dict]:
    q = load_questionnaire()
    it = item_map(q)
    rng = np.random.default_rng(seed)
    t0 = datetime(2026, 11, 13, 9, tzinfo=timezone.utc)
    rows = []
    for i in range(n):
        freq = int(rng.integers(0, 5))
        periodo = rng.choice(["1-4", "5-8", "9+"], p=[0.4, 0.4, 0.2])
        usos = [u for u, pr in (("gerar_codigo", 0.35), ("duvidas", 0.55), ("corrigir_erros", 0.45), ("gerar_testes", 0.15), ("outro", 0.05)) if rng.random() < pr] or ["duvidas"]
        conf_base = 3.8 - 0.35 * freq - (0.4 if "gerar_codigo" in usos else 0)
        dep_base = 3.0 + (0.3 if periodo == "1-4" else -0.1)

        def lk(base):
            return int(np.clip(round(rng.normal(base, 0.9)), 1, 5))

        a = {
            "Q1": "sim", "Q2": "sim", "Q3": str(periodo),
            "Q4": rng.choice(["sim", "nao"]), "Q5": rng.choice(["<1", "1-2", "3-5", ">5"]),
            "Q6": it["Q6"]["options"][freq]["value"],
            "Q7": list(rng.choice(["chatgpt", "copilot", "claude", "gemini", "outra"], size=int(rng.integers(1, 4)), replace=False)),
            "Q8": rng.choice([o["value"] for o in it["Q8"]["options"]]), "Q9": usos,
            "_dev": True,
        }
        for c in ("Q10", "Q11", "Q12", "Q13"):
            a[c] = lk(conf_base)
        for c in ("Q14", "Q15", "Q16"):
            a[c] = lk(dep_base)
        a["Q17"] = lk(6 - dep_base)
        a["Q18"] = 1
        a["duration_s"] = int(rng.integers(150, 600))
        a = {k: (v.item() if hasattr(v, "item") else v) for k, v in a.items()}
        # casos para exercitar os descartes
        if i % 17 == 3:
            a["Q18"] = 4
        elif i % 19 == 5:
            a["duration_s"] = 25
        elif i % 23 == 7:
            a["Q1"] = "nao"
        elif i % 29 == 11:
            del a["Q13"]
        rows.append({"id": str(uuid.uuid4()), "created_at": t0 + timedelta(minutes=37 * i),
                     "form_version": q["version"], "consent": True, "answers": a})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=80)
    ap.add_argument("--db", action="store_true", help="insere em responses_dev (DATABASE_URL_DEV)")
    args = ap.parse_args()
    rows = gerar(args.n)
    if args.db:
        import psycopg
        url = os.environ["DATABASE_URL_DEV"]
        with psycopg.connect(url) as con, con.cursor() as cur:
            for r in rows:
                cur.execute(
                    "insert into responses_dev (id, created_at, form_version, consent, answers) values (%s,%s,%s,%s,%s)",
                    (r["id"], r["created_at"], r["form_version"], r["consent"], json.dumps(r["answers"])),
                )
        print(f"{len(rows)} linhas sinteticas em responses_dev")
        return
    from analysis import rows_to_df
    OUT.parent.mkdir(exist_ok=True)
    rows_to_df(rows).to_csv(OUT, index=False)
    print(f"{len(rows)} linhas sinteticas em {OUT}")


if __name__ == "__main__":
    main()
