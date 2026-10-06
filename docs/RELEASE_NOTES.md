# v1.2.0 — Engineering Reliability Update — 2026-10-06

- DoF defaults to a clearly labeled image/sensor/film-plane measurement, with conversion to the unchanged thin-lens equations. The explicit principal-plane option is retained; near/far limits follow the selected datum. The image-plane branch is limited to magnification ≤1.
- Centralized adaptive mm/m and angle formatting preserves close-focus differences and small values, with explicit infinity and normalized signed zero.
- Preset schema 2 distinguishes nominal sheets from active image area and includes stable IDs, categories and provenance. All 14 legacy names remain usable through `presets()`; custom sizes remain editable. The 5×7 active area changes from 178×127 mm to an explicitly illustrative 170×120 mm; nominal sheet size is 177.8×127 mm. Recheck stored designs that depended on the old preset geometry.
- Monte Carlo reports observed failures / sample count and a two-sided 95% Wilson interval. Zero failures has a positive upper bound. This is conditional sampling uncertainty, not a manufacturing capability claim. Uniform remains the default; Normal explicitly means ±3σ with unbounded tails.
- Camera Design and Monte Carlo now share component records and target. Camera Design visibly reports nominal/target, error/correction, tolerance envelope or bounded worst case, and analytic sigma. Changing the shared model marks previous simulation results stale.
- One sidebar Light/Dark state updates native widgets, CSS and figures. Language and theme changes preserve inputs and simulation samples. Session-state default duplication warnings are fixed without suppressing warnings.

## Compatibility

The core `depth_of_field` principal-plane contract is unchanged. `dof_with_datum` is an additional measurement wrapper. Existing `Format`, `Component`, CLI and geometry entry points remain available. Invalid boolean numeric values/signs, empty/non-text component names and nonfinite inputs now fail explicitly.

Export schema advances from 1 to **2**. English keys/canonical choices and full numeric precision remain stable. Format records add active/nominal metadata. DoF inputs retain principal-plane `distance_mm` and add `entered_distance_mm` / `distance_datum`; DoF result near/far/hyperfocal values follow that declared datum. Consumers must check schema and datum. Existing schema-1 files are not rewritten, and the app does not import saved records.

Session migration selects the currently active design/Monte Carlo chain if legacy state exists, then uses one shared model. Separate conflicting legacy chains cannot both be retained as the active chain. User component names are preserved. Inputs remain session-local; download before closing the app.

The Streamlit dependency stays pinned at 1.65.0 because native theme synchronization uses its host-message protocol. New hosting domains need their own explicit allowed origin; see `DEPLOYMENT.md`.

## Historical releases

### v1.1.1 — 2026-10-06

Moved Camera Design's back width and height into a collapsed record section below the results, labelled as not used in calculations in both languages. The main input explanation now identifies the optical-axis dimension chain. Existing field values and exported records are preserved.

### v1.1.0 — 2026-10-06

Added English / Simplified Chinese selection at the top of the sidebar. All seven workspaces translate navigation, parameters, metrics, preset descriptions, comparison-table headers, distribution options, model notes, validation messages and engineering chart labels. Switching languages keeps custom dimensions, canonical selections, component records and existing Monte Carlo results.

Bundled Noto Sans SC under SIL OFL 1.1 for portable Chinese chart rendering, including user-entered component names. Font selection is local to each figure. The calculation library and export schema retain their existing conventions and English identifiers. User data is never translated. Streamlit and Community Cloud controls retain their own language.

### v1.0.0 — 2026-10-06

Initial implementation of the agreed Camera Engineering Toolkit scope: seven engineering workspaces, fourteen customizable format presets, independent Python calculation library, Matplotlib charts, CSV/JSON records, reproducible Monte Carlo, optional CLI, project documentation, MIT license, CI and deployment files.

The interface language is English. Streamlit's built-in Light, Dark and system theme choices are retained. Numerical limits, model assumptions and unsupported physics are described in `MODELS.md`.

Excluded from this release: optical ray tracing, full lens design, Scheimpflug/tilt/swing simulation, verified camera/lens catalogs, persistent accounts, correlated tolerance distributions and fabrication-ready CAD.
