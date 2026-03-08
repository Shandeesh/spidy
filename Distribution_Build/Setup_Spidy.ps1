# Spidy AI - One Click Installer & Activator

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$LicenseFile = Join-Path $ScriptDir "license.key"
$LicenseManager = Join-Path $ScriptDir "License_Manager\licensing.py"
$ReqFile = Join-Path $ScriptDir "requirements.txt"
$DistServer = Join-Path $ScriptDir "dist_server.py"
$PythonExe = "python" # Default

Write-Host "============================" -ForegroundColor Cyan
Write-Host "   Spidy AI Installation    " -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan

# 1. Check Python
try {
    $ver = & $PythonExe --version 2>&1
    Write-Host "Found Python: $ver" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ and try again."
    Pause
    Exit
}

# 2. Activation Step
if (-not (Test-Path $LicenseFile)) {
    Write-Host "`n[ ACTIVATION REQUIRED ]" -ForegroundColor Yellow
    
    # Get HWID via Python script
    $HWID = & $PythonExe -c "from License_Manager.licensing import get_hardware_id; print(get_hardware_id())"
    
    Write-Host "Your Hardware ID: " -NoNewline
    Write-Host "$HWID" -ForegroundColor White -BackgroundColor Blue
    Write-Host "`nPlease send this ID to the Admin to receive your Activation Key."
    
    $UserKey = Read-Host "Enter Activation Key"
    
    # Validate
    $IsValid = & $PythonExe -c "from License_Manager.licensing import validate_key; print(validate_key('$HWID', '$UserKey'))"
    
    if ($IsValid -match "True") {
        Write-Host "Activation Successful!" -ForegroundColor Green
        $UserKey | Out-File -FilePath $LicenseFile -Encoding ascii
    }
    else {
        Write-Host "Invalid Activation Key! Setup Aborted." -ForegroundColor Red
        Pause
        Exit
    }
}
else {
    Write-Host "License Key found. Proceeding..." -ForegroundColor Green
}

# 3. Virtual Env Setup
$VenvDir = Join-Path $ScriptDir ".venv"
if (-not (Test-Path $VenvDir)) {
    Write-Host "`nCreating Virtual Environment..." -ForegroundColor Yellow
    & $PythonExe -m venv $VenvDir
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

# 4. Install Dependencies
Write-Host "Installing Dependencies..." -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r $ReqFile

# 5. Create Desktop Shortcut
Write-Host "Creating Desktop Shortcut..." -ForegroundColor Yellow
$WshShell = New-Object -comObject WScript.Shell
$Desktop = [System.Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $Desktop "Spidy AI.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $VenvPython
$Shortcut.Arguments = "`"$DistServer`""
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.Description = "Launch Spidy AI"
$Shortcut.Save()

Write-Host "`nInstallation Complete!" -ForegroundColor Green
Write-Host "You can now start Spidy AI from your Desktop."
Pause
