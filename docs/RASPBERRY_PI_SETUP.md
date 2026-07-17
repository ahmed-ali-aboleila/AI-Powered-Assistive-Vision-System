# Raspberry Pi Setup

Target device: Raspberry Pi 4 Model B.

Recommended OS: Raspberry Pi OS 64-bit.

## 1. Clone

```bash
cd ~
git clone https://github.com/AhmedAli40/Assistive-Vision-Raspberry-Pi.git
cd Assistive-Vision-Raspberry-Pi
```

## 2. Install

```bash
chmod +x install_pi.sh run_pi.sh download_models.sh
./install_pi.sh
```

This installs:
- Python virtual environment `.venv`
- PortAudio/PyAudio support
- Linux audio dependencies
- `espeak-ng` offline TTS fallback
- Raspberry Pi Python requirements

## 3. Download Models

```bash
./download_models.sh
```

Google Drive folder:

```text
https://drive.google.com/drive/folders/1XIOsn-erryTL9f5AB7jxJTJ5kEhGC1cL?usp=drive_link
```

Expected structure:

```text
models/
  cnn_v3_final.h5
  cnn_v3_final.tflite
  vosk-model/
  vosk-model-ar-mgb2-0.4/
```

## 4. Preflight

```bash
source .venv/bin/activate
VISION_RPI_MODE=1 python tools/rpi_preflight.py
```

The result should end with:

```text
READY
```

If it prints `NOT READY`, read the missing dependency or missing model line and fix that item first.

## 5. Run

```bash
./run_pi.sh
```

Try another camera index:

```bash
VISION_CAMERA_INDEX=1 ./run_pi.sh
```

Show the OpenCV display window:

```bash
VISION_SHOW_WINDOW=1 ./run_pi.sh
```

Force `.h5` instead of TFLite:

```bash
VISION_USE_TFLITE=0 ./run_pi.sh
```

## Runtime Behavior

Raspberry Pi mode:
- Uses camera index `0` by default.
- Uses `models/cnn_v3_final.tflite` for emotion inference when available.
- Keeps face recognition, registration, emotion detection, Arabic/English commands, and TTS active.
- Disables the display window by default for headless use.

## First Real Test

1. Start the system with `./run_pi.sh`.
2. Say `vision`.
3. Say `vision who is this`.
4. Register a person with `vision register`.
5. Test a registered person.
6. Test an unknown person.
7. Test `vision pause` and `vision resume`.
8. Test `vision delete` only after confirming the names list is correct.

## Face Recognition Tips

- Register each important person in good light.
- During registration, face the camera, then slightly turn left/right, then change expression.
- If a registered person appears as unknown, use `vision improve person`.
- If a stranger is recognized as a registered person, use `vision new person` to register/correct them.

## Audio Tips

- Keep speakers away from the microphone.
- Use a USB microphone if possible.
- Run in a quiet room for the first calibration.
- Vosk offline commands need `models/vosk-model/` and `models/vosk-model-ar-mgb2-0.4/`.
- Google STT and Edge TTS work better with internet.

## Do Not Commit

These files are local/private and ignored by Git:

```text
models/
face_data.pkl
blocked.json
logs/
tts_cache/
```
