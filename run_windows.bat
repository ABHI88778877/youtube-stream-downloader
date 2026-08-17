@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py"
) else (
    set "PY=python"
)

echo.
echo ==========================================
echo YouTube Stream Downloader
echo ==========================================
echo.

%PY% -m venv .venv
if errorlevel 1 (
    echo Failed to create virtual environment.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Starting server...
echo Open http://127.0.0.1:5000
echo Press Ctrl+C to stop.
echo.

python app.py
pause
