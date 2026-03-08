@echo off
echo ==========================================
echo [1/4] Installing AI Core Dependencies...
echo ==========================================
pip install -r "c:\Users\Shandeesh R P\spidy\AI_Engine\requirements.txt"
pip install -r "c:\Users\Shandeesh R P\spidy\Security_Module\requirements.txt"

echo ==========================================
echo [2/4] Installing MT5 Bridge Dependencies...
echo ==========================================
pip install -r "c:\Users\Shandeesh R P\spidy\Trading_Backend\mt5_bridge\requirements.txt"

echo ==========================================
echo [3/4] Installing Backend API Dependencies...
echo ==========================================
cd "c:\Users\Shandeesh R P\spidy\Trading_Backend\backend_api"
call npm install

echo ==========================================
echo [4/4] Installing Frontend Dashboard Dependencies...
echo ==========================================
cd "c:\Users\Shandeesh R P\spidy\Frontend_Dashboard\dashboard_app"
call npm install

echo ==========================================
echo ALL DEPENDENCIES INSTALLED SUCCESSFULLY!
echo ==========================================
pause
