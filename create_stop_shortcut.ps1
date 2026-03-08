$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\Stop Spidy.lnk")
$Shortcut.TargetPath = "C:\Users\Shandeesh R P\spidy\stop_spidy.bat"
$Shortcut.IconLocation = "C:\Windows\System32\shell32.dll,27" # Red shutdown icon
$Shortcut.Save()
Write-Host "Shortcut created on Desktop: $DesktopPath\Stop Spidy.lnk"
