$VenvPython = "C:\Users\Shandeesh R P\spidy\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual Environment python not found at $VenvPython"
    exit 1
}

Write-Host "Installing AI Engine requirements..."
& $VenvPython -m pip install -r "AI_Engine\requirements.txt"

Write-Host "Installing Security Module requirements..."
& $VenvPython -m pip install -r "Security_Module\requirements.txt"

Write-Host "Installing MT5 Bridge requirements..."
& $VenvPython -m pip install -r "Trading_Backend\mt5_bridge\requirements.txt"

Write-Host "Repaired Successfully."
