"""Streamlit entry point. Run: python -m streamlit run app.py"""
from dataclasses import asdict
import math

import numpy as np
import pandas as pd
import streamlit as st

from cet import __version__, charts
from cet.core import (Component, Format, bellows, component_records, coverage, depth_of_field,
                      equivalence, focal_for_fov, fov, monte_carlo, presets, sensor, stack_up)
from cet.export import report, to_csv, to_json
from cet.i18n import LANGUAGES, translate


def t(text, language=st.session_state.get("p_language", "en")):
    # Bind this render's locale so widget serialization never consults a later
    # session context (including callbacks and Streamlit's AppTest runner).
    return translate(text, language)


st.set_page_config(page_title="Camera Engineering Toolkit", page_icon="◉", layout="wide",
                   initial_sidebar_state="auto", menu_items={
                       "About": f"Camera Engineering Toolkit {__version__} · MIT · Paraxial engineering models"})

# Keep tool inputs when Streamlit removes widgets belonging to another tool.
for key in list(st.session_state):
    if key.startswith("p_") and not key.endswith("_table"):
        st.session_state[key] = st.session_state[key]

st.markdown("""<style>
.block-container {max-width: 1480px; padding-top: 2.5rem; padding-bottom: 3rem;}
h1 {font-size: 2rem !important; letter-spacing: -.04em; font-weight: 650 !important;}
h2 {font-size: 1.35rem !important;} h3 {font-size: 1.08rem !important;}
[data-testid="stSidebar"] {border-right: 1px solid #8491a326;}
[data-testid="stSidebar"] .block-container {padding-top: 2rem;}
[data-testid="stMetric"] {padding: .8rem 1rem; border: 1px solid #8491a333; border-radius: 7px;}
[data-testid="stMetricValue"] {font-variant-numeric: tabular-nums; font-size: 1.55rem;}
[data-testid="stMetricLabel"] {font-size: .875rem;}
.eyebrow {font-size:.76rem; letter-spacing:.16em; color:#168b99; font-weight:700; margin-bottom:.5rem;}
.brand {font-size:1.22rem; font-weight:700; line-height:1.3; letter-spacing:-.03em;}
.brand small {display:block; font-size:.75rem; letter-spacing:.12em; font-weight:500; margin-top:.6rem; opacity:.6;}
[data-testid="stSidebar"] [role="radiogroup"] {gap:.5rem;}
[data-testid="stDownloadButton"] button {width:100%;}
@media(max-width:700px) {.block-container {padding:1.5rem 1rem;} h1 {font-size:1.6rem !important;}}
</style>""", unsafe_allow_html=True)

FORMATS = presets()
TOOLS = ["Format / Sensor", "Field of View", "Lens Equivalence", "Depth of Field",
         "Large Format", "Camera Design", "Tolerance / Monte Carlo"]
DESCRIPTIONS = {
    "Format / Sensor": "Image geometry, pixel pitch and the 135-format reference.",
    "Field of View": "Calculate angular coverage, solve for focal length and compare formats.",
    "Lens Equivalence": "Match the same angle of view across two image formats.",
    "Depth of Field": "Hyperfocal distance and acceptable-focus limits for a chosen blur criterion.",
    "Large Format": "Bellows exposure and image-circle coverage with rise and shift.",
    "Camera Design": "Place the sensor plane using a signed mechanical dimension chain.",
    "Tolerance / Monte Carlo": "Estimate assembly variation with independent component tolerances.",
}


def dark():
    return getattr(getattr(st.context, "theme", None), "type", "light") == "dark"


def number(label, value, key, minimum=0.001, maximum=100000.0, step=None, fmt=None):
    kwargs = {"min_value": float(minimum), "max_value": float(maximum), "value": float(value),
              "key": f"p_{key}"}
    if step is not None:
        kwargs["step"] = float(step)
    if fmt:
        kwargs["format"] = fmt
    return st.number_input(t(label), **kwargs)


def format_picker(prefix, default="Medium format 48 × 36", label="Image format"):
    names = list(FORMATS) + ["Custom"]
    selected = st.selectbox(t(label), names, index=names.index(default), key=f"p_{prefix}_preset", format_func=t)
    if st.session_state.get(f"p_{prefix}_last") != selected:
        if selected != "Custom":
            st.session_state[f"p_{prefix}_w"] = FORMATS[selected].width_mm
            st.session_state[f"p_{prefix}_h"] = FORMATS[selected].height_mm
        st.session_state[f"p_{prefix}_last"] = selected
    a, b = st.columns(2)
    with a:
        w = number("Width (mm)", 48, prefix + "_w", maximum=2000)
    with b:
        h = number("Height (mm)", 36, prefix + "_h", maximum=2000)
    base = FORMATS.get(selected)
    unchanged = base and base.width_mm == w and base.height_mm == h
    fmt = base if unchanged else Format("Custom", w, h)
    st.caption(t(fmt.note if unchanged else "Custom image area. All calculations use the dimensions above."))
    return fmt


def metric_row(items):
    for column, (label, value) in zip(st.columns(len(items)), items):
        column.metric(t(label), t(value))


def distance(value):
    return "∞" if math.isinf(value) else f"{value / 1000:,.3f} m"


def exports(tool, inputs, results, suffix=""):
    payload = report(tool, inputs, results)
    st.divider()
    left, a, b = st.columns([2, 1, 1])
    left.caption(t("Export a calculation record · inputs, results & units"))
    stem = tool.lower().replace(" / ", "-").replace(" ", "-") + suffix
    a.download_button(t("Download JSON"), to_json(payload), file_name=f"cet-{stem}.json",
                      mime="application/json", key=stem + "json")
    b.download_button(t("Download CSV"), to_csv(payload), file_name=f"cet-{stem}.csv",
                      mime="text/csv", key=stem + "csv")


def draw(fig):
    charts.prepare_font(fig)
    st.pyplot(fig, width="stretch")
    fig.clear()


def component_editor(prefix, initial):
    st.caption(t("Add or remove rows. Dimensions are in mm; Sign sets the direction in the chain."))
    data = st.data_editor(pd.DataFrame(st.session_state.get(prefix + "_table_seed", initial)), hide_index=True, num_rows="dynamic", width="stretch",
        key=f"p_{prefix}_table", column_config={
            "name": st.column_config.TextColumn(t("Component"), required=True),
            "nominal_mm": st.column_config.NumberColumn(t("Nominal (mm)"), min_value=0, max_value=100000,
                                                         required=True, format="%.4f"),
            "tolerance_mm": st.column_config.NumberColumn(t("± tolerance (mm)"), min_value=0, max_value=10000,
                                                           required=True, format="%.4f"),
            "sign": st.column_config.SelectboxColumn(t("Sign"), options=[1, -1], required=True),
            "distribution": st.column_config.SelectboxColumn(t("Distribution"), options=["Uniform", "Normal (±3σ)"], format_func=t, required=True)
        })
    st.session_state[prefix + "_table_result"] = data.to_dict("records")
    result = []
    for index, record in enumerate(data.to_dict("records"), start=1):
        if any(pd.isna(v) for v in record.values()):
            raise ValueError(f"Complete every field in component row {index}, or delete that row.")
        result.append(Component(**record))
    return result


DEFAULT_COMPONENTS = [asdict(Component("Body register", 40.0, .05)),
                      asdict(Component("Adapter", 10.0, .03)),
                      asdict(Component("Back to sensor", 20.0, .02))]


def switch_tool():
    for prefix in ("design", "mc"):
        if prefix + "_table_result" in st.session_state:
            st.session_state[prefix + "_table_seed"] = st.session_state[prefix + "_table_result"]
        st.session_state.pop(f"p_{prefix}_table", None)


def format_tool():
    left, right = st.columns([1, 1.75], gap="large")
    with left:
        st.subheader(t("Image area"))
        fmt = format_picker("sensor")
        has_pixels = st.checkbox(t("Include pixel resolution"), value=True, key="p_sensor_pixels")
        x = y = None
        if has_pixels:
            x = st.number_input(t("Horizontal pixels"), min_value=1, max_value=1000000, value=8000, key="p_sensor_px")
            y = st.number_input(t("Vertical pixels"), min_value=1, max_value=1000000, value=6000, key="p_sensor_py")
    result = sensor(fmt, x, y)
    with right:
        metric_row([("Diagonal", f"{result['diagonal_mm']:.3f} mm"), ("Aspect ratio", f"{result['aspect_ratio']:.4f} : 1"),
                    ("Crop vs 135", f"{result['crop_factor_135_diagonal']:.4f}×")])
        if has_pixels:
            metric_row([("Resolution", f"{result['megapixels']:.2f} MP"),
                        ("Pixel pitch · X / Y", f"{result['pixel_pitch_x_um']:.2f} / {result['pixel_pitch_y_um']:.2f} µm"),
                        ("Pixel density", f"{result['pixel_density_px_per_mm2']:,.0f} px/mm²")])
            if not math.isclose(result["pixel_pitch_x_um"], result["pixel_pitch_y_um"], rel_tol=.01):
                st.warning(t("These dimensions imply non-square pixels. Check active area and pixel resolution."))
        st.subheader(t("Image area at the same scale"))
        draw(charts.format_rectangles([fmt, FORMATS["135 / Full frame"]], dark(), language=st.session_state.get("p_language", "en")))
    exports("Format / Sensor", {"format": asdict(fmt), "pixels_x": x, "pixels_y": y}, result)


def fov_tool():
    left, right = st.columns([1, 1.75], gap="large")
    with left:
        st.subheader(t("Optical setup"))
        fmt = format_picker("fov")
        mode = st.radio(t("Solve for"), ["Angle of view", "Focal length"], horizontal=True, key="p_fov_mode", format_func=t)
        axis = "Horizontal"
        angle = None
        if mode == "Focal length":
            axis = st.selectbox(t("Target axis"), ["Horizontal", "Vertical", "Diagonal"], key="p_fov_axis", format_func=t)
            angle = number("Target angle (°)", 40, "fov_angle", minimum=.01, maximum=179.99)
            focal = focal_for_fov(fmt, angle, axis)
        else:
            focal = number("Focal length (mm)", 80, "fov_focal", maximum=10000)
        st.caption(t("Rectilinear projection at infinity. Distortion, fisheye lenses and focus breathing are excluded."))
    result = fov(fmt, focal)
    with right:
        metric_row([(axis + " FOV", f"{result[axis.lower() + '_deg']:.2f}°")
                    for axis in ("Horizontal", "Vertical", "Diagonal")])
        if mode == "Focal length":
            st.metric(t("Required focal length"), t(f"{focal:.3f} mm"))
        st.subheader(t("Angular field projected at 1 m"))
        draw(charts.fov_plot(fmt, focal, dark(), language=st.session_state.get("p_language", "en")))
    st.subheader(t("Compare formats & focal lengths"))
    a, b = st.columns([1.7, 1])
    names = a.multiselect(t("Comparison formats"), list(FORMATS), default=["135 / Full frame", "Medium format 48 × 36"], key="p_fov_compare", format_func=t)
    focal_text = b.text_input(t("Focal lengths (mm, comma-separated)"), "50, 80", key="p_fov_lengths")
    comparison = []
    try:
        focal_values = [float(v.strip()) for v in focal_text.split(",") if v.strip()]
        if not focal_values:
            raise ValueError("Enter at least one focal length.")
        if len(focal_values) * (len(names) + 1) > 60:
            raise ValueError("Use at most 60 format / focal-length combinations.")
        selected = [(name, FORMATS[name]) for name in names]
        if fmt.name == "Custom":
            selected.insert(0, (f"Custom {fmt.width_mm:g} × {fmt.height_mm:g}", fmt))
        for name, area in selected:
            for length in focal_values:
                comparison.append({"format": name, "focal_mm": length, **fov(area, length)})
        if comparison:
            table = pd.DataFrame(comparison).round(3)
            table["format"] = table["format"].map(t)
            st.dataframe(table, hide_index=True, width="stretch", column_config={
                "format": t("Format"), "focal_mm": t("Focal length (mm)"),
                "horizontal_deg": t("Horizontal FOV") + " (°)",
                "vertical_deg": t("Vertical FOV") + " (°)",
                "diagonal_deg": t("Diagonal FOV") + " (°)"})
        else:
            st.info(t("Select a comparison format to build the table."))
    except ValueError as exc:
        comparison = []
        st.warning(t(f"Comparison: {exc}"))
    exports("Field of View", {"format": asdict(fmt), "focal_mm": focal, "mode": mode,
                              "target_axis": axis, "target_angle_deg": angle},
            {**result, "focal_mm": focal, "comparison": comparison})


def equivalence_tool():
    a, b, c = st.columns([1, 1, 1.2], gap="large")
    with a:
        st.subheader(t("Source format"))
        source = format_picker("equiv_source")
        focal = number("Source focal length (mm)", 80, "equiv_focal", maximum=10000)
        aperture = number("Source f-number", 4, "equiv_aperture", minimum=.1, maximum=256)
    with b:
        st.subheader(t("Target format"))
        target = format_picker("equiv_target", "135 / Full frame")
        axis = st.selectbox(t("Match angle along"), ["Diagonal", "Horizontal", "Vertical"], key="p_equiv_axis", format_func=t)
    result = equivalence(source, target, focal, aperture, axis)
    with c:
        st.subheader(t("Equivalent setup"))
        st.metric(t("Target focal length"), t(f"{result['equivalent_focal_mm']:.3f} mm"))
        st.metric(t("Matched angle · " + axis.lower()), t(f"{result['target_angle_deg']:.2f}°"))
        st.metric(t("Approx. equivalent DOF aperture"), t(f"f/{result['equivalent_dof_f_number']:.2f}"))
    st.info(t("Different aspect ratios cannot match all three angles at once. The aperture result approximates equal depth of field at the same viewpoint, with CoC scaled by the selected format ratio. It is not an exposure correction."))
    draw(charts.format_rectangles([source, target], dark(), language=st.session_state.get("p_language", "en")))
    exports("Lens Equivalence", {"source": asdict(source), "target": asdict(target), "source_focal_mm": focal,
                                 "source_f_number": aperture, "axis": axis}, result)


def dof_tool():
    left, right = st.columns([1, 1.75], gap="large")
    with left:
        fmt = format_picker("dof", "135 / Full frame")
        focal = number("Focal length (mm)", 50, "dof_focal", maximum=10000)
        aperture = number("F-number", 8, "dof_aperture", minimum=.1, maximum=256)
        distance_m = number("Focus distance (m)", 3, "dof_distance", maximum=1000000)
        mode = st.radio(t("Circle of confusion"), ["Format diagonal / 1500", "Custom"], key="p_dof_cocmode", format_func=t)
        coc = fmt.diagonal_mm / 1500 if mode != "Custom" else number("CoC (mm)", .03, "dof_coc", minimum=.0001, maximum=10, fmt="%.4f")
        st.caption(t(f"CoC used: {coc:.5f} mm. Diagonal / 1500 is a viewing convention, not a sensor limit."))
    result = depth_of_field(focal, aperture, distance_m * 1000, coc)
    with right:
        metric_row([("Near limit", distance(result["near_mm"])), ("Far limit", distance(result["far_mm"])),
                    ("Total depth", distance(result["total_dof_mm"]))])
        metric_row([("Hyperfocal", distance(result["hyperfocal_mm"])), ("In front of focus", distance(result["front_dof_mm"])),
                    ("Behind focus", distance(result["rear_dof_mm"]))])
        st.subheader(t("Acceptable-focus interval"))
        end = min(result["far_mm"] / 1000, max(distance_m * 2, result["near_mm"] / 1000 + 1))
        fig, ax, fg = charts.canvas(dark(), (8, 2.5))
        ax.axvspan(result["near_mm"] / 1000, end, color=charts.COLORS[0], alpha=.25, label=t("Within CoC criterion"))
        ax.axvline(distance_m, color=charts.COLORS[1], lw=2, label=t("Focus distance"))
        ax.set(xlim=(0, end * 1.08), ylim=(0, 1), xlabel=t("Object distance from principal plane (m)"), yticks=[])
        ax.legend(fontsize=9, facecolor=fig.get_facecolor(), labelcolor=fg)
        draw(fig)
        if math.isinf(result["far_mm"]) or result["far_mm"] / 1000 > end:
            st.caption(t("The interval continues beyond the right edge of this chart."))
        st.caption(t("Thin-lens geometric blur model; excludes diffraction, aberrations and pupil asymmetry. Distances are from the lens principal plane."))
    exports("Depth of Field", {"format": asdict(fmt), "focal_mm": focal, "f_number": aperture,
                               "distance_mm": distance_m * 1000, "coc_mm": coc, "coc_mode": mode}, result)


def large_tool():
    a, b = st.columns([1, 1.75], gap="large")
    with a:
        fmt = format_picker("large", "4 × 5 sheet")
        focal = number("Focal length (mm)", 150, "large_focal", maximum=10000)
        extension = number("Total bellows extension (mm)", 200, "large_extension", maximum=20000)
        circle = number("Image circle diameter (mm)", 210, "large_circle", maximum=20000)
        dx = number("Horizontal shift (mm)", 0, "large_dx", minimum=-1000, maximum=1000)
        dy = number("Vertical rise / fall (mm)", 15, "large_dy", minimum=-1000, maximum=1000)
    bellow = bellows(focal, extension)
    cover = coverage(fmt, circle, dx, dy)
    with b:
        metric_row([("Magnification", f"{bellow['magnification']:.3f}×"),
                    ("Exposure factor", f"{bellow['exposure_factor']:.3f}×"),
                    ("Exposure compensation", f"+{bellow['exposure_compensation_stops']:.3f} stops")])
        metric_row([("Object distance", distance(bellow['object_distance_mm'])),
                    ("Required image circle", f"{cover['required_circle_mm']:.2f} mm"),
                    ("Radial margin", f"{cover['radial_margin_mm']:+.2f} mm")])
        (st.success if cover["covered"] else st.warning)(t("Image area is inside the supplied circle." if cover["covered"] else "Image area extends outside the supplied circle."))
        draw(charts.coverage_plot(fmt, circle, dx, dy, dark(), language=st.session_state.get("p_language", "en")))
    st.caption(t("Extension is the total image distance from the rear principal plane, not extension beyond infinity. Bellows model assumes pupil magnification 1. Supply the image circle at the actual focus and aperture; tilt/swing, mechanical vignetting and automatic circle enlargement are excluded."))
    exports("Large Format", {"format": asdict(fmt), "focal_mm": focal, "extension_mm": extension,
                              "image_circle_mm": circle, "shift_x_mm": dx, "shift_y_mm": dy},
            {"bellows": bellow, "coverage": cover})


def design_tool():
    a, b = st.columns([1, 1.75], gap="large")
    with a:
        target = number("Required flange-to-sensor distance (mm)", 70, "design_target", maximum=10000)
        width = number("Back envelope width (mm)", 80, "design_width", maximum=2000)
        height = number("Back envelope height (mm)", 70, "design_height", maximum=2000)
        st.caption(t("Lens flange is Z = 0; positive Z points toward the sensor. Back envelope dimensions are recorded only; no collision or mounting-hole analysis is implied."))
    with b:
        st.subheader(t("Sensor-plane stack"))
        components = component_editor("design", DEFAULT_COMPONENTS)
    result = stack_up(components, target)
    metric_row([("Actual sensor plane", f"{result['actual_mm']:.4f} mm"),
                ("Plane error", f"{result['error_mm']:+.4f} mm"),
                ("Required net correction", f"{result['required_correction_mm']:+.4f} mm")])
    draw(charts.stack_plot(components, target, dark(), language=st.session_state.get("p_language", "en")))
    st.caption(t("Positive plane error means the sensor is too far from the lens flange. Positive correction adds net spacing; negative correction removes it. A tolerance envelope sums stated ± values; it is not a guaranteed bound for unbounded normal distributions."))
    exports("Camera Design", {"flange_distance_mm": target, "back_width_mm": width, "back_height_mm": height,
                               "components": component_records(components)}, result)


def tolerance_tool():
    a, b, c, d = st.columns(4)
    with a:
        target = number("Target stack (mm)", 70, "mc_target", minimum=-100000, maximum=100000)
    with b:
        low = number("Lower error limit (mm)", -.1, "mc_low", minimum=-10000, maximum=10000, fmt="%.4f")
    with c:
        high = number("Upper error limit (mm)", .1, "mc_high", minimum=-10000, maximum=10000, fmt="%.4f")
    with d:
        count = st.selectbox(t("Samples"), [1000, 10000, 50000, 100000, 250000], index=2, key="p_mc_count")
    components = component_editor("mc", DEFAULT_COMPONENTS)
    a, b = st.columns([1, 3])
    seed = a.number_input(t("Random seed"), min_value=0, max_value=2**32 - 1, value=42, key="p_mc_seed")
    b.caption(t("Uniform: bounded at ± tolerance. Normal: tolerance means ±3σ, with unbounded tails. Components are independent; the 95% interval describes simulated assemblies, not confidence in the mean."))
    inputs = {"components": component_records(components), "target_mm": target, "lower_error_mm": low,
              "upper_error_mm": high, "samples": count, "seed": seed}
    signature = to_json(inputs)
    # Validate before offering a simulation, including an empty or incomplete table.
    analytic = stack_up(components, target)
    if low >= high:
        raise ValueError("Lower error limit must be below upper error limit.")
    if st.button(t("Run simulation"), type="primary", key="run_mc"):
        with st.spinner(t("Sampling the tolerance stack…")):
            results, errors = monte_carlo(components, target, low, high, count, seed)
        st.session_state["simulation"] = (signature, results, errors)
    previous = st.session_state.get("simulation")
    if not previous or previous[0] != signature:
        st.info(t("Ready to simulate." if not previous else "Inputs changed. Run the simulation again to refresh the results."))
        metric_row([("Nominal error", f"{analytic['error_mm']:+.4f} mm"),
                    ("Analytic standard deviation", f"{analytic['analytic_sigma_mm']:.5f} mm"),
                    ("Tolerance envelope", f"±{(analytic['tolerance_envelope_max_mm'] - analytic['actual_mm']):.4f} mm")])
        return
    _, result, errors = previous
    metric_row([("Mean error", f"{result['mean_error_mm']:+.5f} mm"),
                ("Standard deviation", f"{result['sample_std_mm']:.5f} mm"),
                ("Outside specification", f"{100 * result['out_of_spec_fraction']:.3f}%")])
    a, b = st.columns([2, 1])
    with a:
        draw(charts.histogram(errors, low, high, dark(), language=st.session_state.get("p_language", "en")))
    with b:
        st.metric(t("Central 95% · lower"), t(f"{result['p025_error_mm']:+.5f} mm"))
        st.metric(t("Central 95% · upper"), t(f"{result['p975_error_mm']:+.5f} mm"))
        st.metric(t("Within specification"), t(f"{100 * result['yield_fraction']:.3f}%"))
        st.caption(t(f"{count:,} samples · seed {seed}. Finite samples do not establish zero failure risk."))
    exports("Tolerance / Monte Carlo", inputs, result)
    st.download_button(t("Download all samples (CSV)"), pd.DataFrame({"sample": np.arange(1, count + 1),
        "plane_error_mm": errors, "stack_mm": errors + target}).to_csv(index=False),
        file_name="cet-monte-carlo-samples.csv", mime="text/csv")


with st.sidebar:
    st.selectbox("Language / 语言", list(LANGUAGES), format_func=LANGUAGES.get,
                 key="p_language", on_change=switch_tool)
    st.markdown(f'<div class="brand">◉ Camera Engineering<br>Toolkit<small>{t("OPTICS / MECHANICS / VARIATION")}</small></div>', unsafe_allow_html=True)
    st.divider()
    tool = st.radio(t("Workspace"), TOOLS, index=1, key="p_tool", on_change=switch_tool, format_func=t)
    st.divider()
    st.caption(t("APPEARANCE"))
    st.write(t("Light / Dark / System"))
    st.caption(t("Open the top-right menu to choose Light, Dark or System."))
    st.caption(t(f"VERSION {__version__} · SI UNITS"))
    with st.expander(t("Calculation notes")):
        st.write(t("All lengths use mm internally. Object distance inputs marked m are converted explicitly. Presets are representative active areas. Custom dimensions are always available."))
        st.write(t("Inputs stay available while switching tools in this session. Download calculation records before closing the app."))
        st.write(t("No accounts, analytics or external calculation services. A hosted server processes inputs in session memory."))

st.markdown(f'<div class="eyebrow">{TOOLS.index(tool) + 1:02d} / {t("ENGINEERING WORKSPACE")}</div>', unsafe_allow_html=True)
st.title(t(tool))
st.caption(t(DESCRIPTIONS[tool]))
st.divider()
try:
    {"Format / Sensor": format_tool, "Field of View": fov_tool, "Lens Equivalence": equivalence_tool,
     "Depth of Field": dof_tool, "Large Format": large_tool, "Camera Design": design_tool,
     "Tolerance / Monte Carlo": tolerance_tool}[tool]()
except ValueError as exc:
    st.error(t(str(exc)))
