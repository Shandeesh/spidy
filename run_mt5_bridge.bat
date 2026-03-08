@echo off
cd /d "c:\Users\Shandeesh R P\spidy\Trading_Backend\mt5_bridge"
echo ===================================================
echo   SPIDY MT5 BRIDGE LAUNCHER
title Spidy MT5 Bridge
echo ===================================================

:: Check for Passed Python Path
if "%~1" neq "" (
    set "PYTHON_EXE=%~1"
) else (
    set "PYTHON_EXE=python"
)

echo Using Python: "%PYTHON_EXE%"
"$PYTHON_EXE%" --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found or invalid path!
    echo Path: "%PYTHON_EXE%"
    pause
    exit /b
)

:: Validate Imports
"$PYTHON_EXE%" -c "import pandas, fastapi, MetaTrader5; print('Environment OK')" >nul 2>&1  
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python environment is broken or missing dependencies!
    pause
    exit /b
)

echo Starting Bridge Server...
"$PYTHON_EXE%" bridge_server.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Server Crashed! Code: %ERRORLEVEL%
    pause
)
