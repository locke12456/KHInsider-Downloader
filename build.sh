@echo off
echo === KHInsider Downloader Build (Windows) ===

REM Install build dependency
pip install pyinstaller

REM Clean previous build
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

REM Build
python -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "KHInsider Downloader" ^
    --add-data "locales;locales" ^
    --add-data "khinsider;khinsider" ^
    --hidden-import bs4 ^
    --hidden-import requests ^
    --hidden-import yaml ^
    --icon NONE ^
    khinsider_downloader_gui.py

echo.
if exist "dist\KHInsider Downloader.exe" (
    echo Build successful! Output: dist\KHInsider Downloader.exe
) else (
    echo Build failed!
)
pause