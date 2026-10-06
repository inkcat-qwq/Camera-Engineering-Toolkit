"""Paraxial/rectilinear models. All internal lengths are millimetres.

Object distances are measured from the lens principal plane, not sensor plane.
See docs/MODELS.md for derivations, assumptions and sign conventions.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from importlib.resources import files
import json
from numbers import Integral

import numpy as np


def finite(value: float, name: str, *, positive=False, nonnegative=False) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number.") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite.")
    if positive and result <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    if nonnegative and result < 0:
        raise ValueError(f"{name} cannot be negative.")
    return result


def integer(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, Integral) or not low <= value <= high:
        raise ValueError(f"{name} must be an integer from {low:,} to {high:,}.")
    return int(value)


@dataclass(frozen=True)
class Format:
    name: str
    width_mm: float
    height_mm: float
    note: str = "Custom active image area"

    def __post_init__(self):
        object.__setattr__(self, "width_mm", finite(self.width_mm, "Width", positive=True))
        object.__setattr__(self, "height_mm", finite(self.height_mm, "Height", positive=True))

    @property
    def diagonal_mm(self):
        return math.hypot(self.width_mm, self.height_mm)

    def dimension(self, axis):
        if axis not in ("Horizontal", "Vertical", "Diagonal"):
            raise ValueError("Axis must be Horizontal, Vertical or Diagonal.")
        return {"Horizontal": self.width_mm, "Vertical": self.height_mm,
                "Diagonal": self.diagonal_mm}[axis]


def presets():
    data = json.loads(files("cet").joinpath("data/formats.json").read_text(encoding="utf-8"))
    return {item["name"]: Format(**item) for item in data}


def sensor(fmt: Format, pixels_x=None, pixels_y=None):
    result = {"width_mm": fmt.width_mm, "height_mm": fmt.height_mm,
              "diagonal_mm": fmt.diagonal_mm, "area_mm2": fmt.width_mm * fmt.height_mm,
              "aspect_ratio": fmt.width_mm / fmt.height_mm,
              "crop_factor_135_diagonal": math.hypot(36, 24) / fmt.diagonal_mm}
    if (pixels_x is None) != (pixels_y is None):
        raise ValueError("Provide both pixel dimensions, or neither.")
    if pixels_x is not None:
        x = integer(pixels_x, "Horizontal pixels", 1, 1_000_000)
        y = integer(pixels_y, "Vertical pixels", 1, 1_000_000)
        result.update(megapixels=x * y / 1e6,
                      pixel_pitch_x_um=1000 * fmt.width_mm / x,
                      pixel_pitch_y_um=1000 * fmt.height_mm / y,
                      pixel_density_px_per_mm2=x * y / result["area_mm2"])
    return result


def fov(fmt: Format, focal_mm):
    focal = finite(focal_mm, "Focal length", positive=True)
    return {f"{axis.lower()}_deg": math.degrees(2 * math.atan(fmt.dimension(axis) / (2 * focal)))
            for axis in ("Horizontal", "Vertical", "Diagonal")}


def focal_for_fov(fmt: Format, angle_deg, axis="Horizontal"):
    angle = finite(angle_deg, "Target angle", positive=True)
    if angle >= 180:
        raise ValueError("Target angle must be below 180 degrees.")
    return fmt.dimension(axis) / (2 * math.tan(math.radians(angle) / 2))


def equivalence(source: Format, target: Format, focal_mm, f_number, axis="Diagonal"):
    focal = finite(focal_mm, "Focal length", positive=True)
    aperture = finite(f_number, "F-number", positive=True)
    ratio = target.dimension(axis) / source.dimension(axis)
    return {"scale_target_over_source": ratio, "equivalent_focal_mm": focal * ratio,
            "equivalent_dof_f_number": aperture * ratio,
            "source_angle_deg": fov(source, focal)[f"{axis.lower()}_deg"],
            "target_angle_deg": fov(target, focal * ratio)[f"{axis.lower()}_deg"]}


def depth_of_field(focal_mm, f_number, distance_mm, coc_mm):
    f = finite(focal_mm, "Focal length", positive=True)
    n = finite(f_number, "F-number", positive=True)
    s = finite(distance_mm, "Focus distance", positive=True)
    c = finite(coc_mm, "Circle of confusion", positive=True)
    if s <= f:
        raise ValueError("Focus distance must exceed focal length (measured from the principal plane).")
    q = f * f / (n * c)
    h = q + f
    near = s * q / (q + s - f)
    far = math.inf if s >= h else s * q / (q - s + f)
    return {"hyperfocal_mm": h, "near_mm": near, "far_mm": far,
            "total_dof_mm": far - near, "front_dof_mm": s - near, "rear_dof_mm": far - s}


def bellows(focal_mm, extension_mm):
    f = finite(focal_mm, "Focal length", positive=True)
    v = finite(extension_mm, "Total extension", positive=True)
    if v < f:
        raise ValueError("Total extension must be at least the focal length.")
    m = v / f - 1
    factor = (v / f) ** 2
    return {"magnification": m, "object_distance_mm": math.inf if m == 0 else f * (1 + 1 / m),
            "exposure_factor": factor, "exposure_compensation_stops": math.log2(factor),
            "effective_f_number_multiplier": v / f}


def coverage(fmt: Format, circle_mm, shift_x_mm=0, shift_y_mm=0):
    diameter = finite(circle_mm, "Image circle", positive=True)
    dx = finite(shift_x_mm, "Horizontal shift")
    dy = finite(shift_y_mm, "Vertical shift")
    required = 2 * math.hypot(fmt.width_mm / 2 + abs(dx), fmt.height_mm / 2 + abs(dy))
    margin = (diameter - required) / 2
    return {"required_circle_mm": required, "radial_margin_mm": margin,
            "covered": margin >= -1e-10,
            "centered_radial_margin_mm": (diameter - fmt.diagonal_mm) / 2}


@dataclass(frozen=True)
class Component:
    name: str
    nominal_mm: float
    tolerance_mm: float = 0
    sign: int = 1
    distribution: str = "Uniform"

    def __post_init__(self):
        if not str(self.name).strip():
            raise ValueError("Each component needs a name.")
        object.__setattr__(self, "nominal_mm", finite(self.nominal_mm, "Nominal dimension", nonnegative=True))
        object.__setattr__(self, "tolerance_mm", finite(self.tolerance_mm, "Tolerance", nonnegative=True))
        if self.sign not in (-1, 1):
            raise ValueError("Component sign must be +1 or -1.")
        if self.distribution not in ("Uniform", "Normal (±3σ)"):
            raise ValueError("Distribution must be Uniform or Normal (±3σ).")

    @property
    def sigma_mm(self):
        return self.tolerance_mm / (math.sqrt(3) if self.distribution == "Uniform" else 3)


def check_components(components):
    if not 1 <= len(components) <= 100:
        raise ValueError("Provide between 1 and 100 components.")


def stack_up(components: list[Component], target_mm):
    check_components(components)
    target = finite(target_mm, "Target sensor plane")
    actual = math.fsum(c.sign * c.nominal_mm for c in components)
    tol = math.fsum(c.tolerance_mm for c in components)
    sigma = math.sqrt(math.fsum(c.sigma_mm ** 2 for c in components))
    return {"target_mm": target, "actual_mm": actual, "error_mm": actual - target,
            "required_correction_mm": target - actual,
            "tolerance_envelope_min_mm": actual - tol, "tolerance_envelope_max_mm": actual + tol,
            "analytic_sigma_mm": sigma}


def monte_carlo(components: list[Component], target_mm, lower_error_mm, upper_error_mm,
                samples=50_000, seed=42):
    stats = stack_up(components, target_mm)
    low = finite(lower_error_mm, "Lower error limit")
    high = finite(upper_error_mm, "Upper error limit")
    if low >= high:
        raise ValueError("Lower error limit must be below upper error limit.")
    count = integer(samples, "Samples", 100, 250_000)
    seed = integer(seed, "Seed", 0, 2**32 - 1)
    rng = np.random.default_rng(seed)
    totals = np.zeros(count)
    for component in components:
        t = component.tolerance_mm
        noise = (rng.uniform(-t, t, count) if component.distribution == "Uniform"
                 else rng.normal(0, t / 3, count))
        totals += component.sign * (component.nominal_mm + noise)
    errors = totals - stats["target_mm"]
    p025, p975 = np.quantile(errors, [0.025, 0.975])
    outside = int(np.count_nonzero((errors < low) | (errors > high)))
    result = {**stats, "samples": count, "seed": seed, "mean_error_mm": float(errors.mean()),
              "sample_std_mm": float(errors.std(ddof=1)), "p025_error_mm": float(p025),
              "p975_error_mm": float(p975), "lower_error_limit_mm": low, "upper_error_limit_mm": high,
              "out_of_spec_count": outside, "out_of_spec_fraction": outside / count,
              "yield_fraction": 1 - outside / count}
    return result, errors


def component_records(components):
    return [asdict(c) for c in components]
