@echo off
cd /d "%~dp0"
title EchoChamber Server

echo ========================================================
echo   Starting EchoChamber Server...
echo   - FastAPI:   http://localhost:8008
echo   - Streamlit: http://localhost:8501
echo ========================================================
echo.

start "" cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:8008 & start http://localhost:8501"

start "FastAPI-8008" .venv\Scripts\python.exe -m uvicorn app.main:app --port 8008 --host 0.0.0.0

.venv\Scripts\python.exe -m streamlit run dashboard.py --server.port 8501

pause
