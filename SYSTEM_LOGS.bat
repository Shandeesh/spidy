@echo off
powershell -Command "Get-Content 'Trading_Backend\mt5_bridge\system_logs.txt' -Wait"
