# Spidy AI Launcher Script
# Starts Backend, Frontend, and Browser UI

$ErrorActionPreference = "Stop"

$FrontendDir = "C:\Users\Shandeesh R P\spidy\Frontend_Dashboard\dashboard_app"
$TargetUrl = "http://localhost:3000/?v=2" # Cache Buster for Icon

Write-Host "============================" -ForegroundColor Cyan
Write-Host "   Starting Spidy AI...     " -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan

# --- HELPER: Validate Python Environment ---
function Test-PythonEnvironment ($PyPath) {
    if (-not (Test-Path $PyPath)) { return $false }
    try {
        # Check for critical imports: pandas (missing in user's venv), fastapi, MetaTrader5
        $Result = & $PyPath -c "import pandas, fastapi, MetaTrader5; print('OK')" 2>&1
        if ($LASTEXITCODE -eq 0 -and $Result -match "OK") { return $true }
    }
    catch { }
    return $false
}

# Determine Python Interpreter (Robust)
$VenvPython = "C:\Users\Shandeesh R P\spidy\.venv\Scripts\python.exe"
$GlobalPython = "python"
$PythonExe = $null

# 1. Try Virtual Environment first
Write-Host "Checking Virtual Environment..." -NoNewline
if (Test-PythonEnvironment $VenvPython) {
    $PythonExe = $VenvPython
    Write-Host " [OK]" -ForegroundColor Green
    Write-Host "Using Virtual Environment Python." -ForegroundColor Cyan
}
else {
    Write-Host " [BROKEN/MISSING]" -ForegroundColor Red
    Write-Host "   - Venv path exists? $((Test-Path $VenvPython))"
    Write-Host "   - Missing dependencies (e.g. pandas). falling back..."
    
    # 2. Fallback to Global Python
    Write-Host "Checking Global Python..." -NoNewline
    # Test 'python' command
    try {
        $GlobalPyPath = (Get-Command "python" -ErrorAction SilentlyContinue).Source
        if ($GlobalPyPath -and (Test-PythonEnvironment "python")) {
            $PythonExe = "python"
            Write-Host " [OK]" -ForegroundColor Green
            Write-Host "Using Global Python." -ForegroundColor Yellow
        }
        else {
            Write-Host " [FAILED]" -ForegroundColor Red
        }
    }
    catch { Write-Host " [FAILED]" -ForegroundColor Red }
}

if ($PythonExe) {
    # Debug: Confirm selection
    Write-Host "Selected Python: $PythonExe" -ForegroundColor DarkGray
}

# 3. Final Check
if (-not $PythonExe) {
    Write-Host "`nCRITICAL ERROR: No working Python environment found!" -ForegroundColor Red
    Write-Host "Please install Python 3.10+ and run: pip install -r requirements.txt"
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# Start MT5 Bridge (Direct Python Launch)
$BridgeScript = "C:\Users\Shandeesh R P\spidy\Trading_Backend\mt5_bridge\bridge_server.py"
$BridgeDir = "C:\Users\Shandeesh R P\spidy\Trading_Backend\mt5_bridge"
$VenvActivate = "C:\Users\Shandeesh R P\spidy\.venv\Scripts\activate.bat"

# FIX #13: Activate venv before launching to ensure all pip packages are on PATH
Write-Host "Launching Bridge Server via: $PythonExe" -ForegroundColor Cyan
if ($PythonExe -eq $VenvPython -and (Test-Path $VenvActivate)) {
    # Use venv activation to set PATH correctly
    $BridgeProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/k `"title Spidy MT5 Bridge && cd /d `"$BridgeDir`" && `"$VenvActivate`" && python `"$BridgeScript`"`"" -WorkingDirectory $BridgeDir -PassThru
} else {
    $BridgeProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/k `"title Spidy MT5 Bridge && cd /d `"$BridgeDir`" && `"$PythonExe`" `"$BridgeScript`"`"" -WorkingDirectory $BridgeDir -PassThru
}



Write-Host "MT5 Bridge started (PID: $($BridgeProcess.Id))." -ForegroundColor Green

# Start AI Brain Server (Python)
$BrainScript = "C:\Users\Shandeesh R P\spidy\AI_Engine\brain\brain_server.py"
$BrainProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/k `"title Spidy AI Brain && `"$PythonExe`" `"$BrainScript`"`"" -WorkingDirectory (Split-Path $BrainScript) -PassThru



Write-Host "AI Brain Server started (PID: $($BrainProcess.Id))." -ForegroundColor Green

# Start Node.js API Server
$NodePath = "C:\Users\Shandeesh R P\spidy\Trading_Backend\backend_api\server.js"
$NodeProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/k `"title Spidy Backend Node && node `"$NodePath`"`"" -WorkingDirectory (Split-Path $NodePath) -PassThru



Write-Host "Node.js Backend started (PID: $($NodeProcess.Id))." -ForegroundColor Green

# 2. Start Frontend Server
Write-Host "Starting Frontend Server (Next.js)..." -ForegroundColor Yellow

# Use cmd /c npm run dev to ensure environment variables are loaded correctly
$FrontendProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/k `"title Spidy Frontend && npm run dev`"" -WorkingDirectory $FrontendDir -PassThru


Write-Host "Frontend started (PID: $($FrontendProcess.Id))." -ForegroundColor Green

# 3. Wait for Port 3000 (Health Check)
Write-Host "Waiting for Dashboard to come online..." -ForegroundColor Yellow

$MaxRetries = 30
$RetryCount = 0
$PortOpen = $false

while ($RetryCount -lt $MaxRetries) {
    $Test = Test-NetConnection -ComputerName "localhost" -Port 3000 -InformationLevel Quiet
    if ($Test) {
        $PortOpen = $true
        break
    }
    Write-Host "." -NoNewline
    Start-Sleep -Seconds 1
    $RetryCount++
}
Write-Host "" # Newline

if (-not $PortOpen) {
    Write-Host "Error: Frontend failed to start on port 3000." -ForegroundColor Red
    Write-Host "Check if 'npm run dev' works manually."
    # Don't exit, maybe it's just slow? But usually it's fatal.
}
else {
    Write-Host "Dashboard is UP!" -ForegroundColor Green
}

# 4. Open Browser
Write-Host "Launching App Interface..." -ForegroundColor Yellow
$ChromePath = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
$EdgePath = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"

if (Test-Path $ChromePath) {
    Start-Process -FilePath $ChromePath -ArgumentList "--app=$TargetUrl"
}
elseif (Test-Path $EdgePath) {
    Start-Process -FilePath $EdgePath -ArgumentList "--app=$TargetUrl"
}
else {
    Write-Host "Warning: Browser not found. Open $TargetUrl manually." -ForegroundColor Red
    Start-Process $TargetUrl # Fallback to default browser
}

try {
    Write-Host "`nSpidy AI is running!" -ForegroundColor Cyan
    Write-Host "Keep this window OPEN." -ForegroundColor Cyan
    Write-Host "Press any key to stop servers and exit..." -ForegroundColor Yellow
    
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
finally {
    Write-Host "`nStopping servers..." -ForegroundColor Red
    Stop-Process -Id $BridgeProcess.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $BrainProcess.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $NodeProcess.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $FrontendProcess.Id -ErrorAction SilentlyContinue 
    # Also kill any node processes started by cmd
    Get-Process node -ErrorAction SilentlyContinue | Stop-Process -ErrorAction SilentlyContinue
    Write-Host "Servers stopped. Goodbye!" -ForegroundColor Cyan
}
