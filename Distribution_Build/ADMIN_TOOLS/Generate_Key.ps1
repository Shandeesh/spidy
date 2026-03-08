# Admin Key Generator
$ScriptDir = $PSScriptRoot
# Logic to call Python Licensing
$PythonExample = "python" # Assumes admin has python, or uses the one in ..\ if available?
# We assume Admin has environment.

Write-Host "=== SPIDY AI KEY GENERATOR ===" -ForegroundColor Cyan
$HWID = Read-Host "Enter Client's Hardware ID"

# Execute Python from parent directory
$LicensingScript = Join-Path $ScriptDir "..\License_Manager\licensing.py"

# We need to run the python script and capture output?
# Actually licensing.py has an interactive mode. Let's just run it.
& $PythonExample $LicensingScript

Pause
