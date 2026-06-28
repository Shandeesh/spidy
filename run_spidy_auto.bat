@echo off
echo ===================================================
echo   Running Spidy AI Ecosystem (Auto)
echo ===================================================

echo 0. Starting Local Brain (Ollama)...
start "Ollama" cmd /k "ollama serve"
timeout /t 5 /nobreak >nul

echo 1. Starting Backend API...
start "Spidy Backend" cmd /k "cd /d "%~dp0Trading_Backend\backend_api" && node server.js"

echo Waiting for Backend...
timeout /t 3 /nobreak >nul

echo 2. Starting Frontend Dashboard...
start "Spidy Dashboard" cmd /k "cd /d "%~dp0Frontend_Dashboard\dashboard_app" && npm run dev"

echo Waiting for Dashboard...
timeout /t 5 /nobreak >nul
echo Opening Dashboard in Browser...
start http://localhost:3000

echo 3. Starting MT5 Bridge...
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)
start "Spidy MT5 Bridge" cmd /k "cd /d "%~dp0Trading_Backend\mt5_bridge" && "%PYTHON_EXE%" bridge_server.py"

echo ===================================================
echo   All Services Started! 
echo ===================================================
