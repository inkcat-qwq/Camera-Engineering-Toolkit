from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from cet.i18n import translate

APP = Path(__file__).resolve().parents[1] / "app.py"
TOOLS = ["Format / Sensor", "Field of View", "Lens Equivalence", "Depth of Field",
         "Large Format", "Camera Design", "Tolerance / Monte Carlo"]


def open_tool(name):
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.radio(key="p_tool").set_value(name).run()
    return app


@pytest.mark.parametrize("name", TOOLS)
def test_tools_render_without_exceptions(name):
    app = open_tool(name)
    assert not app.exception
    assert not app.error
    assert app.title[0].value == name


def test_inverse_fov_custom_input_and_navigation_persistence():
    app = open_tool("Field of View")
    app.number_input(key="p_fov_focal").set_value(120).run()
    app.radio(key="p_tool").set_value("Format / Sensor").run()
    app.radio(key="p_tool").set_value("Field of View").run()
    assert app.number_input(key="p_fov_focal").value == 120
    app.radio(key="p_fov_mode").set_value("Focal length").run()
    app.number_input(key="p_fov_angle").set_value(90).run()
    assert any(m.value == "24.000 mm" for m in app.metric)
    assert not app.exception


def test_monte_carlo_runs_and_marks_stale_results():
    app = open_tool("Tolerance / Monte Carlo")
    app.button(key="run_mc").click().run()
    assert not app.exception
    assert any(m.label == "Mean error" for m in app.metric)
    app.number_input(key="p_mc_high").set_value(.05).run()
    assert any("Inputs changed" in item.value for item in app.info)
    assert not any(m.label == "Mean error" for m in app.metric)


def test_invalid_inputs_show_user_error_not_traceback():
    app = open_tool("Large Format")
    app.number_input(key="p_large_extension").set_value(100).run()
    assert not app.exception
    assert "at least the focal length" in app.error[0].value


def test_dof_infinity_has_display_and_downloads():
    app = open_tool("Depth of Field")
    app.number_input(key="p_dof_distance").set_value(1000).run()
    assert not app.exception
    assert any(m.value == "∞" for m in app.metric)
    assert len(app.get("download_button")) == 2


def test_comparison_nan_is_rejected():
    app = open_tool("Field of View")
    app.text_input(key="p_fov_lengths").set_value("nan, 50").run()
    assert not app.exception
    assert any("finite" in w.value for w in app.warning)


@pytest.mark.parametrize("name", TOOLS)
def test_chinese_workspaces_render_and_switch_back(name):
    app = open_tool(name)
    before = [(m.label, m.value) for m in app.metric]
    app.selectbox(key="p_language").set_value("zh").run()
    assert not app.exception
    assert not app.error
    assert app.title[0].value == translate(name, "zh")
    assert [(m.label, m.value) for m in app.metric] == [
        (translate(label, "zh"), translate(value, "zh")) for label, value in before]
    app.selectbox(key="p_language").set_value("en").run()
    assert not app.exception
    assert app.title[0].value == name
    assert [(m.label, m.value) for m in app.metric] == before


def test_language_preserves_custom_format_inverse_inputs_and_comparison():
    app = open_tool("Field of View")
    app.selectbox(key="p_fov_preset").set_value("Custom").run()
    app.number_input(key="p_fov_w").set_value(65).run()
    app.number_input(key="p_fov_h").set_value(40).run()
    app.radio(key="p_fov_mode").set_value("Focal length").run()
    app.selectbox(key="p_fov_axis").set_value("Vertical").run()
    app.number_input(key="p_fov_angle").set_value(65).run()
    app.multiselect(key="p_fov_compare").set_value(["Micro Four Thirds"]).run()
    before = [m.value for m in app.metric]
    app.selectbox(key="p_language").set_value("zh").run()
    assert not app.exception
    assert app.selectbox(key="p_fov_preset").value == "Custom"
    assert app.number_input(key="p_fov_w").value == 65
    assert app.number_input(key="p_fov_h").value == 40
    assert app.radio(key="p_fov_mode").value == "Focal length"
    assert app.selectbox(key="p_fov_axis").value == "Vertical"
    assert app.number_input(key="p_fov_angle").value == 65
    assert app.multiselect(key="p_fov_compare").value == ["Micro Four Thirds"]
    assert [m.value for m in app.metric] == before
    assert "M4/3 画幅" in app.dataframe[0].value["format"].tolist()


def test_edited_components_and_simulation_survive_language_change():
    import numpy as np
    app = open_tool("Tolerance / Monte Carlo")
    # AppTest has no data-editor input API. Load committed custom records,
    # then exercise the real editor, simulation and language callbacks.
    records = [dict(row) for row in app.session_state["mc_table_result"]]
    records[1].update(name="测试转接环", nominal_mm=10.02, distribution="Normal (±3σ)")
    app.session_state["mc_table_seed"] = records
    app.run()
    assert app.session_state["mc_table_result"][1]["name"] == "测试转接环"
    app.button(key="run_mc").click().run()
    signature, result, samples = app.session_state["simulation"]
    for language in ("zh", "en", "zh"):
        app.selectbox(key="p_language").set_value(language).run()
        assert not app.exception
        assert not app.error
        assert app.session_state["mc_table_result"][1]["name"] == "测试转接环"
        assert app.session_state["mc_table_result"][1]["nominal_mm"] == 10.02
        assert app.session_state["simulation"][0] == signature
        assert app.session_state["simulation"][1] == result
        assert np.array_equal(app.session_state["simulation"][2], samples)
        assert any(m.label == translate("Mean error", language) for m in app.metric)
        assert len(app.get("download_button")) == 3


def test_chinese_validation_and_dynamic_hints():
    app = open_tool("Large Format")
    app.selectbox(key="p_language").set_value("zh").run()
    app.number_input(key="p_large_extension").set_value(100).run()
    assert app.error[0].value == "皮腔总伸长必须大于或等于焦距。"
    app.radio(key="p_tool").set_value("Field of View").run()
    app.text_input(key="p_fov_lengths").set_value("nan").run()
    assert app.warning[0].value == "比较：焦距必须为有限数值。"
    app.text_input(key="p_fov_lengths").set_value("abc").run()
    assert app.warning[0].value == "比较：请输入有效焦距，并使用英文逗号分隔。"
    app.radio(key="p_tool").set_value("Depth of Field").run()
    assert any("使用的弥散圆：" in c.value for c in app.caption)


def test_language_does_not_change_export_schema_or_values(monkeypatch):
    from cet import export
    records = []
    original = export.report
    def capture(*args, **kwargs):
        payload = original(*args, **kwargs)
        records.append(payload)
        return payload
    monkeypatch.setattr(export, "report", capture)
    app = open_tool("Field of View")
    before = records[-1]
    app.selectbox(key="p_language").set_value("zh").run()
    after = records[-1]
    for key in ("tool", "inputs", "results", "schema_version"):
        assert after[key] == before[key]
