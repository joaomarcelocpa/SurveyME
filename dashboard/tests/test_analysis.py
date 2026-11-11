import math
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import analysis as an  # noqa: E402
import seed_dev  # noqa: E402

Q = an.load_questionnaire()


def base_df():
    return an.rows_to_df(seed_dev.gerar(80))


def test_margem_de_erro_pior_caso():
    assert math.isclose(an.margin_of_error(0.5, 50), 0.1386, abs_tol=1e-3)
    assert math.isclose(an.margin_of_error(0.5, 60), 0.1265, abs_tol=1e-3)


def test_holm():
    assert an.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_descartes_com_motivo_e_nada_removido():
    df = base_df()
    c = an.classify(df, Q)
    assert len(c) == len(df)
    assert set(c.loc[~c.valida, "motivo"]) <= set(an.MOTIVOS)
    assert {"falhou na atenção", "tempo muito curto", "fora da população", "incompleta"} <= set(c.motivo)


def test_item_invertido_e_escores():
    df = pd.DataFrame([{**{f"Q{i}": 3 for i in range(10, 17)}, "Q17": 5}])
    s = an.add_scores(df, Q)
    assert s.loc[0, "dependencia"] == pytest.approx((3 + 3 + 3 + 1) / 4)
    assert s.loc[0, "confianca"] == 3


def test_cronbach_itens_identicos_da_alfa_1():
    rows = [{"Q10": v, "Q11": v, "Q12": v, "Q13": v} for v in [1, 2, 3, 4, 5, 2, 4]]
    assert an.cronbach(pd.DataFrame(rows), Q, "confianca")["alpha"] == pytest.approx(1.0)


def test_qps_detectam_associacao_sintetica():
    v = an.classify(base_df(), Q)
    v = v[v.valida]
    res = an.answer_rqs(v, Q).set_index("QP")
    assert res.loc["QP1", "efeito"] < -0.4 and res.loc["QP1", "p_holm"] < 0.05
    assert (res["p_holm"] >= res["p"] - 1e-12).all()


def test_dunn_tres_pares():
    v = an.add_scores(an.classify(base_df(), Q).query("valida"), Q)
    assert len(an.dunn(v.dependencia, v.Q3)) == 3


def test_mannwhitney_efeito_sinal():
    y = pd.Series([5, 5, 4, 1, 2, 1])
    g = pd.Series(["a", "a", "a", "b", "b", "b"])
    r = an.mannwhitney(y, g, "a", "b")
    assert r["efeito"] == pytest.approx(1.0)


def test_quase_duplicata_sinalizada_e_identica_nao():
    rows = seed_dev.gerar(3)
    a = rows[0]["answers"]
    quase = {**a, "Q10": min(5, a["Q10"] + 1)}
    ident = dict(a)
    t0 = rows[0]["created_at"]
    mk = lambda ans, m: {"id": f"id{m}", "created_at": t0 + pd.Timedelta(minutes=m), "form_version": "1", "consent": True, "answers": ans}
    df = an.rows_to_df([mk(a, 0), mk(quase, 5), mk({**a, "Q9": ["outro"], "Q10": 1}, 6)])
    f = an.flag_near_duplicates(df, Q)
    assert f.tolist() == [False, a["Q10"] < 5, False]
    df2 = an.rows_to_df([mk(a, 0), mk(ident, 5)])
    assert not an.flag_near_duplicates(df2, Q).any()


def test_grupo_exclusivo_multipla_escolha():
    s = pd.Series(["gerar_codigo", "duvidas", "duvidas|gerar_codigo", "corrigir_erros", "duvidas|gerar_testes"])
    g = an.grupo_exclusivo(s, "gerar_codigo", "duvidas")
    assert g.tolist()[:2] == ["gerar_codigo", "duvidas"]
    assert pd.isna(g[2]) and pd.isna(g[3])
    assert g[4] == "duvidas"


def test_normaliza_multipla_ordenada():
    assert an.normalize_answers({"Q9": ["duvidas", "gerar_codigo"]})["Q9"] == "duvidas|gerar_codigo"
