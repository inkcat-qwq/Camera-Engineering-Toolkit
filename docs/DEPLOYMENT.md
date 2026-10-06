# Deployment — v1.2.0

Public deployment: **https://camera-engineering-toolkit.streamlit.app/**. Source: `inkcat-qwq/Camera-Engineering-Toolkit`, branch `main`, entry point `app.py`, Python 3.14. The initial deployment was verified on 2026-10-06. Visitors do not need to install Python.

## Streamlit Community Cloud

1. Store this project in a GitHub repository, preserving the directory structure.
2. Sign in at [Streamlit Community Cloud](https://share.streamlit.io/) and connect the GitHub repository.
3. Create an app using branch `main` and entry point `app.py`.
4. Select a supported Python version (3.12 or newer recommended). Dependencies are installed from `requirements.txt`.
5. Deploy, then open all seven workspaces and run the Monte Carlo example. Keep the generated app URL in the repository description / README.

The [official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) describes the current account and repository connection flow. Connecting a previously unconnected account may require the owner to approve access. No secrets are required by this app.

## Application theme

The app's sidebar Light/Dark state owns its native widget palette, CSS and Matplotlib colors. Streamlit 1.65.0 is pinned: its native theme bridge receives `SET_CUSTOM_THEME_CONFIG` via a trusted same-origin `window.postMessage`, with no process-wide theme mutation. Only static application colors are passed. Top-right toolbar actions and the framework menu are hidden so they cannot create a second conflicting theme state or expose a Deploy button. The toolbar container stays visible because it also holds the narrow-screen sidebar opener.

`client.allowedOrigins` explicitly includes loopback HTTP and this app's Community Cloud origins. When deploying on another domain, add only the exact trusted app / embed origin to that setting and validate both theme directions, including the canvas editor. Do not replace the list with an unrestricted wildcard. A future Streamlit upgrade must revalidate the native-theme protocol, widget defaults, state retention and browser rendering; AppTest alone cannot verify browser postMessage handling.

## Docker

```sh
docker build -t camera-engineering-toolkit .
docker run --rm -p 8501:8501 camera-engineering-toolkit
```

Open http://localhost:8501. The Docker image runs as a non-root user. For a public service, use a platform that supports long-lived Python processes and WebSocket connections, put HTTPS in front of it, and choose suitable memory/concurrency limits. The application keeps calculations in session memory and caps sample counts per run.

## Source and release checks

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m build
```

The package contains the reusable `cet` library, presets and CLI; run the web app from the source checkout. `requirements-tested.txt` records the exact runtime versions used for the delivered local validation. Normal installation uses compatible version ranges to allow supported Python platforms.

## Windows launcher

`launch.bat` uses the Windows Python launcher, creates `.venv` within this project and installs packages on first use. It opens a normal interactive terminal because the user launched it and needs to close the app there. Stop with Ctrl+C. It never edits global Python packages. If a newer release changes dependencies, run `.venv\Scripts\python -m pip install -r requirements.txt` again.
