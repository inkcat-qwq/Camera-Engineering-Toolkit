"""v1.2 measurement definitions, uncertainty, metadata and presentation contracts."""
import json
import math
from dataclasses import asdict, replace
from importlib.resources import files

import numpy as np
import pytest
from matplotlib.colors import to_rgba

from cet import charts
from cet.chain import DEFAULT_ROWS, DimensionChain
from cet.core import (Component, DISTANCE_DATUMS, Format, depth_of_field,
                      dof_with_datum, image_distance, image_to_principal_distance,
                      principal_to_image_distance, stack_up, wilson_interval)
from cet.display import angle, comparison_focals, length, percentage
from cet.formats import CATEGORIES, format_record, load_catalog, preset_catalog
from cet.theme import native_theme_html, palette, theme_css


@pytest.mark.parametrize("f,s", [(50, 3000), (100, 300), (100, 200), (20, 1e9)])
def test_datum_conversion_roundtrip(f, s):
    v = 1 / (1 / f - 1 / s)
    total = principal_to_image_distance(f, s)
    assert total == pytest.approx(s + v)
    assert image_to_principal_distance(f, total) == pytest.approx(s)
    assert image_distance(f, s) == pytest.approx(v)


@pytest.mark.parametrize("s", [200, 300, 3000])
def test_image_datum_limits_share_one_focused_image_plane(s):
    f, n, c = 100, 8, .03
    v = 1 / (1 / f - 1 / s)
    total = s + v
    result = dof_with_datum(f, n, total, c)
    principal = depth_of_field(f, n, s, c)
    assert result["principal_object_distance_mm"] == pytest.approx(s)
    for key in ("near_mm", "far_mm"):
        assert result[key] == pytest.approx(principal[key] + v)
        u = result[key] - v
        v_at_limit = 1 / (1 / f - 1 / u)
        assert f / n * abs(v - v_at_limit) / v_at_limit == pytest.approx(c)
    assert total - result["near_mm"] == pytest.approx(result["front_dof_mm"])
    assert result["far_mm"] - total == pytest.approx(result["rear_dof_mm"])
    for key in ("total_dof_mm", "front_dof_mm", "rear_dof_mm"):
        assert result[key] == pytest.approx(principal[key])


def test_principal_mode_preserves_reference_equations_and_macro_branch():
    for s in (150, 300, 3000):
        old = depth_of_field(100, 8, s, .03)
        new = dof_with_datum(100, 8, s, .03, DISTANCE_DATUMS[1])
        for key, value in old.items():
            assert new[key] == value


def test_image_hyperfocal_boundary_and_own_conjugate():
    f, n, c = 50, 8, .03
    h = f * f / (n * c) + f
    total_h = h + 1 / (1 / f - 1 / h)
    at = dof_with_datum(f, n, total_h, c)
    assert at["hyperfocal_mm"] == pytest.approx(total_h)
    assert at["near_mm"] == pytest.approx(h / 2 + image_distance(f, h))
    assert math.isinf(at["far_mm"])
    assert math.isfinite(dof_with_datum(f, n, total_h - .001, c)["far_mm"])
    assert math.isinf(dof_with_datum(f, n, total_h + .001, c)["far_mm"])
    close = dof_with_datum(f, n, 4 * f, c)
    assert close["hyperfocal_mm"] == pytest.approx(total_h)
    limited = dof_with_datum(1, 256, 4, 10)
    assert limited["hyperfocal_branch_limited"]
    assert limited["hyperfocal_mm"] == 4
    assert math.isinf(limited["far_mm"])


@pytest.mark.parametrize("call", [
    lambda: image_to_principal_distance(100, 399.999),
    lambda: image_to_principal_distance(100, math.inf),
    lambda: image_to_principal_distance(100, math.nan),
    lambda: image_to_principal_distance(0, 400),
    lambda: principal_to_image_distance(100, 100),
    lambda: dof_with_datum(100, 8, 400, .03, "unknown"),
    lambda: depth_of_field(1e308, 8, 1.5e308, .03),
])
def test_impossible_or_unrepresentable_geometry_rejected(call):
    with pytest.raises(ValueError):
        call()


@pytest.mark.parametrize("mm,expected", [
    (.12345, "0.1235 mm"), (.00002769, "0.00002769 mm"),
    (2.769, "2.769 mm"), (27.69, "27.69 mm"), (276.9, "276.9 mm"),
    (2769, "2.769 m"), (27690, "27.69 m"), (1e9, "1e+06 m"),
    (math.inf, "∞"), (-math.inf, "−∞"), (-0., "0.000 mm"),
    (1e-12, "1e-12 mm"), (-1e-12, "-1e-12 mm"),
])
def test_adaptive_lengths(mm, expected):
    assert length(mm) == expected


def test_front_rear_asymmetry_and_small_angles_remain_visible():
    r = dof_with_datum(100, 8, 450, .03)
    assert length(r["front_dof_mm"]) != length(r["rear_dof_mm"])
    assert "mm" in length(r["total_dof_mm"])
    assert angle(.0002769) == "0.0002769°"
    assert angle(-0.) == "0°"
    assert length(.01, signed=True).startswith("+")
    assert not length(-0., signed=True).startswith(("+", "-"))
    with pytest.raises(ValueError):
        length(math.nan)


def test_catalog_stable_ids_categories_and_sheet_area_distinction():
    catalog = preset_catalog()
    raw = json.loads(files("cet").joinpath("data/formats.json").read_text(encoding="utf-8"))
    assert catalog == load_catalog(raw)
    assert len(catalog) == 14
    for key, p in catalog.items():
        assert p.id == key and p.category in CATEGORIES
        assert p.active_width_mm > 0 and p.active_height_mm > 0
        assert p.as_format().diagonal_mm > 0
        assert p.notes and p.source and p.units == "mm"
    sheets = {p.legacy_name: p for p in catalog.values() if p.category == "sheet_film"}
    assert set(sheets) == {"4 × 5 sheet", "5 × 7 sheet", "8 × 10 sheet"}
    p = sheets["5 × 7 sheet"]
    assert (p.nominal_width_mm, p.nominal_height_mm) == (177.8, 127)
    assert (p.active_width_mm, p.active_height_mm) == (170, 120)
    assert "representative" in p.display_name.lower()
    assert format_record(p.as_format())["preset_id"] == p.id
    assert format_record(Format("Custom", 119, 169))["category"] == "custom"
    # Rotation is legitimate: do not force all image areas to be landscape.
    assert replace(p, active_width_mm=120, active_height_mm=170).active_width_mm == 120
    with pytest.raises(ValueError, match="Duplicate"):
        load_catalog({"schema_version": 2, "presets": [asdict(p), asdict(p)]})


@pytest.mark.parametrize("changes", [
    {"active_width_mm": 0}, {"active_height_mm": math.nan}, {"active_width_mm": math.inf},
    {"active_width_mm": 500}, {"id": "Unstable Name"}, {"category": "mystery"},
    {"nominal_width_mm": None}, {"units": "in"},
])
def test_preset_sanity_rejects_inconsistent_definitions(changes):
    p = next(p for p in preset_catalog().values() if p.legacy_name == "5 × 7 sheet")
    with pytest.raises(ValueError):
        replace(p, **changes)


@pytest.mark.parametrize("k,n,expected", [
    (0, 1000, (0, .003826758485555124)),
    (1, 1000, (.000176546370626078, .005642558597957935)),
    (50, 100, (.4038315303659956, .5961684696340044)),
    (0, 1, (0, .7934506856227626)),
    (1, 1, (.20654931437723745, 1)),
])
def test_wilson_known_cases(k, n, expected):
    assert wilson_interval(k, n) == pytest.approx(expected)


def test_wilson_large_sample_boundaries_and_percentage_resolution():
    lo, hi = wilson_interval(0, 250000)
    assert lo == 0 and 0 < hi < wilson_interval(0, 1000)[1]
    assert wilson_interval(250000, 250000) == pytest.approx((1 - hi, 1))
    assert percentage(hi, 250000) == "0.0015%"
    assert percentage(0, 1000) == "0.0%"
    assert percentage(1 / 1000, 1000) == "0.1%"
    for k, n in ((-1, 100), (101, 100), (True, 100), (0, 0), (1.5, 10)):
        with pytest.raises(ValueError):
            wilson_interval(k, n)


def test_shared_chain_distribution_meanings_and_confidence():
    chain = DimensionChain.from_records(DEFAULT_ROWS, 70)
    assert all(c.distribution == "Uniform" for c in chain.components)
    assert chain.summary() == stack_up(chain.components, 70)
    assert chain.summary()["bounded_worst_case"]
    assert chain.summary()["stated_tolerance_mm"] == pytest.approx(.1)
    assert chain.summary()["analytic_sigma_mm"] == pytest.approx(math.sqrt(.0038 / 3))
    result, samples = chain.simulate(-.1, .1, 1000, 42)
    assert result["out_of_spec_count"] == 0
    assert result["failure_probability_ci95_high"] > 0
    assert np.max(np.abs(samples)) <= .1
    normal = DimensionChain((Component("A", 10, .3, 1, "Normal (±3σ)"),), 10)
    result, samples = normal.simulate(-.3, .3, 100000, 42)
    assert not result["bounded_worst_case"]
    assert result["analytic_sigma_mm"] == pytest.approx(.1)
    assert np.count_nonzero(np.abs(samples) > .3) > 0
    assert samples.std(ddof=1) == pytest.approx(.1, rel=.02)
    deterministic = DimensionChain((Component("A", 10),), 10)
    r, _ = deterministic.simulate(1, 2, 1000, 0)
    assert r["out_of_spec_count"] == 1000
    assert r["failure_probability_ci95_high"] == 1
    assert r["failure_probability_ci95_low"] < 1


@pytest.mark.parametrize("call", [
    lambda: Component(None, 1), lambda: Component(123, 1), lambda: Component("  ", 1),
    lambda: Component("A", 1, sign=True), lambda: Component("A", 1, sign=np.bool_(True)),
    lambda: Component("A", math.nan), lambda: Component("A", 1, math.inf),
    lambda: Component("A", True), lambda: Format("huge", 1e308, 1e308),
    lambda: stack_up([Component("A", 1e308), Component("B", 1e308)], 0),
    lambda: comparison_focals("1e309"), lambda: comparison_focals("1e200"),
    lambda: comparison_focals("nan"), lambda: comparison_focals("inf"),
    lambda: comparison_focals("50," * 100000),
])
def test_related_invalid_inputs_fail_cleanly(call):
    with pytest.raises(ValueError):
        call()


@pytest.mark.parametrize("theme", ["Light", "Dark"])
def test_all_chart_factories_use_session_palette_without_global_mutation(theme):
    from matplotlib import rcParams
    before = dict(rcParams)
    dark = theme == "Dark"
    fmt = Format("Example", 48, 36)
    figs = [charts.canvas(dark)[0], charts.format_rectangles([fmt], dark),
            charts.fov_plot(fmt, 80, dark), charts.coverage_plot(fmt, 100, 0, 0, dark),
            charts.stack_plot(DimensionChain.from_records(DEFAULT_ROWS, 70).components, 70, dark),
            charts.histogram(np.array([-.02, 0, .03]), -.1, .1, dark)]
    p = palette(theme)
    for fig in figs:
        assert fig.get_facecolor() == to_rgba(p["secondaryBackgroundColor"])
        assert fig.axes[0].get_facecolor() == to_rgba(p["secondaryBackgroundColor"])
        assert fig.axes[0].xaxis.label.get_color() == p["textColor"]
        fig.clear()
    assert dict(rcParams) == before
    assert p["backgroundColor"] in theme_css(theme)
    assert json.dumps(p) in native_theme_html(theme)
