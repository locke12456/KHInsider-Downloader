```markdown
# KHInsider Downloader

A PyQt6 GUI application for batch downloading game soundtracks from [downloads.khinsider.com](https://downloads.khinsider.com).

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- 🎵 Browse and download entire albums or selected tracks
- 🎨 Clean PyQt6 GUI with album preview table
- 🌍 Multi-language support (English, 繁體中文, 简体中文, 日本語, 한국어)
- 📂 Choose output format (MP3, FLAC, etc.) and download directory
- ⚡ Background downloading with progress tracking
- 🔄 Auto-retry on connection failures (up to 3 attempts)
- ❌ Cancel downloads at any time

## Screenshots

*(Add screenshots here)*

## Prerequisites

- Python 3.10 or higher
- Git (for cloning with submodule)

## Installation

### 1. Clone the repository

```

git clone --recurse-submodules https://github.com/YOUR_USERNAME/khinsider-downloader.git

cd khinsider-downloader

```

If you already cloned without `--recurse-submodules`:

```

git submodule update --init --recursive

```

### 2. Install dependencies

```

pip install -r requirements.txt

```

### 3. Run

```

python khinsider_downloader_[gui.py](http://gui.py)

```

## Usage

1. Enter an album URL or slug in the input field
   - Full URL: `https://downloads.khinsider.com/game-soundtracks/album/pangya-windows-gamerip-2004`
   - Or just the slug: `pangya-windows-gamerip-2004`
2. Click **Load** (or press Enter)
3. Select the desired audio format from the dropdown
4. (Optional) Choose an output directory — defaults to a folder named after the album
5. Check/uncheck tracks as needed
6. Click **Download**

## Internationalization (i18n)

The app auto-detects your system language. You can also switch languages at runtime via the dropdown in the top-right corner.

Supported locales:
| Code    | Language |
|---------|----------|
| `en`    | English  |
| `zh-TW` | 繁體中文  |
| `zh`    | 简体中文  |
| `ja`    | 日本語   |
| `ko`    | 한국어   |

Translation files are in `locales/*.yml`. Feel free to edit them or add new languages.

## Building Standalone Executable

See `build.bat` (Windows) or use PyInstaller directly:

```

python -m PyInstaller --noconfirm --onefile --windowed \

--name "KHInsider Downloader" \

--add-data "locales:locales" \

--add-data "khinsider:khinsider" \

khinsider_downloader_[gui.py](http://gui.py)

```

The executable will be in the `dist/` folder.

## Project Structure

```

khinsider-downloader/

├── khinsider/                  # git submodule (obskyr/khinsider)

│   └── [khinsider.py](http://khinsider.py)

├── locales/

│   ├── en.yml

│   ├── zh-TW.yml

│   ├── zh.yml

│   ├── ja.yml

│   └── ko.yml

├── khinsider_downloader_[gui.py](http://gui.py) # Main application

├── requirements.txt

├── build.bat                   # Windows build script

├── [build.sh](http://build.sh)                    # Linux/macOS build script

└── [README.md](http://README.md)

```

## Credits

- [obskyr/khinsider](https://github.com/obskyr/khinsider) — KHInsider download library
- [python-i18n](https://pypi.org/project/python-i18n/) — Internationalization
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — GUI framework

## License

MIT License
```
