# Models and conventions

## Units and image area

Internal distances are millimetres. The DOF screen accepts focus distance in metres and converts it. Angles are degrees in the interface. Pixel pitch is micrometres; density is pixels per square millimetre. Width and height describe the active rectangular image area, not a sensor package, film outside the gate or a lens mount.

Preset dimensions are illustrative rounded/representative areas. They are not a database of verified camera models. For fabrication or exact matching, enter measured active dimensions. Format and pixel arrays need not have the same aspect ratio; unequal X/Y pitch is reported rather than silently assuming square pixels.

For width W and height H: diagonal d = sqrt(W² + H²); area A = WH; aspect = W/H; diagonal crop = sqrt(36² + 24²)/d. Pixel pitch X = 1000W / horizontal pixel count, with the analogous Y expression. Density = total pixels / A.

## Rectilinear angular field of view

For format dimension d along the chosen axis and focal length f:

```text
angle = 2 atan(d / (2f))
f = d / (2 tan(angle / 2))
```

The inverse requires 0 < angle < 180°. It assumes a rectilinear lens at infinity without distortion or focus breathing. The field diagram is a geometric projection of that angle onto a plane 1 m from the projection centre; it is not a finite-conjugate lens calculation.

## Lens equivalence

For an explicitly selected axis, k = target dimension / source dimension. The target focal length is k times the source focal length. Different aspect ratios cannot generally match horizontal, vertical and diagonal angles simultaneously.

The displayed DOF-equivalent aperture is k times the source f-number. This is an approximate equal-viewpoint/equal-output comparison with CoC scaled by the same ratio and subject distances large relative to focal length. It does not change the exposure f-number rule and is not a transmission or sensor-noise equivalence claim.

## Depth of field

Focus and object distances are measured from the lens principal plane. Let f be focal length, N be f-number, s > f be focus distance and c > 0 be permitted image-plane blur diameter:

```text
q = f² / (N c)
hyperfocal H = q + f
near = s q / (q + s - f)
far = s q / (q - s + f), for s < H
far = infinity, for s >= H
```

This uses a thin lens with entrance/exit pupil magnification 1. The expressions follow from image distance v = fs/(s-f) and cone blur c = (f/N)|v_s-v_u|/v_u. At s = H, the near limit is H/2 and the far limit is infinity. Tests independently substitute both computed limits into the blur equation. Some photographic calculators replace q with H as a distant-subject approximation; results can differ slightly.

The optional default c = diagonal/1500 is a viewing convention, not a sensor resolving-power limit. Format affects DOF only through the chosen CoC in this model. Custom CoC allows another output size, viewing distance or acceptance criterion. Diffraction, pupil asymmetry, aberrations, breathing and sensor cover glass are excluded.

## Bellows

The extension v is total image distance from the rear principal plane, not extra draw beyond the infinity position. For v >= f:

```text
m = v/f - 1
object distance u = f(1 + 1/m), or infinity when m = 0
exposure factor = (v/f)² = (1+m)²
stops = log2(exposure factor)
effective f-number multiplier = v/f
```

Pupil magnification is assumed to be 1. Real asymmetric lenses may require a pupil correction; internal focusing may change the effective focal length. Exposure compensation is positive added exposure. Reciprocity failure is not included.

## Image circle and movements

For an image rectangle shifted by dx and dy relative to the optical axis, the farthest corner radius is:

```text
r_required = sqrt((W/2 + |dx|)² + (H/2 + |dy|)²)
required image circle = 2 r_required
radial margin = supplied image-circle diameter / 2 - r_required
```

All corners fit when margin >= 0 (with a 1e-10 mm numerical boundary tolerance). The user must supply image circle at the actual aperture and focus; the model does not automatically enlarge an infinity-rated circle for close focus. Tilt, swing, mechanical vignetting and image quality within the circle are not assessed.

## Mechanical stack

Lens flange is the Z = 0 datum. Positive Z points toward the sensor. Each component contributes sign × nominal length; nominal lengths are nonnegative and sign is +1 or -1. Recesses can subtract length if their datums follow that convention.

```text
actual sensor plane = sum(sign_i × nominal_i)
plane error = actual - target flange distance
required net correction = target - actual
stated tolerance envelope = actual ± sum(tolerance_i)
```

Positive plane error places the sensor too far from the flange; positive correction adds net spacing. A negative correction requires shortening the chain, not a negative-thickness shim. Example dimensions are hypothetical, not certified mounting dimensions. Back width and height are recorded envelope dimensions; they are not used for collision, mounting or image coverage analysis.

## Monte Carlo

Each component is independent. Uniform errors are sampled between -t and +t with sigma = t/sqrt(3). For **Normal (±3σ)**, t is three standard deviations and the distribution is unbounded: this is a process model, not hard acceptance truncation. The stated tolerance envelope therefore is not a guaranteed bound for normal sampling.

NumPy `default_rng(seed)` draws one component at a time into a summed vector, avoiding a samples-by-components allocation. Sample error is simulated stack minus target. Results report sample standard deviation (ddof = 1), empirical 2.5th/97.5th percentiles, and fraction strictly below/above the error limits (limits are inclusive). The 95% interval describes simulated assemblies, not confidence in the estimated mean. A seed reproduces results with the same input ordering and compatible NumPy implementation. Exact draws are not guaranteed across dependency changes.

Analytic sigma is sqrt(sum(sigma_i²)); signs do not change independent variances. Between 1 and 100 components and 100–250,000 samples are accepted by the library; the interface offers five sample sizes. Changing any input invalidates displayed simulation results until rerun. Zero observed failures is not evidence of zero true failure probability. Correlation, bias drift, non-linear optical sensitivity and process capability indices are outside v1.0.

## References

- [Edmund Optics: Understanding focal length and field of view](https://www.edmundoptics.com/knowledge-center/application-notes/imaging/understanding-focal-length-and-field-of-view/) — optical terminology and field of view.
- [Edmund Optics: Imaging fundamentals](https://www.edmundoptics.com/knowledge-center/application-notes/imaging/6-fundamental-parameters-of-an-imaging-system/) — image-system parameter definitions.
- [NumPy random Generator](https://numpy.org/doc/stable/reference/random/generator.html) — generator interface used for simulations.

The algebraic models above are stated explicitly so their behavior can be checked without relying on undocumented camera-specific assumptions.
