# Deployment

## Streamlit Community Cloud

1. Store this project in a GitHub repository, preserving the directory structure.
2. Sign in at [Streamlit Community Cloud](https://share.streamlit.io/) and connect the GitHub repository.
3. Create an app using branch `main` and entry point `app.py`.
4. Select a supported Python version (3.12 or newer recommended). Dependencies are installed from `requirements.txt`.
5. Deploy, then open all seven workspaces and run the Monte Carlo example. Keep the generated app URL in the repository description / README.

The [official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) describes the current account and repository connection flow. Connecting a previously unconnected account may require the owner to approve access. No secrets are required by this app.

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
