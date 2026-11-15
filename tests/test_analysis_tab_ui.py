"""AppTest coverage for the Analysis tab sections 7-9 (structure, best-response basins, sensitivity) and state handling."""
import os

import pytest
from streamlit.testing.v1 import AppTest

import game_engine as ge
import sample_data as sd

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _headings(at):
    return [str(m.value) for m in at.markdown if str(m.value).startswith("### ")]


def _metric(at, label):
    vals = [m.value for m in at.metric if m.label == label]
    assert vals, f"metric {label!r} not found in {[m.label for m in at.metric]}"
    return str(vals[0])


@pytest.fixture(scope="module")
def default_app():
    at = AppTest.from_file(APP, default_timeout=120).run()
    at.selectbox(key="scenario_preset").set_value("Default scenario").run()
    assert not at.exception
    return at


def test_U01_analysis_tab_has_all_nine_sections(default_app):
    heads = _headings(default_app)
    for number in range(1, 10):
        assert any(h.startswith(f"### {number} ") for h in heads), (number, heads)


def test_U02_displayed_numbers_equal_the_engine(default_app):
    at = default_app
    sc = sd.get_default_scenario()
    L = ge.analyze_landscape(sc)
    assert _metric(at, "Pure Nash equilibria") == str(L["n_equilibria"]) == "23"
    assert _metric(at, "Possible assignments") == "6,561"
    d = ge.analyze_distributions(sc)
    assert _metric(at, "Lowest welfare") == str(d["welfare"]["min"])
    b = ge.analyze_basins(sc)
    assert _metric(at, "Runs (one per start)") == f"{b['n_runs']:,}"
    assert _metric(at, "Distinct end points") == str(b["n_endpoints"])
    assert _metric(at, "Longest run (moves)") == str(b["max_steps"])


def test_U03_switching_update_order_and_sweep_parameter_works_and_errors_nothing(default_app):
    at = default_app
    at.radio(key="analysis_basin_order").set_value("random").run()
    assert not at.exception and _metric(at, "Converged") == "6,561"
    for param in ("compatibility_scale", "preference_scale", "gamma"):
        at.selectbox(key="analysis_sweep_param").set_value(param).run()
        assert not at.exception, param
    at.radio(key="analysis_basin_order").set_value("round_robin").run()
    assert not at.exception


def test_U04_changing_gamma_updates_every_analysis_number_no_stale_results():
    at = AppTest.from_file(APP, default_timeout=120).run()
    at.selectbox(key="scenario_preset").set_value("Default scenario").run()
    assert _metric(at, "Pure Nash equilibria") == "23"
    at.checkbox(key="gamma_override_on").set_value(True).run()
    at.slider(key="gamma_override").set_value(1.0).run()
    assert not at.exception
    expected = ge.analyze_landscape(dict(sd.get_default_scenario(), gamma=1.0))["n_equilibria"]
    assert expected != 23
    assert _metric(at, "Pure Nash equilibria") == str(expected)
    b = ge.analyze_basins(dict(sd.get_default_scenario(), gamma=1.0))
    assert _metric(at, "Distinct end points") == str(b["n_endpoints"])
    at.checkbox(key="gamma_override_on").set_value(False).run()
    assert _metric(at, "Pure Nash equilibria") == "23"


def test_U05_tiny_scenario_renders_every_section_without_exception():
    at = AppTest.from_file(APP, default_timeout=120).run()
    at.selectbox(key="scenario_preset").set_value("Tiny hand-verified example").run()
    assert not at.exception
    assert any(h.startswith("### 9 ") for h in _headings(at))
    assert _metric(at, "Pure Nash equilibria") == "1"


def test_U06_scenario_above_the_enumeration_cap_shows_the_warning_not_the_sections():
    at = AppTest.from_file(APP, default_timeout=120).run()
    at.selectbox(key="scenario_preset").set_value("Custom synthetic scenario").run()
    at.slider(key="custom_num_students").set_value(12).run()
    at.slider(key="custom_num_projects").set_value(5).run()
    assert not at.exception
    assert any("unavailable" in str(w.value) for w in at.warning)
    assert not any(h.startswith("### 7 ") for h in _headings(at))
