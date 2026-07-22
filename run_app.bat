@echo off
title D2D Dashboard
cd /d "%~dp0"
echo ===================================================
echo   Starting D2D Server...
echo   Dashboard URL: http://127.0.0.1:8000
echo ===================================================
timeout /t 2 >nul
start "" "http://127.0.0.1:8000"
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
pause
