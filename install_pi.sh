#!/usr/bin/env bash
set -euo pipefail

sudo apt update
sudo apt install -y \
  python3-dev \
  python3-venv \
  portaudio19-dev \
  libasound2-dev \
  espeak-ng \
  ffmpeg \
  libatlas-base-dev \
  libopenblas-dev \
  libhdf5-dev \
  libjpeg-dev \
  zlib1g-dev \
  fonts-dejavu \
  fonts-liberation

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-pi.txt

echo "Install complete. Activate with: source .venv/bin/activate"
echo "Run preflight with: VISION_RPI_MODE=1 python tools/rpi_preflight.py"
