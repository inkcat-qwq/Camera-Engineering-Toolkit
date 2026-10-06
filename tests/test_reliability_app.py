from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from cet import charts, export
from cet.chain import DEFAULT_ROWS
from cet.core import DISTANCE_DATUMS
from cet.i18n import translate
from cet.theme import palette
from matplotlib.colors import to_rgba

APP = Path(__file__).resolve().parents[1] / "app.py"
TOOLS = ["Format / Sensor", "Field of View", "Lens Equivalence", "Depth of Field",
         "Large Format", "Camera Design", "Tolerance / Monte Carlo"]


def test_shared_chain_and_target_survive_both_workflows_and_invalidate_mc():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.radio(key="p_tool").set_value("Camera Design").run()
    rows = deepcopy(DEFAULT_ROWS)
    rows[1].update(name="Custom adapter", nominal_mm=10.02, distribution="Normal (±3σ)")
    app.session_state["chain_editor_seed"] = rows
    app.run()
    app.number_input(key="p_chain_target").set_value(70.01).run()
    assert app.session_state["chain_rows"] == rows
    assert any("not a bound" in m.label for m in app.metric)
    app.radio(key="p_tool").set_value("Tolerance / Monte Carlo").run()
    assert app.session_state["chain_rows"] == rows
    assert app.number_input(key="p_chain_target").value == 70.01
    app.button(key="run_mc").click().run()
    old = app.session_state["simulation"]
    app.radio(key="p_theme").set_value("Dark").run()
    assert np.array_equal(app.session_state["simulation"][2], old[2])
    app.radio(key="p_tool").set_value("Camera Design").run()
    assert app.session_state["chain_rows"] == rows
    app.number_input(key="p_chain_target").set_value(70.02).run()
    app.radio(key="p_tool").set_value("Tolerance / Monte Carlo").run()
    assert any("Inputs changed" in i.value for i in app.info)
    assert not any(m.label == "Mean error" for m in app.metric)
    assert not app.exception and not app.error


@pytest.mark.parametrize("name", TOOLS)
def test_theme_switch_redraws_without_input_change_in_both_languages(name, monkeypatch):
    canvas = charts.canvas
    observed = []
    def capture(*args, **kwargs):
        fig, ax, fg = canvas(*args, **kwargs)
        observed.append(fig.get_facecolor())
        return fig, ax, fg
    monkeypatch.setattr(charts, "canvas", capture)
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.radio(key="p_tool").set_value(name).run()
    if name == "Tolerance / Monte Carlo":
        app.button(key="run_mc").click().run()
    metrics = [m.value for m in app.metric]
    for language in ("en", "zh"):
        app.selectbox(key="p_language").set_value(language).run()
        for theme in ("Dark", "Light"):
            observed.clear()
            app.radio(key="p_theme").set_value(theme).run()
            assert not app.exception and not app.error
            assert app.title[0].value == translate(name, language)
            assert observed and all(c == to_rgba(palette(theme)["secondaryBackgroundColor"]) for c in observed)
            assert [m.value for m in app.metric] == [translate(v, language) for v in metrics]


def test_no_widget_default_plus_assigned_state_contract(monkeypatch):
    # AppTest runs without a server runtime, which otherwise bypasses this rule.
    # Inspect the same policy arguments rather than disabling the warning.
    from streamlit.elements.lib import policies
    original = policies.check_session_state_rules
    conflicts = []
    def check(default_value, key, writes_allowed=True):
        from streamlit.runtime.state import get_session_state
        if key and key.startswith("p_") and writes_allowed:
            if default_value is not None and get_session_state().is_new_state_value(key):
                conflicts.append(key)
        return original(default_value, key, writes_allowed)
    monkeypatch.setattr(policies, "check_session_state_rules", check)
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    for name in TOOLS:
        app.radio(key="p_tool").set_value(name).run()
        app.radio(key="p_theme").set_value("Dark").run()
        assert not app.exception
    assert not conflicts


def test_dof_ui_default_datum_close_focus_validation_and_schema(monkeypatch):
    records = []
    original = export.report
    def capture(*args, **kwargs):
        r = original(*args, **kwargs)
        records.append(r)
        return r
    monkeypatch.setattr(export, "report", capture)
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.radio(key="p_tool").set_value("Depth of Field").run()
    assert app.radio(key="p_dof_datum").value == DISTANCE_DATUMS[0]
    app.number_input(key="p_dof_focal").set_value(100).run()
    app.number_input(key="p_dof_distance").set_value(.45).run()
    assert not app.exception and not app.error
    r = records[-1]
    assert r["schema_version"] == 2
    assert r["inputs"]["entered_distance_mm"] == 450
    assert r["inputs"]["distance_mm"] == pytest.approx(300)
    assert r["results"]["near_mm"] > 400
    assert any(m.label == "Total depth" and "mm" in m.value for m in app.metric)
    app.number_input(key="p_dof_distance").set_value(.3).run()
    assert app.error and not app.exception
    app.radio(key="p_dof_datum").set_value(DISTANCE_DATUMS[1]).run()
    assert not app.error and not app.exception
    assert records[-1]["inputs"]["distance_mm"] == 300


def test_all_format_pickers_keep_custom_sheet_dimensions():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    for tool, prefix in (("Format / Sensor", "sensor"), ("Field of View", "fov"),
                         ("Depth of Field", "dof"), ("Large Format", "large")):
        app.radio(key="p_tool").set_value(tool).run()
        app.selectbox(key=f"p_{prefix}_preset").set_value("5 × 7 sheet").run()
        assert app.number_input(key=f"p_{prefix}_w").value == 170
        assert app.number_input(key=f"p_{prefix}_h").value == 120
        assert any("177.8" in i.value and "170" in i.value for i in app.info)
        app.number_input(key=f"p_{prefix}_w").set_value(168).run()
        app.selectbox(key="p_language").set_value("zh").run()
        assert app.number_input(key=f"p_{prefix}_w").value == 168
        app.selectbox(key="p_language").set_value("en").run()
        assert not app.error and not app.exception
