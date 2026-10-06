# Models and conventions — v1.2.0

## Units and image area

Internal distances are millimetres. The DOF screen accepts focus distance in metres and converts it. Angles are degrees in the interface. Pixel pitch is micrometres; density is pixels per square millimetre. Width and height describe the active rectangular image area, not a sensor package, film outside the gate or a lens mount.

Preset dimensions are illustrative rounded/representative areas. They are not a database of verified camera models. For fabrication or exact matching, enter measured active dimensions. Format and pixel arrays need not have the same aspect ratio; unequal X/Y pitch is reported rather than silently assuming square pixels.

Preset schema 2 separates stable ID, display name, category, nominal dimensions, active dimensions, units, notes and provenance. Geometry always uses **active** dimensions. Sheet dimensions (landscape) are 127×101.6 mm for 4×5, 177.8×127 mm for 5×7, and 254×203.2 mm for 8×10. Their illustrative openings are 120×96, 170×120 and 244×193 mm respectively; these are not universal holder specifications. Rotation is allowed; there is no rule that custom width must exceed height.

Display formatting does not alter stored precision. Lengths below 1 m use mm, with additional precision for small values; longer distances use m and very large/tiny values may use scientific notation. Infinity is displayed as ∞. Small angles preserve significant figures and signed zero is normalized.

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

The base equations and existing `depth_of_field` library function continue to use **front principal-plane object distance**. Let f be focal length, N be f-number, s > f be focus distance and c > 0 be permitted image-plane blur diameter:

```text
q = f² / (N c)
hyperfocal H = q + f
near = s q / (q + s - f)
far = s q / (q - s + f), for s < H
far = infinity, for s >= H
```

This uses a thin lens with entrance/exit pupil magnification 1. The expressions follow from image distance v = fs/(s-f) and cone blur c = (f/N)|v_s-v_u|/v_u. At s = H, the near limit is H/2 and the far limit is infinity. Tests independently substitute both computed limits into the blur equation. Some photographic calculators replace q with H as a distant-subject approximation; results can differ slightly.

The UI defaults to **Image / sensor / film plane** because that is the usual camera measurement datum. With coincident thin-lens principal planes, the subject-to-image-plane distance is D = s + v. The wrapper converts it using:

```text
v = f s / (s - f)
D = s + v
s = (D + sqrt(D² - 4 D f)) / 2
```

The larger root selects s ≥ 2f, magnification ≤1. D must be ≥4f; equality is the 1:1 case. The smaller root describes a different optical setup with magnification >1 and is not inferred from a tape-measured D. Explicit principal-plane mode remains available for s > f. A real lens can have separated principal planes; this ideal conversion does not estimate that separation or internal focusing.

Near/far endpoints in image-plane mode are the principal-plane endpoints **plus the current focused v**. We do not refocus separately at each limit. Front/rear/total DoF widths are invariant to the datum translation. Hyperfocal is a different focus setting, so it converts as H + v(H). In the exceptional case H < 2f, infinity is already acceptable at the closest focus on this branch; the UI labels the reported D = 4f setting accordingly.

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

Camera Design and Monte Carlo share `DimensionChain` and one session chain/target. The editor seed is only the baseline for Streamlit edit deltas, not a separate workflow model. A changed chain or target invalidates old simulation results. With entirely bounded Uniform components the sum of tolerances is a worst-case bound; any nonzero Normal component makes it a stated envelope, not a guaranteed bound. RSS sigma combines each component's distribution-specific standard deviation, not raw tolerance values.

## Monte Carlo

Each component is independent. Uniform errors are sampled between -t and +t with sigma = t/sqrt(3). For **Normal (±3σ)**, t is three standard deviations and the distribution is unbounded: this is a process model, not hard acceptance truncation. The stated tolerance envelope therefore is not a guaranteed bound for normal sampling.

NumPy `default_rng(seed)` draws one component at a time into a summed vector, avoiding a samples-by-components allocation. Sample error is simulated stack minus target. Results report sample standard deviation (ddof = 1), empirical 2.5th/97.5th percentiles, and fraction strictly below/above the error limits (limits are inclusive). The 95% interval describes simulated assemblies, not confidence in the estimated mean. A seed reproduces results with the same input ordering and compatible NumPy implementation. Exact draws are not guaranteed across dependency changes.

Analytic sigma is sqrt(sum(sigma_i²)); signs do not change independent variances. Between 1 and 100 components and 100–250,000 samples are accepted by the library; the interface offers five sample sizes. Changing any model input invalidates displayed simulation results until rerun; theme/language changes preserve samples. Correlation, bias drift, non-linear optical sensitivity and process capability indices are outside v1.2.0.

For k failures among n independent simulated assemblies, p = k/n. The **two-sided 95% Wilson score interval** estimates the process-model failure probability:

```text
z = 1.959963984540054
center = (p + z²/(2n)) / (1 + z²/n)
half = z sqrt(p(1-p)/n + z²/(4n²)) / (1 + z²/n)
interval = [center - half, center + half], bounded to [0, 1]
```

Zero failures has lower limit zero and positive upper limit z²/(n+z²); e.g. 0/1,000 gives 0–0.38267585%. Percent precision adapts to sample count. This interval quantifies Monte Carlo sampling uncertainty conditional on the chosen independent process model, not real manufacturing qualification. It is different from the central 95% **assembly-error** interval (empirical quantiles). Even deterministic examples use the same conservative reporting convention rather than claiming zero risk from finite observations.

## References

- [Edmund Optics: Understanding focal length and field of view](https://www.edmundoptics.com/knowledge-center/application-notes/imaging/understanding-focal-length-and-field-of-view/) — optical terminology and field of view.
- [Edmund Optics: Imaging fundamentals](https://www.edmundoptics.com/knowledge-center/application-notes/imaging/6-fundamental-parameters-of-an-imaging-system/) — image-system parameter definitions.
- [NumPy random Generator](https://numpy.org/doc/stable/reference/random/generator.html) — generator interface used for simulations.
- [NIST: Confidence limits for a binomial proportion](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm) — Wilson score interval.

The algebraic models above are stated explicitly so their behavior can be checked without relying on undocumented camera-specific assumptions.
