# Validation record — v1.2.0

Validated on Windows, 2026-10-06, with Python 3.14, Streamlit 1.65.0, NumPy 2.5.3, Matplotlib 3.11.2 and pandas 3.0.6. Exact runtime versions are in `requirements-tested.txt`.

## Automated checks

Before modifications, the clean v1.1.1 baseline (`f1241a34b6ce75b45d87c2d16f7e99059e97f21c`) passed **77 tests, 0 failed, 0 skipped**. The full v1.2.0 suite passed **151 tests, 0 failed, 0 skipped** in 175.68 seconds. No test was removed. Existing assertions were updated only for adaptive display precision and the explicitly unified internal chain state.

New tests cover ordinary/close-focus datum conversion, explicit principal-plane inputs including magnification above 1, geometric blur at translated limits, exact/below/above hyperfocal, impossible geometry, adaptive display, infinity and signed zero, preset metadata and rotated rectangles, duplicate IDs, Wilson reference cases, zero/all failures, Uniform/Normal semantics, shared chain and target, stale-result invalidation, bilingual export fields, and all seven workspaces' theme redraws in both languages. Widget-policy tests inspect default/state conflicts rather than suppressing warnings. Chart tests check palette colors and absence of global Matplotlib state changes.

`pip check` reported no broken requirements. Source and wheel builds succeeded. The package contains the preset catalog, pure modules, bundled regular Noto Sans SC font and its OFL license. The source package contains the app, configuration and documentation. Docker execution was not tested locally.

## Browser checks

From the repository directory, the exact validation launch was equivalent to:

```powershell
& ..\..\work\.venv\Scripts\python.exe -m streamlit run app.py --server.address=127.0.0.1 --server.port=8502 --server.headless=true
```

The process was launched hidden with the resolved absolute Python path and repository working directory, so `.streamlit/config.toml` was loaded. Normal end-user launch remains `python -m streamlit run app.py` from the source repository.

All seven workspaces were inspected in Edge in English / Chinese and Light / Dark (**28 combinations**):

| Workspace | English Light | English Dark | Chinese Light | Chinese Dark |
|---|---|---|---|---|
| Format / Sensor | Checked | Checked | Checked | Checked |
| Field of View | Checked | Checked | Checked | Checked |
| Lens Equivalence | Checked | Checked | Checked | Checked |
| Depth of Field | Checked | Checked | Checked | Checked |
| Large Format | Checked | Checked | Checked | Checked |
| Camera Design | Checked | Checked | Checked | Checked |
| Tolerance / Monte Carlo | Checked | Checked | Checked | Checked |

Specific scenarios:

- A 100 mm, f/8, c=0.03 mm setup at D=450 mm converts to s=300 mm / v=150 mm. Image-plane limits were 448.56687898 and 451.44694534 mm; the UI displayed front/rear depths **1.433 / 1.447 mm**, retaining asymmetry. A 1,000 m subject setting displayed infinity for far/total/rear DoF. The selected datum and model explanation were visible in both languages.
- 5×7 displayed nominal sheet **177.8×127 mm** separately from the editable representative **170×120 mm** image area. At the existing 15 mm rise and 210 mm circle the calculated required circle was 226.7 mm and the uncovered-area warning appeared.
- A real canvas-table edit changed the adapter from 10 to **10.02 mm** in Camera Design. Actual position became 70.02 mm, error +0.02 mm, correction −0.02 mm. Monte Carlo retained the same row. Setting its target to 70.02 mm was reflected back in Camera Design.
- Uniform remained the initial distribution. The centered three-component chain, seed 42, n=1,000 returned **0 / 1,000** failures and **0.0%–0.4%** displayed Wilson interval (unrounded upper bound 0.38267585%). The zero-risk caveat was visible.
- The adapter distribution was changed through the real editor to **Normal (±3σ)**. A new 1,000-sample run completed. Navigation and Chinese translation preserved its distribution and dimensions. Camera Design labeled the stated envelope **not a guaranteed bound** and showed analytic sigma 0.03266 mm.
- Light→Dark and Dark→Light were observed on FOV, DoF, coverage, design stack and the completed Monte Carlo histogram without changing another calculation input. Native fields, canvas editor, figure backgrounds, axes and labels followed the selected theme.
- Actual browser downloads were parsed: DoF JSON has schema 2, toolkit 1.2.0, input D=450 mm, principal distance approximately 300 mm and the declared datum; Monte Carlo result CSV includes Wilson fields; sample CSV contains exactly 1,000 records with `stack_mm = plane_error_mm + 70.02`.
- The final local server log contained only the startup message: no Streamlit, NumPy, pandas or Matplotlib warnings and no tracebacks. Browser warning/error logs were empty. The earlier first regression run's three failures were fixed before the passing full suite.
- README screenshots were recaptured from the current UI. They show version 1.2.0, consistent themes and no Deploy button. README launch commands and sidebar theme instructions were reviewed against the code and launch process.

Browser automation occasionally captured a partially redrawn frame or timed out on full-page screenshots; steady-state views were inspected with normal viewport captures. There were no corresponding app exceptions. Screenshots are viewport excerpts, not physical-device tests.

## Scope of evidence

AppTest verifies Python state and figure configuration; browser checks exercise the native-theme message bridge. A future Streamlit upgrade or different hosting origin requires another browser check. The existing CI matrix covers Python 3.11, 3.12 and 3.14; this document's local result is specifically Python 3.14. Public deployment status and final commit are reported in the release handoff.
