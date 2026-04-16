@echo off
echo ===================================================
echo   Running Spidy AI Ecosystem
echo ===================================================

echo 1. Starting Backend API (Node.js Relay)...
start "Spidy Backend" cmd /k "cd /d "%~dp0Trading_Backend\backend_api" && node server.js"

echo Waiting for Backend to bind...
timeout /t 3 /nobreak >nul

echo 2. Starting Frontend Dashboard...
start "Spidy Dashboard" cmd /k "cd /d "%~dp0Frontend_Dashboard\dashboard_app" && npm run dev"

echo 3. Starting MT5 Bridge...
start "Spidy MT5 Bridge" cmd /k "call run_mt5_bridge.bat"

echo 4. Starting AI Brain Server (Process Isolation)...
start "Spidy AI Brain" cmd /k "cd /d "%~dp0AI_Engine\brain" && python brain_server.py"

echo Waiting for Bridge and Brain to initialise...
timeout /t 5 /nobreak >nul

echo 5. Starting Multi-Agent Orchestrator...
start "Spidy Agents" cmd /k "cd /d "%~dp0" && ".venv\Scripts\python.exe" -m agents.orchestrator --config spidy_ai/config/settings.yaml"

echo ===================================================
echo   All Services Started!
echo   - Backend   : http://localhost:5000
echo   - Dashboard : http://localhost:3000 (Next.js)
echo   - MT5 Bridge: http://localhost:8000
echo   - AI Brain  : http://localhost:5001
echo   - Agents    : running (see "Spidy Agents" window)
echo ===================================================
pause
