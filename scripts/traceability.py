"""Gera a tabela de rastreabilidade (item, QP, metrica, escala) em Markdown."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ESCALAS = {"nominal": "Nominal", "ordinal": "Ordinal", "intervalar": "Intervalar", "razao": "Razão"}


def gerar(path=ROOT / "questionnaire.json"):
    q = json.loads(Path(path).read_text(encoding="utf-8"))
    linhas = ["| Item | Pergunta | QP | Construto | Métrica | Escala |", "|---|---|---|---|---|---|"]
    for it in q["items"]:
        qp = ", ".join(it["rq"]) if it.get("rq") else "—"
        texto = it["text"].replace("|", "\\|")
        linhas.append(
            f"| {it['id']} | {texto} | {qp} | {it.get('construct') or '—'} | {it['metric']} | {ESCALAS[it['scale']]} |"
        )
    return "\n".join(linhas) + "\n"


if __name__ == "__main__":
    sys.stdout.write(gerar(*sys.argv[1:2]))
