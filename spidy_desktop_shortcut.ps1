$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$OneDriveDesktop = "$env:UserProfile\OneDrive\Desktop"

$ShortcutName = "Spidy AI.lnk"
$ShortcutPath = Join-Path $DesktopPath $ShortcutName

# List of paths to check for cleanup
$PathsToCheck = @(
    $DesktopPath,
    $OneDriveDesktop,
    "C:\Users\Public\Desktop"
)

# Cleanup loop
foreach ($Path in $PathsToCheck) {
    if (Test-Path $Path) {
        # Valid old names to remove
        $OldNames = @("Spidy AI Terminal.lnk", "Spidy AI Terminal")
        
        foreach ($Name in $OldNames) {
            $FullPath = Join-Path $Path $Name
            if (Test-Path $FullPath) {
                Remove-Item $FullPath -Force -ErrorAction SilentlyContinue
                Write-Host "Removed old shortcut: $FullPath"
            }
        }
    }
}

# New Target: PowerShell executing the launcher
$TargetExe = "powershell.exe"
$LauncherScript = "C:\Users\Shandeesh R P\spidy\spidy_launcher.ps1"
$Arguments = "-NoExit -ExecutionPolicy Bypass -File `"$LauncherScript`""

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetExe
$Shortcut.Arguments = $Arguments
$Shortcut.IconLocation = "C:\Users\Shandeesh R P\spidy\spidy_icon.ico" 
$Shortcut.Description = "Launch Spidy AI"
$Shortcut.Save()

Write-Host "Shortcut created at: $ShortcutPath"
