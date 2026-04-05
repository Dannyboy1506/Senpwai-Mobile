# Senpcli Mobile

Android anime downloader app built with Kivy.

## Project Structure

```
senpwai-mobile/
├── main.py                    # Kivy App entry point
├── screens/
│   ├── home_screen.py         # Search, results, episode selection
│   ├── download_screen.py     # Active/completed/failed downloads
│   ├── library_screen.py      # Downloaded anime browser + player
│   └── settings_screen.py     # Quality, site, folder settings
├── services/
│   ├── downloader.py          # Download manager with queue + threads
│   ├── scraper.py             # Download class + HTTP client
│   └── storage.py             # File management, resume scanning
├── widgets/                   # Custom widget definitions
├── kv/                        # Kivy layout files (embedded in Python)
├── icon.png                   # 512x512 app icon
├── buildozer.spec             # Android build configuration
├── build_apk.sh               # One-click build script for WSL
└── requirements.txt           # Python dependencies
```

## Features

- Search anime on Pahe and Gogo
- Download episodes with progress tracking
- Pause, resume, cancel downloads
- Auto-resume partial downloads on app restart
- Browse downloaded anime library
- Built-in video playback
- Configurable quality, site, sub/dub
- Dark theme
- Storage management

## Running on Desktop (Testing)

```bash
pip install kivy requests anitopy appdirs tqdm plyer
cd senpwai-mobile
python main.py
```

## Building APK (WSL Kali)

### Option 1: One-click script
```bash
wsl bash ~/Desktop/senpwai-mobile/build_apk.sh
```

### Option 2: Manual steps
```bash
# Start WSL Kali
wsl

# Install dependencies (openjdk-11)
sudo apt update
sudo apt install -y python3 python3-venv python3-dev build-essential git zip unzip \
    openjdk-11-jdk autoconf automake libtool libssl-dev pkg-config zlib1g-dev ffmpeg cmake

# Create and activate virtual environment
python3 -m venv ~/senpwai-venv
source ~/senpwai-venv/bin/activate

# Install buildozer in venv
pip install --upgrade pip
pip install buildozer cython

# Copy project and build
cp -r /mnt/c/Users/TheBoys/Desktop/senpwai-mobile ~/senpwai-mobile
cd ~/senpwai-mobile
buildozer android debug
```

Output APK: `~/senpwai-mobile/bin/senpcli-1.0.0-debug.apk`

## Installing APK

```bash
# Via ADB
adb install bin/senpcli-1.0.0-debug.apk

# Or copy to phone storage and install manually
cp bin/senpcli-1.0.0-debug.apk /mnt/c/Users/TheBoys/Desktop/
```

## Storage Location

- Android: `/storage/emulated/0/Download/Senpcli/`
- Desktop: `~/.senpwai-mobile/`

## Config

App settings saved to:
- Android: App-specific storage
- Desktop: `~/.senpwai-mobile/app_config.json`
