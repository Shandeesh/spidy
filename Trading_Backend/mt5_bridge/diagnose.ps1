$ErrorActionPreference = "Continue"

Write-Host "Starting sxstrace..."
$traceJob = Start-Process sxstrace -ArgumentList "Trace -logfile:mt5_trace.etl" -PassThru

Write-Host "Waiting 2 seconds for trace to start..."
Start-Sleep -Seconds 2

Write-Host "Attempting to launch MT5..."
python "c:\Users\Shandeesh R P\spidy\Trading_Backend\mt5_bridge\debug_mt5_launch.py"

Write-Host "Stopping sxstrace..."
Start-Process sxstrace -ArgumentList "StopTrace" -Wait

Write-Host "Parsing trace..."
sxstrace Parse -logfile:mt5_trace.etl -outfile:mt5_trace.txt

Write-Host "Done. Check mt5_trace.txt."
