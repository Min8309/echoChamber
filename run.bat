@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EchoChamber Server

echo ===================================================
echo   EchoChamber 서버 및 대시보드를 실행합니다...
echo ===================================================
echo.

:: 2초 후 브라우저 자동 오픈
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8000"

:: 가상환경 활성화 (존재할 경우)
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

:: FastAPI 서버 실행
uvicorn app.main:app --reload --port 8000

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [오류] 서버 실행 중 문제가 발생했습니다.
    pause
)
