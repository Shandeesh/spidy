
$DesktopPath = [Environment]::GetFolderPath("Desktop")
Write-Host "Standard Desktop Path: $DesktopPath"
Get-ChildItem -Path $DesktopPath -Filter "Spidy*.lnk" -ErrorAction SilentlyContinue | Select-Object FullName

# Check OneDrive Desktop just in case
$OneDriveDesktop = "$env:UserProfile\OneDrive\Desktop"
if (Test-Path $OneDriveDesktop) {
    Write-Host "OneDrive Desktop Path: $OneDriveDesktop"
    Get-ChildItem -Path $OneDriveDesktop -Filter "Spidy*.lnk" -ErrorAction SilentlyContinue | Select-Object FullName
}

# Check Public Desktop
$PublicDesktop = "C:\Users\Public\Desktop"
if (Test-Path $PublicDesktop) {
    Write-Host "Public Desktop Path: $PublicDesktop"
    Get-ChildItem -Path $PublicDesktop -Filter "Spidy*.lnk" -ErrorAction SilentlyContinue | Select-Object FullName
}
