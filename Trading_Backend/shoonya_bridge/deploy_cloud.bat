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
REM Production API Keys (Provided by User)
SET SHOONYA_USER=TIOPS3465L
SET SHOONYA_PWD=Shandeesh8667
SET SHOONYA_VC=TIOPS3465L_U
SET SHOONYA_API_KEY=97b50207a82e998c37bfea64c90ce846
SET SHOONYA_IMEI=abc1234
SET SHOONYA_FACTOR2=tiops3465l

REM CRITICAL: Enter your TOTP Secret (Text Code) below for Auto-Login
REM Example: SET SHOONYA_TOTP_SECRET=JBSWY3DPEHPK3PXP
SET SHOONYA_TOTP_SECRET=

ECHO Credentials Loaded.
ECHO.

ECHO [3] Launching Shoonya Bridge (Production Mode on Port 8001)...
ECHO This window acts as the Cloud Console. Minimize it, DO NOT CLOSE.
ECHO.
python shoonya_server.py
PAUSE
