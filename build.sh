#!/usr/bin/env bash
set -e

echo "=== KHInsider Downloader Build (Linux/macOS) ==="

# Install build dependency
pip install pyinstaller

# Clean previous build
rm -rf dist build

# Build
python -m PyInstaller \
    --noconfirm \
    --onefile \
    --windowed \
    --name "KHInsider Downloader" \
    --add-data "locales:locales" \
    --add-data "khinsider:khinsider" \
    khinsider_downloader_gui.py

if [ -f "dist/KHInsider Downloader" ]; then
    echo ""
    echo "Build successful! Output: dist/KHInsider Downloader"
    chmod +x "dist/KHInsider Downloader"
else
    echo "Build failed!"
    exit 1
fi