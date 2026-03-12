Write-Host "=== KHInsider Downloader Build (PowerShell) ===" -ForegroundColor Cyan

# Install build dependency
pip install pyinstaller

# Clean previous build
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
if (Test-Path build) { Remove-Item -Recurse -Force build }

# Build
python -m PyInstaller `
    --noconfirm `
    --onefile `
    --windowed `
    --name "KHInsider Downloader" `
    --add-data "locales;locales" `
    --add-data "khinsider;khinsider" `
    --icon NONE `
    khinsider_downloader_gui.py

if (Test-Path "dist\KHInsider Downloader.exe") {
    Write-Host "`nBuild successful! Output: dist\KHInsider Downloader.exe" -ForegroundColor Green
} else {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}