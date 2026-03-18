@echo off
echo ========================================
echo   ORCHESTRA - Local Development Servers
echo ========================================
echo.
echo Starting Main Server (port 8000) ...
start "ORCHESTRA Main (8000)" cmd /k "cd /d %~dp0 && .venv\Scripts\activate && uvicorn app:app --host 0.0.0.0 --port 8000 --reload"

echo Starting Document Agent (port 8002) ...
start "ORCHESTRA DocAgent (8002)" cmd /k "cd /d %~dp0 && .venv\Scripts\activate && uvicorn doc_app:app --host 0.0.0.0 --port 8002 --reload"

echo.
echo Both servers launched in separate windows.
echo   Main server:     http://localhost:8000
echo   Document agent:  http://localhost:8002
echo.
pause
