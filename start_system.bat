echo Starting Shoonya Bridge Server...
:: start "Spidy Shoonya Bridge" cmd /k "cd /d "c:\Users\Shandeesh R P\spidy\Trading_Backend\shoonya_bridge" && python shoonya_server.py"

:: Optional: Start MT5 Bridge (The Scout) on separate port if needed
start "Spidy MT5 Bridge" cmd /k "call run_mt5_bridge.bat"

:: 2. Start Backend API (Node.js)
start "Spidy Backend API" cmd /k "cd /d "c:\Users\Shandeesh R P\spidy\Trading_Backend\backend_api" && node server.js"

:: 3. Start Frontend Dashboard (Next.js)
start "Spidy Dashboard" cmd /k "cd /d "c:\Users\Shandeesh R P\spidy\Frontend_Dashboard\dashboard_app" && npm run dev"

:: 4. Start AI Brain Test (Optional / Idle)
:: Just keeping a window open for Member 1 Logs
start "Spidy AI Brain" cmd /k "cd /d "c:\Users\Shandeesh R P\spidy\AI_Engine\brain" && python brain_server.py"

echo All services launched! 
echo Access Dashboard at http://localhost:3000
