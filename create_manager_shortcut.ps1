$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\Spidy Manager.lnk")
$Shortcut.TargetPath = "C:\Users\Shandeesh R P\spidy\spidy_manager.bat"
$Shortcut.WorkingDirectory = "C:\Users\Shandeesh R P\spidy"
$Shortcut.IconLocation = "C:\Windows\System32\shell32.dll,238" # Cool gear/system icon
$Shortcut.Save()
Write-Host "Shortcut created on Desktop: $DesktopPath\Spidy Manager.lnk"

# Remove the old "Stop Spidy" shortcut if it exists to reduce clutter
$OldShortcut = "$DesktopPath\Stop Spidy.lnk"
if (Test-Path $OldShortcut) {
    Remove-Item $OldShortcut
    Write-Host "Removed old 'Stop Spidy' shortcut."
}
