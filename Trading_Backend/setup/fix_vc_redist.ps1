# Download and Install VC++ Redistributable (2015-2022) x64
$url = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
$outPath = "$env:TEMP\vc_redist.x64.exe"

Write-Host "Downloading Visual C++ Redistributable..."
Invoke-WebRequest -Uri $url -OutFile $outPath

Write-Host "Installing... (Takes a moment, please approve UAC if prompted)"
Start-Process -FilePath $outPath -ArgumentList "/install", "/passive", "/norestart" -Wait -Verb RunAs

Write-Host "Installation Complete. Try running the bridge server again."
Remove-Item $outPath -ErrorAction SilentlyContinue
