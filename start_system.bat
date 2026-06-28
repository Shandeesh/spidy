@echo off
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    echo [WARN] Virtual environment Python not found. Falling back to system python...
    set "PYTHON_EXE=python"
)

echo Starting Shoonya Bridge Server...
:: start "Spidy Shoonya Bridge" cmd /k "cd /d "%~dp0Trading_Backend\shoonya_bridge" && "%PYTHON_EXE%" shoonya_server.py"

:: Optional: Start MT5 Bridge (The Scout) on separate port if needed
start "Spidy MT5 Bridge" cmd /k "call "%~dp0run_mt5_bridge.bat" "%PYTHON_EXE%""

:: 2. Start Backend API (Node.js)
start "Spidy Backend API" cmd /k "cd /d "%~dp0Trading_Backend\backend_api" && node server.js"

:: 3. Start Frontend Dashboard (Next.js)
start "Spidy Dashboard" cmd /k "cd /d "%~dp0Frontend_Dashboard\dashboard_app" && npm run dev"

:: 4. Start AI Brain Server
start "Spidy AI Brain" cmd /k "cd /d "%~dp0AI_Engine\brain" && "%PYTHON_EXE%" brain_server.py"

echo All services launched! 
echo Access Dashboard at http://localhost:3000

