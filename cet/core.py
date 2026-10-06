"""Paraxial/rectilinear models. All internal lengths are millimetres.

The base DoF equations use principal-plane distance; dof_with_datum wraps them
with explicit image-plane or principal-plane measurement semantics.
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
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a number.")
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
        if not math.isfinite(self.width_mm * self.height_mm):
            raise ValueError("Image area is too large for this model.")

    @property
    def diagonal_mm(self):
        return math.hypot(self.width_mm, self.height_mm)

    def dimension(self, axis):
        if axis not in ("Horizontal", "Vertical", "Diagonal"):
            raise ValueError("Axis must be Horizontal, Vertical or Diagonal.")
        return {"Horizontal": self.width_mm, "Vertical": self.height_mm,
                "Diagonal": self.diagonal_mm}[axis]


def presets():
    # Legacy name-keyed calculation interface; metadata lives in the catalog.
    from .formats import preset_catalog
    return {item.legacy_name: item.as_format() for item in preset_catalog().values()}


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
    try:
        q = f * f / (n * c)
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Parameters exceed the numerical range of this model.") from exc
    if not math.isfinite(q) or q <= 0:
        raise ValueError("Parameters exceed the numerical range of this model.")
    h = q + f
    near = s * q / (q + s - f)
    far = math.inf if s >= h else s * q / (q - s + f)
    if not all(math.isfinite(v) for v in (h, near)) or (s < h and not math.isfinite(far)):
        raise ValueError("Parameters exceed the numerical range of this model.")
    return {"hyperfocal_mm": h, "near_mm": near, "far_mm": far,
            "total_dof_mm": far - near, "front_dof_mm": s - near, "rear_dof_mm": far - s}


DISTANCE_DATUMS = ("Image / sensor / film plane", "Front principal plane")


def image_distance(focal_mm, object_mm):
    """Focused image conjugate v; distances from coincident thin-lens planes."""
    f = finite(focal_mm, "Focal length", positive=True)
    s = finite(object_mm, "Focus distance", positive=True)
    if s <= f:
        raise ValueError("Focus distance must exceed focal length (measured from the principal plane).")
    return finite(f / (1 - f / s), "Image distance", positive=True)


def principal_to_image_distance(focal_mm, object_mm):
    """Subject-to-image-plane separation D = s + v at this focus setting."""
    v = image_distance(focal_mm, object_mm)
    return finite(float(object_mm) + v, "Subject-to-image-plane distance", positive=True)


def image_to_principal_distance(focal_mm, total_mm):
    """Photographic branch s >= 2f (magnification <= 1), including 1:1.

    D = s + fs/(s-f) has two roots. Select the larger object conjugate.
    Use a dimensionless discriminant to avoid overflow at long distances.
    """
    f = finite(focal_mm, "Focal length", positive=True)
    total = finite(total_mm, "Subject-to-image-plane distance", positive=True)
    if total / f < 4:
        raise ValueError("Subject-to-image-plane distance must be at least 4 × focal length in this thin-lens model.")
    return total * (0.5 + 0.5 * math.sqrt(1 - 4 * (f / total)))


def dof_with_datum(focal_mm, f_number, distance_mm, coc_mm,
                   datum=DISTANCE_DATUMS[0]):
    """Presentation model around the unchanged principal-plane DoF equations.

    Near/far endpoints shift by the CURRENT focused image conjugate, not by
    refocusing at each endpoint. Hyperfocal is a different focus setting and
    uses its own conjugate. DoF widths are translation invariant.
    """
    if datum not in DISTANCE_DATUMS:
        raise ValueError("Unknown distance datum.")
    distance_mm = finite(distance_mm, "Focus distance", positive=True)
    s = (image_to_principal_distance(focal_mm, distance_mm)
         if datum == DISTANCE_DATUMS[0] else finite(distance_mm, "Focus distance", positive=True))
    v = image_distance(focal_mm, s)
    result = depth_of_field(focal_mm, f_number, s, coc_mm)
    h = result["hyperfocal_mm"]
    image_mode = datum == DISTANCE_DATUMS[0]
    # Image-plane mode only covers the s >= 2f branch. If H < 2f, every
    # accessible focus setting already reaches infinity: the first is 1:1.
    hyper_setting = principal_to_image_distance(focal_mm, max(h, 2 * float(focal_mm))) if image_mode else h
    if image_mode and distance_mm >= hyper_setting:
        # Protect an exact converted hyperfocal boundary from inverse-roundoff.
        result.update(far_mm=math.inf, total_dof_mm=math.inf, rear_dof_mm=math.inf)
    offset = v if image_mode else 0.0
    return {**result, "near_mm": result["near_mm"] + offset,
            "far_mm": result["far_mm"] + offset, "hyperfocal_mm": hyper_setting,
            "distance_datum": datum, "focus_distance_mm": float(distance_mm),
            "principal_object_distance_mm": s, "focused_image_distance_mm": v,
            "principal_hyperfocal_mm": h,
            "hyperfocal_branch_limited": image_mode and h < 2 * float(focal_mm)}


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
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Each component needs a name.")
        object.__setattr__(self, "nominal_mm", finite(self.nominal_mm, "Nominal dimension", nonnegative=True))
        object.__setattr__(self, "tolerance_mm", finite(self.tolerance_mm, "Tolerance", nonnegative=True))
        if isinstance(self.sign, (bool, np.bool_)) or self.sign not in (-1, 1):
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
    try:
        actual = math.fsum(c.sign * c.nominal_mm for c in components)
        tol = math.fsum(c.tolerance_mm for c in components)
    except OverflowError as exc:
        raise ValueError("Parameters exceed the numerical range of this model.") from exc
    sigma = math.hypot(*(c.sigma_mm for c in components))
    if not all(math.isfinite(v) for v in (actual, tol, sigma, actual - target, actual + tol, actual - tol)):
        raise ValueError("Parameters exceed the numerical range of this model.")
    return {"target_mm": target, "actual_mm": actual, "error_mm": actual - target,
            "required_correction_mm": target - actual,
            "tolerance_envelope_min_mm": actual - tol, "tolerance_envelope_max_mm": actual + tol,
            "analytic_sigma_mm": sigma, "stated_tolerance_mm": tol,
            "bounded_worst_case": all(c.distribution == "Uniform" or c.tolerance_mm == 0 for c in components)}


def wilson_interval(failures, samples):
    """Two-sided 95% Wilson score interval for independent Bernoulli trials."""
    n = integer(samples, "Samples", 1, 2**53)
    k = integer(failures, "Failures", 0, n)
    z = 1.959963984540054
    p = k / n
    z2n = z * z / n
    center = (p + z2n / 2) / (1 + z2n)
    half = z * math.sqrt(p * (1 - p) / n + z2n / (4 * n)) / (1 + z2n)
    return (0.0 if k == 0 else max(0.0, center - half),
            1.0 if k == n else min(1.0, center + half))


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
    ci_low, ci_high = wilson_interval(outside, count)
    result = {**stats, "samples": count, "seed": seed, "mean_error_mm": float(errors.mean()),
              "sample_std_mm": float(errors.std(ddof=1)), "p025_error_mm": float(p025),
              "p975_error_mm": float(p975), "lower_error_limit_mm": low, "upper_error_limit_mm": high,
              "out_of_spec_count": outside, "out_of_spec_fraction": outside / count,
              "yield_fraction": 1 - outside / count,
              "failure_probability_ci95_low": ci_low, "failure_probability_ci95_high": ci_high,
              "failure_probability_ci_method": "Wilson score, two-sided 95%"}
    return result, errors


def component_records(components):
    return [asdict(c) for c in components]
