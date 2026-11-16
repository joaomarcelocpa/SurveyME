from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import analysis as an
from data_source import load_raw
from export import build_workbook
import charts
import monitor
import presentation

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from envfile import load_env  # noqa: E402

load_env(Path(__file__).resolve().parent / ".env")  # DATABASE_URL_RO etc., sem precisar exportar
st.set_page_config(page_title="Survey: IA no aprendizado de programação", layout="wide")
q = an.load_questionnaire()
items = an.item_map(q)

PERFIL = ["Q3", "Q4", "Q5", "Q6", "Q8", "Q9", "Q19"]


def rotulo(iid: str, v) -> str:
    for o in items[iid].get("options", []):
        if o["value"] == v:
            return o["label"]
    return str(v)


@st.cache_data(ttl=60)
def carregar() -> pd.DataFrame:
    return load_raw()


def pagina_metodologia():
    st.title("Metodologia e desvios")
    st.markdown(
        "- **Testes:** Spearman (QP1), Kruskal-Wallis com Dunn (QP2), Mann-Whitney (QP3), escolhidos por serem ordinais as escalas.\n"
        "- **Múltiplas comparações:** correção de Holm sobre as três QPs e sobre os post hoc; p bruto e ajustado são mostrados.\n"
        "- **Margem de erro:** e = 1,96 × √(p(1−p)/n), com p = 0,5 (pior caso). Amostra não probabilística: margem indicativa.\n"
        "- **Descartes:** calculados na análise, com motivo; nenhuma resposta é apagada do banco."
    )
    st.divider()
    f = ROOT / "deviations.md"
    st.markdown(f.read_text(encoding="utf-8") if f.exists() else "_Nenhum desvio registrado._")
    st.divider()
    st.subheader("Rastreabilidade")
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from traceability import gerar
    st.markdown(gerar())


def barras_divergentes(df: pd.DataFrame, iids: list[str]):
    fig = charts.fig_diverging(df, q, iids)
    if fig is None:
        st.info("Sem dados.")
        return
    st.plotly_chart(fig, width="stretch")


def pagina_painel():
    st.title("Assistentes de IA no aprendizado de programação")
    try:
        bruto = carregar()
    except Exception as e:  # noqa: BLE001
        st.error(f"Não foi possível ler os dados: {type(e).__name__}")
        return
    if bruto.empty:
        st.info("Ainda não há respostas.")
        return
    if os.environ.get("SURVEY_TABLE") == "responses_dev" or "_dev" in bruto.columns:
        st.warning("DADOS SINTÉTICOS DE DESENVOLVIMENTO. Não representam coleta real.")

    todos = an.classify(bruto, q)
    validos = todos[todos["valida"]]

    # ----- filtros
    st.sidebar.header("Filtros (amostra válida)")
    filtrado = validos
    for iid in PERFIL:
        multi = items[iid]["type"] == "multi"
        if multi:
            ops = [o["value"] for o in items[iid]["options"] if an.tem_opcao(validos[iid], o["value"]).any()]
        else:
            ops = [o["value"] for o in items[iid]["options"] if o["value"] in set(validos[iid].dropna())]
        esc = st.sidebar.multiselect(items[iid]["text"], ops, format_func=lambda v, i=iid: rotulo(i, v), key="f_" + iid)
        if esc:
            if multi:  # basta ter marcado qualquer uma das opcoes escolhidas
                mask = pd.concat([an.tem_opcao(filtrado[iid], v) for v in esc], axis=1).any(axis=1)
                filtrado = filtrado[mask]
            else:
                filtrado = filtrado[filtrado[iid].isin(esc)]
    st.sidebar.caption(f"{len(filtrado)} de {len(validos)} respostas válidas após filtros.")

    min_n = q["min_duration_seconds"]
    t1, t2, t3, t4, t5 = st.tabs(["Perfil da amostra", "Itens Likert", "Questões de pesquisa", "Confiabilidade", "Exportação"])

    with t1:
        c1, c2, c3 = st.columns(3)
        c1.metric("Recebidas", len(todos))
        c2.metric("Válidas", len(validos))
        c3.metric("Descartadas", len(todos) - len(validos))
        desc = todos[~todos["valida"]]
        if len(desc):
            mot = pd.Series([m for ms in desc["motivos"] for m in ms]).value_counts().rename("ocorrências").to_frame()
            mot["descartadas (motivo principal)"] = desc["motivo"].value_counts()
            st.subheader("Motivos de descarte")
            st.dataframe(mot.fillna(0).astype(int))
            st.caption(f"Uma resposta pode ter mais de um motivo; o principal segue a ordem da tabela. Tempo mínimo: {min_n} s.")
        sus = validos[an.flag_near_duplicates(validos, q)]
        if len(sus):
            st.subheader("Sinalizadas para revisão (não descartadas)")
            st.caption("Respostas válidas quase iguais a outra enviada pouco antes (mesmo perfil, escalas com diferença total de até 2 pontos, em até 60 min). Revise e, se confirmar duplicidade, registre em deviations.md.")
            st.dataframe(sus[["id", "created_at"]], hide_index=True)
        st.subheader("Perfil (amostra filtrada)")
        n = len(filtrado)
        for iid in PERFIL:
            if items[iid]["type"] == "multi":  # cada pessoa pode marcar varias: soma passa de 100%
                cont = pd.Series({o["value"]: int(an.tem_opcao(filtrado[iid], o["value"]).sum()) for o in items[iid]["options"]})
                cont = cont[cont > 0].sort_values(ascending=False)
            else:
                cont = filtrado[iid].value_counts()
            tab = pd.DataFrame({"opção": [rotulo(iid, v) for v in cont.index], "n": cont.values,
                                "%": (100 * cont.values / n).round(1) if n else 0,
                                "± p.p.": [round(100 * an.margin_of_error(c / n, n), 1) for c in cont.values] if n else 0})
            with st.expander(items[iid]["text"], expanded=iid in ("Q3", "Q6")):
                st.dataframe(tab, hide_index=True)
                if items[iid]["type"] == "multi":
                    st.caption("Múltipla escolha: a soma dos percentuais pode passar de 100%.")

    with t2:
        st.caption("Itens de confiança e dependência (amostra filtrada). Q17 aparece como respondido, sem inversão.")
        for key, c in q["constructs"].items():
            st.subheader(c["label"])
            barras_divergentes(filtrado, c["items"])
        with st.expander("Texto dos itens"):
            for key, c in q["constructs"].items():
                for iid in c["items"]:
                    st.write(f"**{iid}**: {items[iid]['text']}" + (" _(invertido)_" if items[iid].get("reverse") else ""))

    with t3:
        res = an.answer_rqs(filtrado, q)
        st.caption("α = 0,05. Testes não paramétricos; p ajustado por Holm sobre as três QPs. "
                   "Margem de erro: e = 1,96 × √(p(1−p)/n), com p = 0,5 e n do teste. Resultados indicam associação, não causalidade.")
        for _, r in res.iterrows():
            rq = next(x for x in q["research_questions"] if x["id"] == r["QP"])
            st.subheader(f"{r['QP']}: {rq['text']}")
            a, b, c, d, e = st.columns(5)
            a.metric("Teste", r["teste"])
            b.metric("n", int(r["n"]))
            c.metric("p bruto / ajustado", "—" if pd.isna(r["p"]) else f"{r['p']:.4f} / {r['p_holm']:.4f}")
            d.metric(f"Efeito ({r['efeito_nome']})", "—" if pd.isna(r["efeito"]) else f"{r['efeito']:.2f}")
            e.metric("Margem de erro", f"± {r['margem_de_erro_pp']:.1f} p.p.")
            st.caption(r["detalhe"])
            if r["teste"] == "Kruskal-Wallis":
                sc = an.add_scores(filtrado, q)
                ph = an.dunn(sc[rq["y"]], sc[rq["group"]])
                if not ph.empty:
                    ph["grupo_a"] = ph["grupo_a"].map(lambda v: rotulo(rq["group"], v))
                    ph["grupo_b"] = ph["grupo_b"].map(lambda v: rotulo(rq["group"], v))
                    st.write("Post hoc de Dunn (Holm):")
                    st.dataframe(ph, hide_index=True)
            if r["teste"] != "Spearman":
                sc = an.add_scores(filtrado, q)
                g = rq["group"]
                dd = sc.dropna(subset=[g, rq["y"]])
                if "groups" in rq:
                    dd = dd[dd[g].isin(rq["groups"])]
                dd = dd.assign(grupo=dd[g].map(lambda v: rotulo(g, v)))
                st.plotly_chart(px.box(dd, x="grupo", y=rq["y"], points="all"), width="stretch")
            else:
                sc = an.add_scores(filtrado, q)
                dd = sc.assign(frequencia=an.ordinal_codes(q, rq["x"], sc[rq["x"]]))
                st.plotly_chart(px.box(dd, x="frequencia", y=rq["y"], points="all"), width="stretch")

    with t4:
        linhas = []
        for key, c in q["constructs"].items():
            if len(c["items"]) < 2:
                continue
            r = an.cronbach(filtrado, q, key)
            linhas.append({"construto": c["label"], "itens": ", ".join(c["items"]), "n": r["n"],
                           "α": round(r["alpha"], 3), "IC95%": f"[{r['ic'][0]:.2f}; {r['ic'][1]:.2f}]",
                           "aceitável (≥ 0,70)": "sim" if r["alpha"] >= 0.7 else "não"})
            sem = {k: round(v, 3) for k, v in r["sem_item"].items()}
            linhas[-1]["α sem cada item"] = ", ".join(f"{k}: {v}" for k, v in sem.items())
        st.dataframe(pd.DataFrame(linhas), hide_index=True)

    with t5:
        raw = bruto.copy()
        raw["created_at"] = raw["created_at"].dt.strftime("%Y-%m-%d %H:%M:%S%z")
        cols = ["id", "created_at", "form_version", "consent"] + [i["id"] for i in q["items"]] + ["duration_s"]
        raw = raw[[c for c in cols if c in raw]]
        st.write("CSV bruto (todas as respostas, inclusive as descartadas, sem dados pessoais).")
        st.download_button("Baixar CSV bruto", raw.to_csv(index=False).encode("utf-8"), "respostas_brutas.csv", "text/csv")
        st.divider()
        st.write("Planilha (.xlsx) com respostas, classificação dos descartes, escores, resultados das QPs, confiabilidade, perfil e dicionário. "
                 "As abas de análise seguem os filtros da barra lateral; as abas Respostas e Classificação trazem tudo.")
        filtros_txt = "; ".join(f"{items[i]['text']}: {', '.join(rotulo(i, v) for v in st.session_state.get('f_' + i, []))}"
                                for i in PERFIL if st.session_state.get("f_" + i)) or "nenhum"
        sint = os.environ.get("SURVEY_TABLE") == "responses_dev" or "_dev" in bruto.columns
        try:
            xlsx = build_workbook(bruto, todos, filtrado, q, filtros_txt, sint)
            st.download_button("Baixar planilha (.xlsx)", xlsx, "survey_resultados.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:  # noqa: BLE001
            st.error(f"Não foi possível gerar a planilha: {type(e).__name__}")


def _fonte_db() -> bool:
    return not os.environ.get("SURVEY_SOURCE", "db").startswith("csv:")


def _sintetico(bruto: pd.DataFrame) -> bool:
    return os.environ.get("SURVEY_TABLE") == "responses_dev" or "_dev" in bruto.columns or not _fonte_db()


def pagina_apresentacao():
    st.title("Apresentação")
    try:
        bruto = carregar()
    except Exception as e:  # noqa: BLE001
        st.error(f"Não foi possível ler os dados: {type(e).__name__}")
        return
    if bruto.empty:
        st.info("Ainda não há respostas.")
        return
    sint = _sintetico(bruto)
    slides = presentation.build_slides(bruto, q, sint)
    if sint:
        st.warning("DADOS SINTÉTICOS DE DESENVOLVIMENTO. Não representam coleta real.")
    i = st.session_state.setdefault("slide", 0)
    i = max(0, min(i, len(slides) - 1))
    c1, c2, c3 = st.columns([1, 6, 1])
    if c1.button("← Anterior", disabled=i == 0):
        st.session_state["slide"] = i - 1
        st.rerun()
    if c3.button("Próximo →", disabled=i == len(slides) - 1):
        st.session_state["slide"] = i + 1
        st.rerun()
    c2.progress((i + 1) / len(slides), text=f"Slide {i + 1} de {len(slides)}")
    sl = slides[i]
    st.header(sl["titulo"])
    if sl.get("texto"):
        st.markdown(f"<p style='font-size:1.25rem'>{sl['texto']}</p>", unsafe_allow_html=True)
    for item in sl.get("lista", []):
        st.markdown(f"- {item}")
    if sl.get("fig") is not None:
        st.plotly_chart(sl["fig"], width="stretch")
    st.divider()
    st.download_button("Baixar versão offline (HTML)", presentation.build_html(slides, sint).encode("utf-8"),
                       "apresentacao_survey.html", "text/html",
                       help="Abre em qualquer navegador, sem internet e sem banco. Use as setas para navegar.")


@st.fragment(run_every=60)
def _monitor_corpo():
    try:
        bruto = carregar()
    except Exception as e:  # noqa: BLE001
        st.error(f"Não foi possível ler os dados: {type(e).__name__}")
        return
    if bruto.empty:
        st.info("Ainda não há respostas.")
        return
    if _sintetico(bruto):
        st.warning("DADOS SINTÉTICOS DE DESENVOLVIMENTO. Não representam coleta real.")
    todos = an.classify(bruto, q)
    validos = todos[todos["valida"]]
    ultima = monitor.local(todos["created_at"]).max()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Recebidas", len(todos))
    c2.metric("Válidas", len(validos), help=f"Meta {monitor.META}; mínimo {monitor.MINIMO} válidas (protocolo).")
    c3.metric("Taxa de descarte", f"{100 * (1 - len(validos) / len(todos)):.0f}%")
    c4.metric("Última resposta", ultima.strftime("%d/%m %H:%M"))
    st.progress(min(1.0, len(validos) / monitor.META), text=f"{len(validos)} de {monitor.META} (mínimo {monitor.MINIMO})")
    if len(validos) < monitor.MINIMO:
        st.caption(f"Faltam {monitor.MINIMO - len(validos)} respostas válidas para o mínimo do protocolo.")

    ac = monitor.acumulado(todos)
    fig = go.Figure()
    fig.add_scatter(x=ac["hora"], y=ac["recebidas"], name="recebidas", mode="lines")
    fig.add_scatter(x=ac["hora"], y=ac["válidas"], name="válidas", mode="lines")
    fig.add_hline(y=monitor.META, line_dash="dot", annotation_text="meta")
    fig.add_hline(y=monitor.MINIMO, line_dash="dot", annotation_text="mínimo")
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="acumulado", legend_orientation="h")
    st.subheader("Evolução")
    st.plotly_chart(fig, width="stretch")
    st.plotly_chart(go.Figure(go.Bar(x=ac["hora"], y=ac["novas na hora"])).update_layout(
        height=220, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="respostas por hora"), width="stretch")

    ra = monitor.rajadas(todos)
    if len(ra):
        st.warning(f"{len(ra)} rajada(s): 5 ou mais respostas em até 5 minutos. Pode ser compartilhamento em massa ou automação.")
        st.dataframe(ra, hide_index=True)

    colA, colB = st.columns(2)
    with colA:
        st.subheader("Descartes")
        desc = todos[~todos["valida"]]
        if len(desc):
            st.dataframe(desc["motivo"].value_counts().rename("respostas").to_frame())
        else:
            st.caption("Nenhuma resposta descartada.")
        du = monitor.duracao(todos, q["min_duration_seconds"])
        if du["mediana"] is not None:
            st.caption(f"Tempo de preenchimento: mediana {du['mediana'] / 60:.1f} min (p10 {du['p10'] / 60:.1f}, p90 {du['p90'] / 60:.1f}); "
                       f"{du['abaixo_minimo']} abaixo de {q['min_duration_seconds']} s.")
        sus = an.flag_near_duplicates(validos, q).sum()
        if sus:
            st.caption(f"{int(sus)} resposta(s) válida(s) sinalizada(s) como quase-duplicata (revisar no painel).")
        st.caption("Versões do questionário: " + ", ".join(f"{k} ({v})" for k, v in todos["form_version"].value_counts().items()))
    with colB:
        st.subheader("Cobertura por grupo")
        cob = monitor.cobertura(validos, q)
        st.dataframe(cob, hide_index=True)
        st.caption(f"Grupos com menos de {monitor.COBERTURA_MIN} respostas válidas deixam a QP sem poder de detecção.")

    st.subheader("Saúde dos dados")
    if not _fonte_db():
        st.caption("Fonte CSV: verificações do banco indisponíveis.")
        return
    url = os.environ.get("DATABASE_URL_RO", "")
    tabela = os.environ.get("SURVEY_TABLE", "responses")
    h = monitor.saude_banco(url, tabela)
    if not h["ok"]:
        st.error(f"Banco inacessível ({h['erro']}).")
    else:
        st.success(f"Banco ok: {h['latencia_ms']} ms, {h['total']} respostas.")
        if tabela == "responses":
            if not h["travas_ok"]:
                st.error("Travas de imutabilidade AUSENTES na tabela de respostas. Reaplique db/migrations/002_imutabilidade.sql.")
            if h["usuario_pode_escrever"]:
                st.error("O usuário do painel tem permissão de escrita. Use o usuário somente leitura (survey_ro).")
    estado = monitor.estado_backup(len(todos))
    if not estado["existe"]:
        st.warning(f"Nenhum backup encontrado em {estado['pasta']}. Rode scripts/backup.py.")
    else:
        msg = f"Último backup: {estado['total']} respostas, há {estado['atrasado_horas']} h (pasta {estado['pasta']})."
        (st.warning if estado["atrasado_horas"] > 3 else st.info)(msg)
        if h["ok"]:
            v = monitor.bk.verify(monitor.bk.fetch_rows(url, tabela), Path(estado["pasta"]))
            if v["ok"]:
                st.success(f"Verificação contra o backup: ok ({v['novas']} respostas novas desde então).")
            else:
                st.error(f"DIVERGÊNCIA em relação ao backup: {len(v['ausentes'])} ausentes, {len(v['alteradas'])} alteradas. "
                         "Não sobrescreva backups; investigue.")


def pagina_monitor():
    st.title("Monitoramento da coleta")
    st.caption("Atualiza sozinho a cada minuto. Horários em Brasília.")
    _monitor_corpo()


PAGINAS = {"Painel": pagina_painel, "Apresentação": pagina_apresentacao, "Monitoramento": pagina_monitor,
           "Metodologia e desvios": pagina_metodologia}
pagina = st.sidebar.radio("Página", list(PAGINAS))
PAGINAS[pagina]()
