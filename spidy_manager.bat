@echo off
title Spidy System Manager
cd /d "%~dp0"
color 0b
cls

:MENU
cls
echo ===========================================================
echo    SPIDY AI TRADING SYSTEM MANAGER
echo ===========================================================
echo.
echo    [1] FULL RESTART
echo        - Closes ALL Spidy processes (MT5, Python, Node)
echo        - Re-launches Spidy fresh
echo.
echo    [2] FULL STOP
echo        - Closes ALL Spidy processes
echo        - Shuts down completely
echo.
echo    [3] Cancel / Exit
echo.
echo ===========================================================
set /p "opt=Select an option (1-3): "

if "%opt%"=="1" goto RESTART
if "%opt%"=="2" goto STOP
if "%opt%"=="3" goto END

:: Invalid input
echo Invalid option selected.
timeout /t 2 >nul
goto MENU

:RESTART
cls
echo [FULL RESTART INITIATED]
echo Stopping all services...
call stop_spidy.bat /force
timeout /t 2 >nul
echo.
echo Starting Spidy...
powershell -ExecutionPolicy Bypass -File "spidy_launcher.ps1"
goto END

:STOP
cls
echo [FULL STOP INITIATED]
call stop_spidy.bat /force
echo.
echo Shutting down...
timeout /t 3 >nul
exit

:END
exit
