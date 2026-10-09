# Spidy Multi-Agent Integration Script (Windows PowerShell)
#
# Usage:
#    1. Download all agent files to a folder (e.g., C:\temp\agents_download)
#    2. Copy this script to your Spidy project root
#    3. Open PowerShell as Admin
#    4. cd C:\path\to\spidy-main
#    5. Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
#    6. .\setup_agents.ps1
#

param(
    [string]$SourceDir = "",
    [string]$ProjectRoot = "",
    [switch]$SkipDeps = $false,
    [switch]$OverwriteExisting = $false
)

$ErrorActionPreference = "Stop"
$WarningPreference = "Continue"

# Colors
$OK = "Green"
$WARN = "Yellow"
$ERR = "Red"
$INFO = "Cyan"

function Write-Status($msg, $color = "Green") { Write-Host $msg -ForegroundColor $color }

if ([string]::IsNullOrWhiteSpace($SourceDir)) {
    $SourceDir = $PSScriptRoot
}
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    if (Test-Path (Join-Path $PSScriptRoot "spidy_ai")) {
        $ProjectRoot = $PSScriptRoot
    } else {
        $ProjectRoot = Split-Path -Parent $PSScriptRoot
    }
}

Write-Status "=== Spidy Multi-Agent Integration Setup ===" "Magenta"
Write-Status ""

# Step 1: Verify source directory
Write-Status "[Step 1/5] Verifying source directory..." $INFO
if (-not (Test-Path $SourceDir)) {
    Write-Status "ERROR: Source directory not found: $SourceDir" $ERR
    Write-Status "   Please download agent files to: $SourceDir" $WARN
    exit 1
}

$requiredFiles = @(
    "orchestrator.py", "message_bus.py", "base_agent.py",
    "data_engineer.py", "researcher.py", "risk_manager.py", "executor.py",
    "__init__.py", "settings.yaml"
)

$missingFiles = @()
foreach ($file in $requiredFiles) {
    if (-not (Test-Path "$SourceDir\$file")) {
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Status "Missing files: $($missingFiles -join ', ')" $ERR
    exit 1
}
Write-Status "All agent files found" $OK

# Step 2: Create directory structure
Write-Status "[Step 2/5] Creating directory structure..." $INFO
$agentsDir = Join-Path $ProjectRoot "agents"
$configDir = Join-Path $ProjectRoot "spidy_ai\config"
$logsDir = Join-Path $ProjectRoot "logs"

foreach ($dir in @($agentsDir, $configDir, $logsDir)) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Status "   Created: $dir" $OK
    }
}

# Step 3: Copy agent files
Write-Status "[Step 3/5] Copying agent files..." $INFO
Write-Status "   Source: $SourceDir" $INFO
Write-Status "   Target: $agentsDir" $INFO
foreach ($file in $requiredFiles) {
    $src = Join-Path $SourceDir $file
    if ($file -eq "settings.yaml") {
        $dst = Join-Path $configDir $file
    } else {
        $dst = Join-Path $agentsDir $file
    }
    
    if ((Test-Path $dst) -and -not $OverwriteExisting) {
        Write-Status "   Keeping existing $file (use -OverwriteExisting to replace)" $WARN
    } else {
        Copy-Item -Path $src -Destination $dst -Force
        Write-Status "   Copied: $file" $OK
    }
}

# Step 4: Install Python dependencies
Write-Status "[Step 4/5] Installing Python dependencies..." $INFO

$hasPython = $false
try {
    $pyVer = python --version 2>&1
    $hasPython = $LASTEXITCODE -eq 0
} catch {
    $hasPython = $false
}

if (-not $hasPython) {
    Write-Status "Python not found. Install Python 3.9+ and add to PATH." $ERR
    exit 1
}
Write-Status "   Python $pyVer" $OK

if (-not $SkipDeps) {
    Write-Status "   Installing: pyyaml, google-generativeai, MetaTrader5..." $WARN
    python -m pip install -q pyyaml google-generativeai MetaTrader5 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Status "   Dependencies installed" $OK
    } else {
        Write-Status "   Some packages may have failed to install" $WARN
    }
}

# Step 5: Create launcher scripts
Write-Status "[Step 5/5] Creating launcher scripts..." $INFO

# PowerShell launcher
$ps1Content = @(
    '# Spidy Multi-Agent System Launcher (PowerShell)'
    'python spidy_ai/run_agents.py --mode sim'
)
$ps1Content | Set-Content -Path "$ProjectRoot\run_spidy_agents.ps1" -Encoding UTF8
Write-Status "   Created run_spidy_agents.ps1" $OK

# Batch launcher
$batContent = @(
    '@echo off'
    'REM Spidy Multi-Agent Trading System Launcher'
    'python spidy_ai/run_agents.py --mode sim'
    'pause'
)
$batContent | Set-Content -Path "$ProjectRoot\run_spidy_agents.bat" -Encoding ASCII
Write-Status "   Created run_spidy_agents.bat" $OK

# Test import
Write-Status ""
Write-Status "Testing agent imports..." $INFO
$testCode = 'import sys; sys.path.insert(0, str(__import__("pathlib").Path.cwd())); from agents import Orchestrator; print("Agents module imported successfully")'

$testResult = python -c $testCode 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Status "   $testResult" $OK
} else {
    Write-Status "   Import test failed (may need env setup)" $WARN
}

# Summary
Write-Status ""
Write-Status "=== Setup Complete ===" "Green"
Write-Status ""

Write-Status "Structure:"
Write-Status "   agents/                      (5 agents + base + bus)"
Write-Status "   spidy_ai/config/settings.yaml (master config)"
Write-Status "   logs/                         (auto-created on first run)"
Write-Status ""

Write-Status "Next steps:"
Write-Status "   1. Open spidy_ai/config/settings.yaml and customize if needed"
Write-Status "   2. Set environment: GOOGLE_API_KEY (for Gemini access)"
Write-Status "   3. Run in simulation:"
Write-Status "      python spidy_ai/run_agents.py --mode sim"
Write-Status "   4. Or double-click: run_spidy_agents.bat (Windows)"
Write-Status ""

Write-Status "Full integration guide: INTEGRATION_GUIDE.md"
Write-Status ""
