@echo off
setlocal enabledelayedexpansion

set ROOT_DIR=%~dp0..\..
set BACKEND_DIR=%ROOT_DIR%\backend
set FRONTEND_DIR=%ROOT_DIR%\frontend

where node >nul 2>nul
if errorlevel 1 (
    echo Node.js not found. Install it from https://nodejs.org
    pause
    exit /b 1
)

where uv >nul 2>nul
if errorlevel 1 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

cd /d "%FRONTEND_DIR%"
call npm ci
if errorlevel 1 (pause & exit /b 1)
call npm run build
if errorlevel 1 (pause & exit /b 1)

cd /d "%BACKEND_DIR%"
call uv sync
if errorlevel 1 (pause & exit /b 1)
call uv run python -m playwright install chromium

if not exist "%BACKEND_DIR%\.env" if exist "%BACKEND_DIR%\.env.example" (
    copy "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
)

if not defined ARESES_DATABASE_URL set ARESES_DATABASE_URL=sqlite+aiosqlite:///./data/areses.db
if not defined ARESES_LOCAL_MODE set ARESES_LOCAL_MODE=true
if not exist "%BACKEND_DIR%\data" mkdir "%BACKEND_DIR%\data"

call uv run alembic upgrade head
if errorlevel 1 (pause & exit /b 1)

echo.
echo ARESES is starting.
echo Open your browser to: http://localhost:8000
echo (The server binds to 0.0.0.0 so other devices on your network can also reach it
echo  at http://this-machine's-LAN-IP:8000 -- but push notifications and other
echo  browser security features only work over http://localhost or HTTPS.)
echo.

call uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

pause
