@echo off
set "PIP_EXE=%~dp0.venv\Scripts\pip.exe"
if not exist "%PIP_EXE%" (
    echo [WARN] Virtual environment pip not found at %PIP_EXE%.
    echo Falling back to global system pip...
    set "PIP_EXE=pip"
)

echo ==========================================
echo [1/6] Installing AI Core Dependencies...
echo ==========================================
"%PIP_EXE%" install -r "%~dp0AI_Engine\requirements.txt"
"%PIP_EXE%" install -r "%~dp0Security_Module\requirements.txt"

echo ==========================================
echo [2/6] Installing MT5 Bridge Dependencies...
echo ==========================================
"%PIP_EXE%" install -r "%~dp0Trading_Backend\mt5_bridge\requirements.txt"

echo ==========================================
echo [3/6] Installing Shoonya Bridge Dependencies...
echo ==========================================
"%PIP_EXE%" install -r "%~dp0Trading_Backend\shoonya_bridge\requirements.txt"

echo ==========================================
echo [4/6] Installing Automation Engine Dependencies...
echo ==========================================
"%PIP_EXE%" install -r "%~dp0Trading_Backend\automation_engine\requirements.txt"

echo ==========================================
echo [5/6] Installing Backend API Dependencies...
echo ==========================================
cd /d "%~dp0Trading_Backend\backend_api"
call npm install

echo ==========================================
echo [6/6] Installing Frontend Dashboard Dependencies...
echo ==========================================
cd /d "%~dp0Frontend_Dashboard\dashboard_app"
call npm install

echo ==========================================
echo ALL DEPENDENCIES INSTALLED SUCCESSFULLY!
echo ==========================================
pause
