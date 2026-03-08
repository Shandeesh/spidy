@echo off
title Stop Spidy
cd /d "%~dp0"
color 0c

:: check for /force arg
set FORCE_MODE=0
if "%1"=="/force" set FORCE_MODE=1

echo ===================================================
echo   STOPPING SPIDY AI ECOSYSTEM...
echo ===================================================

echo.
echo 1. Killing Python Logic (Backend & Brain)...
taskkill /F /IM python.exe /T 2>nul
:: PowerShell Backup Kill
powershell -command "Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force"
if %ERRORLEVEL% EQU 0 ( echo    - Python processes terminated. ) else ( echo    - Python processes already stopped. )

echo.
echo 2. Killing Node.js API (Backend)...
taskkill /F /IM node.exe /T 2>nul
powershell -command "Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force"
if %ERRORLEVEL% EQU 0 ( echo    - Node.js processes terminated. ) else ( echo    - Node.js processes already stopped. )

echo.
echo 3. Killing MT5 Terminal...
if "%FORCE_MODE%"=="1" (
    :: Force mode - auto kill MT5
    taskkill /F /IM terminal64.exe /T 2>nul
    powershell -command "Get-Process terminal64 -ErrorAction SilentlyContinue | Stop-Process -Force"
    echo    - MT5 Terminal closed (Force Mode).
) else (
    :: Prompt mode
    choice /M "Do you want to close MT5 Terminal as well?" /C YN /T 5 /D N
    if %ERRORLEVEL% EQU 1 (
        taskkill /F /IM terminal64.exe /T 2>nul
        echo    - MT5 Terminal closed.
    ) else (
        echo    - MT5 Terminal left open.
    )
)

echo.
echo 4. Cleaning up cmd windows...
taskkill /F /FI "WINDOWTITLE eq Spidy*" /T 2>nul
taskkill /F /FI "WINDOWTITLE eq Ollama*" /T 2>nul

echo.
echo ===================================================
echo   ALL SPIDY SERVICES STOPPED.
echo ===================================================

if "%FORCE_MODE%"=="0" (
    timeout /t 3
)
exit /b
