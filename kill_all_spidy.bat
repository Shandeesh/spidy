@echo off
echo Killing Spidy Processes...
:: Targeted PowerShell Kill for Python
powershell -command "Get-WmiObject Win32_Process -Filter \"Name='python.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*spidy*' -or $_.CommandLine -like '*bridge_server*' -or $_.CommandLine -like '*brain_server*' -or $_.CommandLine -like '*shoonya_server*' -or $_.CommandLine -like '*agents.orchestrator*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

:: Targeted PowerShell Kill for Node
powershell -command "Get-WmiObject Win32_Process -Filter \"Name='node.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*spidy*' -or $_.CommandLine -like '*server.js*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

:: Close MT5 terminal
taskkill /F /IM terminal64.exe /T 2>nul

echo All Spidy processes terminated.
timeout /t 2 >nul
exit /b
