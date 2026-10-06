# v1.1.1 — 2026-10-06

Moved Camera Design's back width and height into a collapsed record section below the results, labelled as not used in calculations in both languages. The main input explanation now identifies the optical-axis dimension chain. Existing field values and exported records are preserved.

# v1.1.0 — 2026-10-06

Added English / Simplified Chinese selection at the top of the sidebar. All seven workspaces translate navigation, parameters, metrics, preset descriptions, comparison-table headers, distribution options, model notes, validation messages and engineering chart labels. Switching languages keeps custom dimensions, canonical selections, component records and existing Monte Carlo results.

Bundled Noto Sans SC under SIL OFL 1.1 for portable Chinese chart rendering, including user-entered component names. Font selection is local to each figure. The calculation library and export schema retain their existing conventions and English identifiers. User data is never translated. Streamlit and Community Cloud controls retain their own language.

# v1.0.0 — 2026-10-06

Initial implementation of the agreed Camera Engineering Toolkit scope: seven engineering workspaces, fourteen customizable format presets, independent Python calculation library, Matplotlib charts, CSV/JSON records, reproducible Monte Carlo, optional CLI, project documentation, MIT license, CI and deployment files.

The interface language is English. Streamlit's built-in Light, Dark and system theme choices are retained. Numerical limits, model assumptions and unsupported physics are described in `MODELS.md`.

Excluded from this release: optical ray tracing, full lens design, Scheimpflug/tilt/swing simulation, verified camera/lens catalogs, persistent accounts, correlated tolerance distributions and fabrication-ready CAD.
