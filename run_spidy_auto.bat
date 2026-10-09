@echo off
echo ===================================================
echo   Running Spidy AI Ecosystem (Auto)
echo ===================================================

echo 1. Starting Backend API...
start "Spidy Backend" cmd /k "cd /d ""%~dp0Trading_Backend\backend_api"" && node server.js"

echo Waiting for Backend...
timeout /t 3 /nobreak >nul

echo 2. Starting Frontend Dashboard...
start "Spidy Dashboard" cmd /k "cd /d ""%~dp0Frontend_Dashboard\dashboard_app"" && npm.cmd run dev"

echo Waiting for Dashboard...
timeout /t 5 /nobreak >nul
echo Opening Dashboard in Browser...
start http://localhost:3000

echo 3. Starting MT5 Bridge...
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)
start "Spidy MT5 Bridge" cmd /k "call ""%~dp0run_mt5_bridge.bat"" ""%PYTHON_EXE%"""

echo 4. Starting AI Brain Server...
start "Spidy AI Brain" cmd /k "cd /d ""%~dp0AI_Engine\brain"" && ""%PYTHON_EXE%"" brain_server.py"

echo 5. Starting Multi-Agent Orchestrator...
start "Spidy Agents" cmd /k "cd /d ""%~dp0"" && ""%PYTHON_EXE%"" -m agents.orchestrator --config spidy_ai/config/settings.yaml"

echo ===================================================
echo   All Services Started!
echo ===================================================
