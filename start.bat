@echo off
setlocal

echo ========================================
echo Text-to-SQL Evaluation Platform
echo ========================================
echo.

REM 优先使用本地虚拟环境Python，否则使用系统Python
set PYTHON_PATH=backend\venv\Scripts\python.exe
"%PYTHON_PATH%" --version >nul 2>&1
if errorlevel 1 (
    set PYTHON_PATH=python
    "%PYTHON_PATH%" --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found in local venv or system PATH.
        echo Please install Python or configure venv in backend\venv directory.
        exit /b 1
    )
)

echo [1/3] Starting Backend Server...
cd /d "%~dp0backend"
start "Backend Server" cmd /k "echo Installing dependencies... && \"%PYTHON_PATH%\" -m pip install -r requirements.txt && echo Starting Uvicorn... && \"%PYTHON_PATH%\" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 5 /nobreak >nul

echo [2/3] Starting Frontend (Vite)...
cd /d "%~dp0frontend"
start "Frontend" cmd /k "npm install && npm run dev -- --host --port 5173"

echo.
echo ========================================
echo Done! All services are starting up.
echo Backend URL:   http://localhost:8000
echo API Docs:      http://localhost:8000/docs
echo Frontend URL:  http://localhost:5173
echo ========================================
echo.
pause
