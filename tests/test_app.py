from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

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
