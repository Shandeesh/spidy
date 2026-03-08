@echo off
echo Killing Spidy Processes...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM node.exe /T 2>nul
taskkill /F /IM terminal64.exe /T 2>nul
echo All Spidy processes terminated.
timeout /t 2 >nul
exit
