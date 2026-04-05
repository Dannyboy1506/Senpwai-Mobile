#!/bin/bash
# Senpcli Mobile - One-click APK build for WSL Kali
# Usage: wsl bash ~/Desktop/senpwai-mobile/build_apk.sh

set -e

echo "=========================================="
echo "  Senpcli Mobile - APK Build"
echo "=========================================="

echo ""
echo "[1/7] Updating system..."
sudo apt update -y

echo "[2/7] Installing build dependencies..."
sudo apt install -y python3 python3-venv python3-dev build-essential \
    git zip unzip openjdk-11-jdk autoconf automake \
    libtool libssl-dev pkg-config zlib1g-dev \
    libncurses5-dev libncursesw5-dev libreadline-dev \
    libsqlite3-dev libgdbm-dev libdb5.3-dev libbz2-dev \
    libexpat1-dev liblzma-dev libffi-dev ffmpeg \
    cmake wget curl

echo "[3/7] Setting up Python virtual environment..."
cd ~
if [ ! -d "senpwai-venv" ]; then
    python3 -m venv senpwai-venv
fi
source ~/senpwai-venv/bin/activate

echo "[4/7] Installing Python packages..."
pip install --upgrade pip
pip install buildozer cython

echo "[5/7] Copying project from Windows..."
rm -rf ~/senpwai-mobile
cp -r /mnt/c/Users/TheBoys/Desktop/senpwai-mobile ~/senpwai-mobile
cd ~/senpwai-mobile

echo "[6/7] Configuring build..."

echo "[7/7] Building APK (20-40 min on first build)..."
buildozer android debug

echo ""
echo "=========================================="
echo "  Build Complete!"
echo "=========================================="
echo "APK: ~/senpwai-mobile/bin/senpcli-1.0.0-debug.apk"
echo ""
echo "Copy to Windows:"
echo "  cp ~/senpwai-mobile/bin/*.apk /mnt/c/Users/TheBoys/Desktop/"
