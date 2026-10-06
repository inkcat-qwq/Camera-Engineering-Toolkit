# Validation record — v1.0.0

Validated locally on Windows with Python 3.14, Streamlit 1.65.0, NumPy 2.5.3, Matplotlib 3.11.2 and pandas 3.0.6 on 2026-10-06.

- **64 automated tests passed**, including every workspace, numerical reference cases, hyperfocal boundaries, reverse FOV, signed stacks, uniform/normal sampling, input errors, navigation state and exports.
- `pip check` reported no broken requirements.
- Source distribution and wheel built successfully. The source distribution includes the web entry point, theme configuration, examples and documentation; the wheel contains the reusable calculation library, data and CLI.
- Local HTTP health endpoint returned 200 / `ok`.
- Browser checks: default 48×36 / 80 mm FOV, native Light/Dark theme switching, 50,000-sample simulation, image-circle coverage, actual JSON download and parsed contents.
- Browser table edit: adapter 10.00 → 10.25 mm changed the actual stack to 70.25 mm, error to +0.25 mm and required correction to -0.25 mm. Values persisted after switching workspaces.
- Screenshots were captured from the running app in `docs/screenshots/`.

The first automated cold start exceeded the initial 30-second timeout while importing/rendering; the UI test timeout is now 60 seconds. Subsequent full suites passed. An initial Edge viewport override did not affect the target tab. A later public-app check in the in-app browser verified the layout at an observed 355 CSS-pixel width: navigation starts collapsed, inputs stack vertically, and text/controls remain readable. This is a browser viewport check, not a physical-device test.

Docker execution has not been tested in this local environment. [GitHub Actions run 37447080161](https://github.com/inkcat-qwq/Camera-Engineering-Toolkit/actions/runs/37447080161) passed both tests and package builds on Python 3.11, 3.12 and 3.14.

The public app was deployed on Streamlit Community Cloud with Python 3.14 at https://camera-engineering-toolkit.streamlit.app/. An independent in-app browser opened it without signing in and verified the FOV recalculation: changing a 48×36 mm setup from 80 mm to 50 mm changes horizontal FOV from 33.40° to 51.28°. A fresh HTTP session received status 200 from the public page without a login redirect and `200 / ok` from the application health endpoint. A 50,000-sample simulation returned mean +0.00009 mm, standard deviation 0.03559 mm and central 95% interval [-0.06673, +0.06697] mm. The sidebar now uses automatic initial state to collapse on narrow screens.
