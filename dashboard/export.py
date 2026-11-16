"""Gera a planilha (.xlsx) com os dados e os resultados do painel. Sem dados pessoais."""
from __future__ import annotations

import io
from datetime import datetime, timezone

import pandas as pd
from openpyxl.styles import Font

import analysis as an

ESCALAS = {"nominal": "Nominal", "ordinal": "Ordinal", "intervalar": "Intervalar", "razao": "Razão"}


def _naive(s: pd.Series) -> pd.Series:
    """Excel nao aceita fuso horario: grava UTC sem tzinfo."""
    s = pd.to_datetime(s, utc=True)
    return s.dt.tz_convert("UTC").dt.tz_localize(None)


def perfil_long(df: pd.DataFrame, q: dict) -> pd.DataFrame:
    items = an.item_map(q)
    n = len(df)
    linhas = []
    for it in q["items"]:
        if it.get("role") != "profile" or it["id"] not in df:
            continue
        for o in it["options"]:
            if it["type"] == "multi":
                c = int(an.tem_opcao(df[it["id"]], o["value"]).sum())
            else:
                c = int((df[it["id"]] == o["value"]).sum())
            p = c / n if n else float("nan")
            linhas.append({"item": it["id"], "pergunta": items[it["id"]]["text"], "opção": o["label"], "n": c,
                           "%": round(100 * p, 1) if n else None,
                           "± p.p.": round(100 * an.margin_of_error(p, n), 1) if n else None})
    return pd.DataFrame(linhas)


def dicionario(q: dict) -> pd.DataFrame:
    linhas = []
    for it in q["items"]:
        linhas.append({
            "item": it["id"], "pergunta": it["text"], "QP": ", ".join(it.get("rq") or []) or "—",
            "construto": it.get("construct") or "—", "métrica": it["metric"], "escala": ESCALAS[it["scale"]],
            "invertido": "sim" if it.get("reverse") else "",
            "opções": "; ".join(f"{o['value']} = {o['label']}" for o in it.get("options", [])),
        })
    return pd.DataFrame(linhas)


def build_workbook(bruto: pd.DataFrame, todos: pd.DataFrame, filtrado: pd.DataFrame, q: dict,
                   filtros: str = "nenhum", sintetico: bool = False) -> bytes:
    """`todos` = bruto classificado; `filtrado` = amostra valida apos os filtros da barra lateral."""
    validos = todos[todos["valida"]]
    sus = an.flag_near_duplicates(validos, q)

    cols = ["id", "created_at", "form_version", "consent"] + [i["id"] for i in q["items"]] + ["duration_s"]
    raw = bruto[[c for c in cols if c in bruto]].copy()
    raw["created_at"] = _naive(raw["created_at"])

    cls = pd.DataFrame({
        "id": todos["id"].values,
        "created_at": _naive(todos["created_at"]).values,
        "situação": ["válida" if v else "descartada" for v in todos["valida"]],
        "motivo principal": todos["motivo"].values,
        "todos os motivos": ["; ".join(m) for m in todos["motivos"]],
    })
    cls["sinalizada para revisão"] = ["sim" if sus.get(i, False) else "" for i in todos.index]

    sc = an.add_scores(filtrado, q)
    escores = sc[["id"] + [k for k in q["constructs"]]].copy()
    escores.columns = ["id"] + [q["constructs"][k]["label"] for k in q["constructs"]]

    rqs = an.answer_rqs(filtrado, q)
    textos = {r["id"]: r["text"] for r in q["research_questions"]}
    rqs.insert(1, "pergunta", rqs["QP"].map(textos))
    rqs = rqs.rename(columns={"p": "p bruto", "p_holm": "p ajustado (Holm)", "efeito_nome": "medida de efeito",
                              "efeito": "efeito", "detalhe": "detalhe", "margem_de_erro_pp": "margem de erro (± p.p.)"})

    conf = []
    for key, c in q["constructs"].items():
        if len(c["items"]) < 2:
            continue
        r = an.cronbach(filtrado, q, key)
        conf.append({"construto": c["label"], "itens": ", ".join(c["items"]), "n": r["n"],
                     "alfa de Cronbach": round(r["alpha"], 3), "IC95% inferior": round(r["ic"][0], 3),
                     "IC95% superior": round(r["ic"][1], 3), "aceitável (≥ 0,70)": "sim" if r["alpha"] >= 0.7 else "não"})
    conf = pd.DataFrame(conf)

    leia = pd.DataFrame({"Informação": [
        "Gerada em (UTC)", "Versão do questionário", "Respostas recebidas", "Respostas válidas", "Respostas descartadas",
        "Filtros aplicados (abas Escores, QPs, Confiabilidade e Perfil)", "Amostra após os filtros",
        "Abas Respostas e Classificação", "Dados pessoais", "Observação",
    ], "Valor": [
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), q["version"], len(todos), len(validos),
        len(todos) - len(validos), filtros, len(filtrado),
        "sempre com todas as respostas, inclusive as descartadas, sem filtros",
        "nenhum (sem nome, e-mail, IP ou identificador); o campo aberto pode conter texto livre: revise antes de divulgar",
        "DADOS SINTÉTICOS DE DESENVOLVIMENTO: não representam coleta real" if sintetico else "dados da coleta",
    ]})

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl", datetime_format="yyyy-mm-dd hh:mm:ss") as xw:
        abas = [("Leia-me", leia), ("Respostas", raw), ("Classificação", cls), ("Escores", escores),
                ("QPs", rqs), ("Confiabilidade", conf), ("Perfil", perfil_long(filtrado, q)),
                ("Dicionário", dicionario(q))]
        for nome, d in abas:
            d.to_excel(xw, sheet_name=nome, index=False)
            ws = xw.sheets[nome]
            ws.freeze_panes = "A2"
            for cell in ws[1]:
                cell.font = Font(bold=True)
            for col in ws.columns:
                largura = max((len(str(c.value)) for c in col[:200] if c.value is not None), default=8)
                ws.column_dimensions[col[0].column_letter].width = min(max(10, largura + 2), 70)
    return buf.getvalue()
