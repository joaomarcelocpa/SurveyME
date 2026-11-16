"""Figuras Plotly compartilhadas pelo painel e pela apresentacao estatica."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import analysis as an

CORES = {"1": "#b2182b", "2": "#ef8a62", "3": "#cfcfcf", "4": "#67a9cf", "5": "#2166ac"}


def rotulo(q: dict, iid: str, v) -> str:
    for o in an.item_map(q)[iid].get("options", []):
        if o["value"] == v:
            return o["label"]
    return str(v)


def fig_diverging(df: pd.DataFrame, q: dict, iids: list[str]) -> go.Figure | None:
    d = an.diverging(df, q, iids)
    if d.empty:
        return None
    escala = an.item_map(q)[iids[0]]["options"]
    fig = go.Figure()
    for v in ["1", "2", "3", "4", "5"]:
        if v == "3":
            base, largura = -d["3"] / 2, d["3"]
        elif v in ("1", "2"):
            off = d["3"] / 2 + (d["2"] if v == "1" else 0)
            base, largura = -(off + d[v]), d[v]
        else:
            off = d["3"] / 2 + (d["4"] if v == "5" else 0)
            base, largura = off, d[v]
        nome = next(o["label"] for o in escala if str(o["value"]) == v)
        fig.add_bar(y=d["item"], x=largura, base=base, orientation="h", name=nome, marker_color=CORES[v],
                    customdata=d[v], hovertemplate="%{y}: %{customdata:.0f}%<extra>" + nome + "</extra>")
    fig.update_layout(barmode="overlay", xaxis_title="% de respostas", yaxis=dict(autorange="reversed"),
                      height=70 + 55 * len(d), legend_orientation="h", margin=dict(l=10, r=10, t=10, b=10))
    fig.add_vline(x=0, line_color="#444")
    return fig


def fig_box(dd: pd.DataFrame, x: str, y: str, titulo_y: str, ordem: list[str] | None = None) -> go.Figure:
    fig = px.box(dd, x=x, y=y, points="all", labels={y: titulo_y}, category_orders={x: ordem} if ordem else None)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=380)
    return fig


def fig_bars(contagens: pd.Series, titulo: str = "") -> go.Figure:
    fig = go.Figure(go.Bar(x=list(contagens.index), y=list(contagens.values), marker_color="#4a5565"))
    fig.update_layout(margin=dict(l=10, r=10, t=30 if titulo else 10, b=10), height=330, title=titulo or None,
                      yaxis_title="respostas")
    return fig


def fig_dupla_barras(a: pd.Series, ta: str, b: pd.Series, tb: str) -> go.Figure:
    fig = make_subplots(rows=1, cols=2, subplot_titles=(ta, tb))
    fig.add_trace(go.Bar(x=list(a.index), y=list(a.values), marker_color="#4a5565", showlegend=False), row=1, col=1)
    fig.add_trace(go.Bar(x=list(b.index), y=list(b.values), marker_color="#9a5b00", showlegend=False), row=1, col=2)
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=340)
    return fig
