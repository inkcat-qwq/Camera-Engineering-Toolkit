# Validation record — v1.0.0

Validated locally on Windows with Python 3.14, Streamlit 1.65.0, NumPy 2.5.3, Matplotlib 3.11.2 and pandas 3.0.6 on 2026-10-06.

- **64 automated tests passed**, including every workspace, numerical reference cases, hyperfocal boundaries, reverse FOV, signed stacks, uniform/normal sampling, input errors, navigation state and exports.
- `pip check` reported no broken requirements.
- Source distribution and wheel built successfully. The source distribution includes the web entry point, theme configuration, examples and documentation; the wheel contains the reusable calculation library, data and CLI.
- Local HTTP health endpoint returned 200 / `ok`.
- Browser checks: default 48×36 / 80 mm FOV, native Light/Dark theme switching, 50,000-sample simulation, image-circle coverage, actual JSON download and parsed contents.
- Browser table edit: adapter 10.00 → 10.25 mm changed the actual stack to 70.25 mm, error to +0.25 mm and required correction to -0.25 mm. Values persisted after switching workspaces.
- Screenshots were captured from the running app in `docs/screenshots/`.

The first automated cold start exceeded the initial 30-second timeout while importing/rendering; the UI test timeout is now 60 seconds. Subsequent full suites passed. The browser's viewport override did not change its observed width, so mobile-device visual validation is not claimed. The layout uses Streamlit's responsive columns and a narrow-screen spacing rule.

Docker execution has not been tested in this local environment. GitHub Actions is configured for Python 3.11, 3.12 and 3.14; its remote status should be checked in the repository. Public hosting requires the owner's Streamlit login and, if prompted, GitHub authorization. No public demo URL is claimed until deployment succeeds.
