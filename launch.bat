@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto run
py -3 -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
:run
.venv\Scripts\python.exe -m streamlit run app.py --server.headless=false
if errorlevel 1 goto failed
exit /b 0
:failed
echo Please install Python 3.11 or newer and retry. See README.md for manual setup.
pause
exit /b 1
