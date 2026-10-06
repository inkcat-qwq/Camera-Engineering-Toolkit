import math
import json
import numpy as np
import pytest
from cet.core import (Component, Format, bellows, coverage, depth_of_field, equivalence,
                      focal_for_fov, fov, monte_carlo, presets, sensor, stack_up)
from cet.export import report, to_csv, to_json


FF = Format("135", 36, 24)
MF = Format("48x36", 48, 36)


def test_reference_sensor_geometry():
    result = sensor(MF, 8000, 6000)
    assert result["diagonal_mm"] == 60
    assert result["pixel_pitch_x_um"] == 6
    assert result["pixel_pitch_y_um"] == 6
    assert result["megapixels"] == 48
    assert result["crop_factor_135_diagonal"] == pytest.approx(.721110255)


def test_reference_fov():
    assert fov(MF, 80)["horizontal_deg"] == pytest.approx(33.39848846798724)
    assert fov(Format("square", 100, 100), 50)["horizontal_deg"] == 90


@pytest.mark.parametrize("axis", ["Horizontal", "Vertical", "Diagonal"])
@pytest.mark.parametrize("focal", [1, 24, 80, 300, 2000])
def test_fov_inverse_round_trip(axis, focal):
    angle = fov(MF, focal)[axis.lower() + "_deg"]
    assert focal_for_fov(MF, angle, axis) == pytest.approx(focal)


def test_equivalence_axis_and_aspect_ratio():
    assert equivalence(MF, FF, 80, 4, "Horizontal")["equivalent_focal_mm"] == 60
    assert equivalence(MF, FF, 80, 4, "Vertical")["equivalent_focal_mm"] == pytest.approx(53.333333333)
    r = equivalence(MF, FF, 80, 4)
    assert r["source_angle_deg"] == pytest.approx(r["target_angle_deg"])
    assert r["equivalent_focal_mm"] == pytest.approx(57.688820407)


def test_dof_limits_produce_requested_geometric_blur():
    f, n, s, coc = 50, 8, 3000, .03
    r = depth_of_field(f, n, s, coc)
    image_at_focus = 1 / (1 / f - 1 / s)
    for limit in (r["near_mm"], r["far_mm"]):
        image = 1 / (1 / f - 1 / limit)
        blur = f / n * abs(image_at_focus - image) / image
        assert blur == pytest.approx(coc)
    assert r["near_mm"] < s < r["far_mm"]
    assert r["total_dof_mm"] == r["far_mm"] - r["near_mm"]


def test_hyperfocal_infinity_boundary():
    h = 50**2 / (8 * .03) + 50
    at = depth_of_field(50, 8, h, .03)
    assert math.isinf(at["far_mm"])
    assert at["near_mm"] == pytest.approx(h / 2)
    assert math.isfinite(depth_of_field(50, 8, h - .001, .03)["far_mm"])
    assert math.isinf(depth_of_field(50, 8, h + .001, .03)["far_mm"])


def test_macro_and_infinity_bellows():
    r = bellows(150, 300)
    assert r["magnification"] == 1
    assert r["exposure_factor"] == 4
    assert r["exposure_compensation_stops"] == 2
    assert r["object_distance_mm"] == 300
    assert math.isinf(bellows(150, 150)["object_distance_mm"])


def test_shifted_corner_coverage_and_symmetry():
    assert coverage(MF, 60)["covered"]
    assert not coverage(MF, 60, 1, 0)["covered"]
    assert coverage(MF, 100, 10, 5) == coverage(MF, 100, -10, -5)
    assert coverage(MF, 100, 10, 5)["required_circle_mm"] == pytest.approx(2 * math.hypot(34, 23))


def test_signed_stack_and_correction():
    cs = [Component("body", 40, .1), Component("adapter", 10, .02), Component("recess", 2, .03, -1)]
    r = stack_up(cs, 50)
    assert r["actual_mm"] == 48
    assert r["error_mm"] == -2
    assert r["required_correction_mm"] == 2
    assert r["tolerance_envelope_min_mm"] == pytest.approx(47.85)


def test_uniform_sampling_reproducible_with_analytic_sigma():
    cs = [Component("A", 10, .1), Component("B", 5, .06, -1)]
    result, errors = monte_carlo(cs, 5, -.1, .1, 100000, 42)
    _, repeat = monte_carlo(cs, 5, -.1, .1, 100000, 42)
    assert np.array_equal(errors, repeat)
    assert abs(errors.mean()) < .001
    assert result["sample_std_mm"] == pytest.approx(math.sqrt((.1**2 + .06**2) / 3), rel=.015)
    assert errors.min() >= -.16 and errors.max() <= .16
    assert result["out_of_spec_count"] == int(np.count_nonzero(np.abs(errors) > .1))
    assert result["yield_fraction"] + result["out_of_spec_fraction"] == 1


def test_normal_sigma_and_signed_bias():
    cs = [Component("A", 10, .3, -1, "Normal (±3σ)")]
    r, errors = monte_carlo(cs, -10.05, -.05, .15, 100000, 17)
    assert r["mean_error_mm"] == pytest.approx(.05, abs=.002)
    assert r["sample_std_mm"] == pytest.approx(.1, rel=.01)
    assert r["out_of_spec_fraction"] == pytest.approx(.3173, abs=.01)
    assert r["p025_error_mm"] == pytest.approx(-.146, abs=.003)


def test_deterministic_zero_tolerance_and_inclusive_limits():
    r, errors = monte_carlo([Component("A", 10)], 9, 0, 1, 100, 0)
    assert r["sample_std_mm"] == 0
    assert r["out_of_spec_count"] == 0
    assert np.all(errors == 1)


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf")])
def test_invalid_dimensions(value):
    with pytest.raises(ValueError):
        Format("Invalid", value, 24)
    with pytest.raises(ValueError):
        fov(FF, value)


@pytest.mark.parametrize("angle", [0, -1, 180, 200, float("nan")])
def test_invalid_fov_angle(angle):
    with pytest.raises(ValueError):
        focal_for_fov(FF, angle)


@pytest.mark.parametrize("call", [
    lambda: sensor(FF, 100, None), lambda: sensor(FF, 100.5, 100),
    lambda: depth_of_field(50, 8, 50, .03), lambda: depth_of_field(50, 0, 1000, .03),
    lambda: bellows(150, 149), lambda: coverage(FF, 0), lambda: stack_up([], 0),
    lambda: Component("A", 1, -.1), lambda: Component("A", 1, .1, 0),
    lambda: Component("A", 1, .1, 1, "unknown"), lambda: Component("", 1),
    lambda: monte_carlo([Component("A", 1)], 1, 1, -1),
    lambda: monte_carlo([Component("A", 1)], 1, -1, 1, 99),
    lambda: monte_carlo([Component("A", 1)], 1, -1, 1, 250001),
    lambda: monte_carlo([Component("A", 1)], 1, -1, 1, 100, -1),
])
def test_invalid_models(call):
    with pytest.raises(ValueError):
        call()


def test_presets_are_packaged_and_valid():
    data = presets()
    assert len(data) >= 14
    assert data["4 × 5 sheet"].width_mm == 120
    assert all(f.diagonal_mm > 0 and f.note for f in data.values())


def test_export_infinity_units_inputs_and_formula_safety():
    payload = report("test", {"name": "=SUM(A1:A2)", "focal_mm": 50}, {"far_mm": math.inf})
    parsed = json.loads(to_json(payload))
    assert parsed["results"]["far_mm"] == "Infinity"
    assert parsed["inputs"]["focal_mm"] == 50
    assert "'=SUM(A1:A2)" in to_csv(payload)
