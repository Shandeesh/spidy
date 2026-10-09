@echo off
TITLE Shoonya Cloud Node - Production
COLOR 0A
CLS

ECHO ===================================================
ECHO    SPIDY AI - SHOONYA CLOUD NODE DEPLOYMENT
ECHO ===================================================
ECHO.
ECHO [1] Installing Python Dependencies...
pip install -r requirements.txt
pip install --upgrade NorenRestApiPy pyotp
ECHO.

ECHO [2] Configuring Environment...
REM shoonya_server.py loads credentials from the repository-root .env file.
REM Keep that file local and use .env.example as the template.
IF NOT EXIST "%~dp0..\..\.env" (
    ECHO [ERROR] Missing root .env file. Copy .env.example and configure Shoonya credentials first.
    PAUSE
    EXIT /B 1
)
ECHO Local credentials file found.
ECHO.

ECHO [3] Launching Shoonya Bridge (Production Mode on Port 8001)...
ECHO This window acts as the Cloud Console. Minimize it, DO NOT CLOSE.
ECHO.
python shoonya_server.py
PAUSE
