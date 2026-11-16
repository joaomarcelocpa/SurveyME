import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import analysis as an  # noqa: E402
import monitor  # noqa: E402
import presentation  # noqa: E402
import seed_dev  # noqa: E402

Q = an.load_questionnaire()


def dados():
    bruto = an.rows_to_df(seed_dev.gerar(80))
    return bruto, an.classify(bruto, Q)


def test_acumulado_e_monotonico_e_termina_no_total():
    _, todos = dados()
    ac = monitor.acumulado(todos)
    assert ac["recebidas"].is_monotonic_increasing and ac["válidas"].is_monotonic_increasing
    assert ac["recebidas"].iloc[-1] == len(todos) and ac["válidas"].iloc[-1] == todos["valida"].sum()


def test_rajadas_detecta_cinco_em_cinco_minutos():
    t0 = pd.Timestamp("2026-11-13 12:00", tz="UTC")
    rapido = pd.DataFrame({"created_at": [t0 + pd.Timedelta(seconds=30 * i) for i in range(6)]})
    lento = pd.DataFrame({"created_at": [t0 + pd.Timedelta(minutes=30 * i) for i in range(6)]})
    assert len(monitor.rajadas(rapido)) == 1 and monitor.rajadas(rapido).iloc[0]["respostas"] == 6
    assert monitor.rajadas(lento).empty


def test_cobertura_cobre_as_tres_qps():
    _, todos = dados()
    cob = monitor.cobertura(todos[todos.valida], Q)
    assert set(cob["QP"]) == {"QP1", "QP2", "QP3"}
    assert set(cob["situação"]) <= {"ok", "baixa"}


def test_apresentacao_slides_e_texto_sem_causalidade():
    bruto, _ = dados()
    slides = presentation.build_slides(bruto, Q, True)
    assert slides[0]["capa"] and slides[-1]["titulo"] == "Obrigado"
    qps = [s for s in slides if s["titulo"].startswith("QP")]
    assert len(qps) == 3 and all("não causalidade" in s["texto"] for s in qps)
    assert "DADOS SINTÉTICOS" in slides[0]["texto"]


def test_html_estatico_funciona_offline():
    bruto, _ = dados()
    h = presentation.build_html(presentation.build_slides(bruto, Q, True), True)
    import re
    # nenhum recurso externo e carregado: plotly vai embutido (as URLs que aparecem estao dentro do codigo dele)
    assert not re.search(r"<(script|link|img|iframe)[^>]+(src|href)=[\"']https?:", h)
    assert h.count('class="slide') >= 9 and "DADOS SINTÉTICOS" in h


def test_magnitude_de_efeito():
    assert presentation.magnitude("ρ", -0.73) == "grande"
    assert presentation.magnitude("ε²", 0.02) == "fraco"
    assert presentation.magnitude("r (bisserial por postos)", 0.05) == "desprezível"
