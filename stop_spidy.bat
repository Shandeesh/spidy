@echo off
title Stop Spidy
cd /d "%~dp0"
color 0c

set FORCE_MODE=0
if "%1"=="/force" set FORCE_MODE=1

echo ===================================================
echo   STOPPING SPIDY AI ECOSYSTEM...
echo ===================================================

echo.
echo 1. Killing Python Logic (Backend and Brain)...
powershell -command "Get-WmiObject Win32_Process -Filter \"Name='python.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*spidy*' -or $_.CommandLine -like '*bridge_server*' -or $_.CommandLine -like '*brain_server*' -or $_.CommandLine -like '*shoonya_server*' -or $_.CommandLine -like '*agents.orchestrator*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo    - Python processes terminated.

echo.
echo 2. Killing Node.js API (Backend)...
powershell -command "Get-WmiObject Win32_Process -Filter \"Name='node.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*spidy*' -or $_.CommandLine -like '*server.js*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo    - Node.js processes terminated.

echo.
echo 3. Killing MT5 Terminal...
if "%FORCE_MODE%"=="1" goto DO_FORCE
goto DO_PROMPT

:DO_FORCE
taskkill /F /IM terminal64.exe /T 2>nul
powershell -command "Get-Process terminal64 -ErrorAction SilentlyContinue | Stop-Process -Force"
echo    - MT5 Terminal closed (Force Mode).
goto AFTER_MT5

:DO_PROMPT
choice /M "Do you want to close MT5 Terminal as well?" /C YN /T 5 /D N
if errorlevel 2 goto AFTER_MT5
taskkill /F /IM terminal64.exe /T 2>nul
echo    - MT5 Terminal closed.

:AFTER_MT5
echo.
echo 4. Cleaning up cmd windows...
taskkill /F /FI "WINDOWTITLE eq Spidy*" /T 2>nul
taskkill /F /FI "WINDOWTITLE eq Ollama*" /T 2>nul

echo.
echo ===================================================
echo   ALL SPIDY SERVICES STOPPED.
echo ===================================================

if "%FORCE_MODE%"=="1" goto END
timeout /t 3

:END
exit /b
