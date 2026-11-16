"""Conteudo da apresentacao: os mesmos slides alimentam a pagina do painel e o HTML estatico (offline)."""
from __future__ import annotations

import html
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go

import analysis as an
import charts
import monitor

LIMITACOES = [
    "Amostra não probabilística (conveniência e bola de neve): os resultados descrevem quem respondeu e não podem ser generalizados.",
    "Confiança e dependência são percepções autorrelatadas, não medem desempenho real.",
    "Desejabilidade social: estudantes podem subestimar o uso de IA; a política dos professores (Q8) ajuda a interpretar.",
    "Survey observa associações, nunca causas.",
    "Anonimato impede bloquear totalmente respostas repetidas; duplicatas evidentes são descartadas e quase-duplicatas são revisadas.",
    "Amostra pequena e três testes: usamos testes não paramétricos, tamanho de efeito e correção de Holm.",
]


def magnitude(nome: str, valor: float) -> str:
    v = abs(valor)
    if nome.startswith("ε"):
        return "fraco" if v < 0.04 else "moderado" if v < 0.16 else "forte"
    return "desprezível" if v < 0.1 else "pequeno" if v < 0.3 else "médio" if v < 0.5 else "grande"


def _p(p: float) -> str:
    """Devolve ' < 0,001' ou ' = 0,012' (ja com o operador)."""
    return " —" if pd.isna(p) else (" < 0,001" if p < 0.001 else f" = {p:.3f}".replace(".", ","))


def _f(x: float, d: int = 2) -> str:
    return "—" if pd.isna(x) else f"{x:.{d}f}".replace(".", ",")


def narrativa(r: pd.Series, rq: dict, q: dict, sc: pd.DataFrame, posthoc: pd.DataFrame | None) -> str:
    """Texto em portugues simples. Nunca afirma causalidade; respeita o p ajustado (Holm)."""
    if r["n"] < 4 or pd.isna(r["p"]):
        return "Ainda não há respostas suficientes para este teste."
    sig = r["p_holm"] < 0.05
    mag = magnitude(r["efeito_nome"], r["efeito"])
    partes = []
    if rq["test"] == "spearman":
        sentido = "menor" if r["efeito"] < 0 else "maior"
        partes.append(f"{'Há' if sig else 'Não encontramos'} associação estatisticamente significativa entre a "
                      f"frequência de uso de IA e a confiança em programar sem ela" + (
                          f": quanto maior a frequência de uso, {sentido} a confiança (ρ = {_f(r['efeito'])}, efeito {mag})." if sig else
                          f" (ρ = {_f(r['efeito'])}, efeito {mag})."))
    elif rq["test"] == "kruskal":
        med = sc.groupby(rq["group"])[rq["y"]].median()
        txt = "; ".join(f"{charts.rotulo(q, rq['group'], k)}: mediana {_f(v)}" for k, v in med.items())
        partes.append(f"{'Há' if sig else 'Não encontramos'} diferença significativa na dependência percebida entre os períodos do curso "
                      f"(ε² = {_f(r['efeito'])}, efeito {mag}). Medianas: {txt}.")
        if sig and posthoc is not None and not posthoc.empty:
            pares = posthoc[posthoc["p_holm"] < 0.05]
            if len(pares):
                partes.append("Pares que diferem (Dunn, Holm): " + "; ".join(f"{a} × {b}" for a, b in zip(pares["grupo_a"], pares["grupo_b"])) + ".")
    else:
        direcao = "mais" if r["efeito"] > 0 else "menos"
        partes.append(f"{'Há' if sig else 'Não encontramos'} diferença significativa de confiança entre quem usa IA só para gerar código e "
                      f"quem a usa só para tirar dúvidas" + (f": o primeiro grupo tem {direcao} confiança (r = {_f(r['efeito'])}, efeito {mag})." if sig
                                                              else f" (r = {_f(r['efeito'])}, efeito {mag})."))
    partes.append(f"Teste: {r['teste']}; p bruto{_p(r['p'])}; p ajustado (Holm){_p(r['p_holm'])}; n = {int(r['n'])}; "
                  f"margem de erro ≈ ±{_f(r['margem_de_erro_pp'], 1)} p.p. Isto indica associação, não causalidade.")
    if r["n"] < monitor.MINIMO:
        partes.append(f"Atenção: n abaixo do mínimo planejado ({monitor.MINIMO}).")
    return " ".join(partes)


def build_slides(bruto: pd.DataFrame, q: dict, sintetico: bool = False) -> list[dict]:
    todos = an.classify(bruto, q)
    validos = todos[todos["valida"]]
    sc = an.add_scores(validos, q)
    res = an.answer_rqs(validos, q).set_index("QP")
    n, nt = len(validos), len(todos)
    slides: list[dict] = []

    aviso = "DADOS SINTÉTICOS DE DESENVOLVIMENTO: não representam coleta real." if sintetico else ""
    slides.append({"titulo": q["title"], "texto": f"Survey pré-registrado · {n} respostas válidas de {nt} recebidas. {aviso}".strip(), "fig": None, "capa": True})

    mot = pd.Series([m for ms in todos[~todos["valida"]]["motivos"] for m in ms]).value_counts() if nt > n else pd.Series(dtype=int)
    slides.append({"titulo": "Quem respondeu", "fig": charts.fig_bars(mot, "Motivos de descarte") if len(mot) else None,
                   "texto": f"{nt} respostas recebidas, {n} válidas e {nt - n} descartadas. Margem de erro de uma proporção, no pior caso, "
                            f"≈ ±{_f(100 * an.margin_of_error(0.5, n), 1) if n else '—'} p.p. (e = 1,96 × √(p(1−p)/n)). Amostra não probabilística: a margem é indicativa."})

    if n:
        a = validos["Q3"].map(lambda v: charts.rotulo(q, "Q3", v)).value_counts()
        b = validos["Q6"].map(lambda v: charts.rotulo(q, "Q6", v)).value_counts()
        slides.append({"titulo": "Perfil da amostra", "texto": "Período do curso e frequência de uso de IA nos estudos.",
                       "fig": charts.fig_dupla_barras(a, "Período do curso", b, "Frequência de uso")})
        fig = charts.fig_diverging(validos, q, q["constructs"]["confianca"]["items"] + q["constructs"]["dependencia"]["items"])
        slides.append({"titulo": "Confiança e dependência", "fig": fig,
                       "texto": "Itens Likert de 5 pontos (Q10–Q13 confiança em programar sem IA; Q14–Q17 dependência, com Q17 invertido nos escores)."})

    for rq in q["research_questions"]:
        if rq["id"] not in res.index:
            continue
        r = res.loc[rq["id"]].copy(); r["QP"] = rq["id"]
        ph = None
        fig = None
        if n:
            if rq["test"] == "kruskal":
                ph = an.dunn(sc[rq["y"]], sc[rq["group"]])
                if not ph.empty:
                    ph["grupo_a"] = ph["grupo_a"].map(lambda v: charts.rotulo(q, rq["group"], v))
                    ph["grupo_b"] = ph["grupo_b"].map(lambda v: charts.rotulo(q, rq["group"], v))
            if rq["test"] == "spearman":
                dd = sc.dropna(subset=[rq["x"], rq["y"]]).assign(frequência=lambda d: d[rq["x"]].map(lambda v: charts.rotulo(q, rq["x"], v)))
                ordem = [o["label"] for o in an.item_map(q)[rq["x"]]["options"]]
                fig = charts.fig_box(dd, "frequência", rq["y"], "Confiança (escore médio)", ordem)
            else:
                g = rq["group"]
                dd = sc.dropna(subset=[g, rq["y"]])
                ordem = [o["label"] for o in an.item_map(q)[g]["options"]]
                if rq["test"] == "mannwhitney":
                    ordem = ["só " + x.replace("_", " ") for x in rq["groups"]]
                    dd = dd.assign(grupo=an.grupo_exclusivo(dd[g], *rq["groups"]).map(lambda v: "só " + str(v).replace("_", " "))).dropna(subset=["grupo"])
                    dd = dd[dd["grupo"].isin(["só " + x.replace("_", " ") for x in rq["groups"]])]
                else:
                    dd = dd.assign(grupo=dd[g].map(lambda v: charts.rotulo(q, g, v)))
                fig = charts.fig_box(dd, "grupo", rq["y"], "Escore médio", ordem)
        slides.append({"titulo": f"{rq['id']}: {rq['text']}", "texto": narrativa(r, rq, q, sc, ph), "fig": fig})

    if n:
        linhas = []
        for key, c in q["constructs"].items():
            if len(c["items"]) > 1:
                rr = an.cronbach(validos, q, key)
                linhas.append(f"{c['label']}: α = {_f(rr['alpha'], 2)} ({'aceitável' if rr['alpha'] >= 0.7 else 'abaixo de 0,70'})")
        slides.append({"titulo": "Confiabilidade dos construtos", "fig": None, "texto": "Alfa de Cronbach. " + "; ".join(linhas) + "."})

    slides.append({"titulo": "Limitações", "fig": None, "lista": LIMITACOES, "texto": ""})
    slides.append({"titulo": "Obrigado", "fig": None, "texto": "Dados, código e protocolo estão no repositório do grupo.", "capa": True})
    return slides


CSS = """:root{--bg:#f5f0e4;--ink:#1d1b16;--muted:#6a6356;--line:#ddd4c1;--accent:#9a5b00}
@media(prefers-color-scheme:dark){:root{--bg:#16151a;--ink:#ece8df;--muted:#8d8a93;--line:#2b2a31;--accent:#e3b04b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI",sans-serif}
.slide{display:none;min-height:100vh;padding:5vh 7vw 9vh;flex-direction:column;justify-content:center;max-width:1200px;margin:0 auto}.slide.on{display:flex}
h1{font-size:clamp(1.6rem,3.2vw,2.6rem);font-weight:500;line-height:1.2;margin:0 0 .8em}.capa h1{font-size:clamp(2rem,5vw,3.6rem)}
p,li{font-size:clamp(1rem,1.7vw,1.35rem);line-height:1.55;color:var(--muted);max-width:60em}li{margin:.5em 0}.fig{margin:1em 0;width:100%;overflow:hidden}.slide>*{min-width:0;max-width:100%}.js-plotly-plot,.plotly-graph-div{width:100%!important}
nav{position:fixed;left:0;right:0;bottom:0;display:flex;justify-content:space-between;align-items:center;padding:.8rem 1.4rem;background:var(--bg);border-top:1px solid var(--line);color:var(--muted);font-size:.95rem}
button{font:inherit;color:var(--ink);background:transparent;border:1px solid var(--muted);border-radius:8px;padding:.4rem 1rem;cursor:pointer}
.bar{position:fixed;top:0;left:0;height:3px;background:var(--accent);width:0}"""

JS = """const S=[...document.querySelectorAll('.slide')];let i=0;
function go(n){i=Math.max(0,Math.min(S.length-1,n));S.forEach((s,k)=>s.classList.toggle('on',k===i));
document.getElementById('c').textContent=(i+1)+' / '+S.length;document.querySelector('.bar').style.width=((i+1)/S.length*100)+'%';
window.dispatchEvent(new Event('resize'))}
document.addEventListener('keydown',e=>{if(['ArrowRight','PageDown',' '].includes(e.key)){e.preventDefault();go(i+1)}
if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();go(i-1)}if(e.key==='Home')go(0);if(e.key==='End')go(S.length-1)});
document.getElementById('prev').onclick=()=>go(i-1);document.getElementById('next').onclick=()=>go(i+1);go(0);"""


def build_html(slides: list[dict], sintetico: bool = False) -> str:
    """HTML autonomo (Plotly embutido) que abre offline. Setas, espaco e botoes navegam."""
    secoes, primeiro = [], True
    for s in slides:
        corpo = f"<h1>{html.escape(s['titulo'])}</h1>"
        if s.get("texto"):
            corpo += f"<p>{html.escape(s['texto'])}</p>"
        if s.get("lista"):
            corpo += "<ul>" + "".join(f"<li>{html.escape(x)}</li>" for x in s["lista"]) + "</ul>"
        if s.get("fig") is not None:
            fig: go.Figure = s["fig"]
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=15))
            corpo += '<div class="fig">' + fig.to_html(full_html=False, include_plotlyjs="inline" if primeiro else False,
                                                      config={"displayModeBar": False}) + "</div>"
            primeiro = False
        secoes.append(f'<section class="slide{" capa" if s.get("capa") else ""}">{corpo}</section>')
    gerado = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    aviso = " · DADOS SINTÉTICOS" if sintetico else ""
    return (f'<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>Apresentação do survey</title><style>{CSS}</style><body><div class=\"bar\"></div>{''.join(secoes)}"
            f'<nav><span>Gerado em {gerado}{aviso}</span><span><button id="prev">←</button> <span id="c"></span> <button id="next">→</button></span></nav>'
            f"<script>{JS}</script></body></html>")
