# Assistive Vision System

An intelligent assistive system that combines real-time face recognition, emotion detection, and voice command processing to help visually impaired users identify people and understand emotions around them.

## Features

### 1. Face Recognition
- **DeepFace** integration with Facenet512 model for accurate face identification
- **Liveness Detection** using Local Binary Patterns (LBP) to prevent spoofing
- **Person Registration** with guided multi-angle capture (front, right, left, up)
- **Person Database Management** — add, delete, and list registered persons
- **Confidence Threshold** set at 0.5 for reliable identification

### 2. Emotion Detection
- **CNN-based emotion classifier** (`cnn_v3_final.h5`)
- Detects 7 emotions: **Happy, Sad, Angry, Fear, Surprise, Disgust, Neutral**
- Real-time emotion feedback with confidence percentages
- Combined with face recognition for contextual announcements

### 3. Speech-to-Text (STT)
- **Multi-engine support:**
  - **Vosk** (offline) — English & Arabic models
  - **Google Speech Recognition** (online fallback)
- **Voice Activation:** Say "vision" or "فيجن" to activate commands
- **Automatic Language Detection** and switching
- **Noise Calibration** for optimal microphone performance

### 4. Text-to-Speech (TTS)
- **Edge TTS** (neural voices) — primary engine
- **SAPI** (Windows) — fallback for offline use
- **Bilingual Support:** English and Arabic with automatic switching
- Smart fallback when internet connectivity is limited

### 5. Voice Commands

| Command (English) | Command (Arabic) | Action |
|-------------------|------------------|--------|
| "vision" | "فيجن" | Activate voice command mode |
| "register" | "تسجيل" | Register a new person |
| "delete" | "حذف" | Delete a registered person |
| "switch to Arabic" | "تبديل للعربية" | Switch TTS/STT to Arabic |
| "switch to English" | "تبديل للإنجليزية" | Switch TTS/STT to English |
| "yes" / "no" | "نعم" / "لا" | Confirm/cancel actions |

## System Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Camera Input   │────▶│   Face Processor │────▶│  Face Recognition│
└─────────────────┘     │  (DeepFace)       │     │  (Facenet512)   │
                        └──────────────────┘     └─────────────────┘
                                  │                        │
                                  ▼                        ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │ Emotion Detection│     │   Person DB     │
                        │  (CNN v3)        │     │  (Embeddings)   │
                        └──────────────────┘     └─────────────────┘
                                  │                        │
                                  └──────────┬─────────────┘
                                             ▼
                                   ┌──────────────────┐
                                   │  Logic Controller │
                                   │  (Decision Engine)│
                                   └──────────────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    ▼                        ▼                        ▼
           ┌─────────────┐        ┌─────────────────┐        ┌─────────────┐
           │  TTS Engine │        │  STT Engine     │        │   Logger    │
           │ (Edge/SAPI) │        │ (Vosk/Google)   │        │  (CSV)      │
           └─────────────┘        └─────────────────┘        └─────────────┘
```

## Installation

### Prerequisites
- Python 3.12+
- Windows (for SAPI TTS fallback)
- Webcam
- Microphone

### Dependencies
```bash
pip install pygame
pip install deepface
pip install tensorflow
pip install tf-keras
pip install edge-tts
pip install SpeechRecognition
pip install vosk
pip install pyttsx3  # SAPI fallback
```

### Model Files
Place the following in the `models/` directory:
- `cnn_v3_final.h5` — Emotion detection model

### Vosk Models (Optional - for offline STT)
Download and extract to project root:
- [English Model](https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip)
- [Arabic Model](https://alphacephei.com/vosk/models/vosk-model-ar-mgb2-0.4.zip)

## Usage

### Run the System
```bash
py -3.12 main.py
```

### First-Time Setup
1. The system will automatically calibrate your microphone
2. DeepFace will download Facenet512 on first run (~30 seconds)
3. Ensure proper lighting for face recognition

### Registering a New Person
1. Say **"vision"** to activate
2. Say **"register"**
3. Say the person's name when prompted
4. Confirm with **"yes"**
5. Follow the voice instructions:
   - Look straight at the camera
   - Turn head to the right
   - Turn head to the left
   - Tilt head slightly upward

### Deleting a Person
1. Say **"vision"**
2. Say **"delete"**
3. Say the name to delete
4. Confirm with **"yes"**

### Switching Languages
- Say **"switch to Arabic"** or **"تبديل للعربية"**
- Say **"switch to English"** or **"تبديل للإنجليزية"**

## Project Structure

```
emotion & face recognition final_v6/
│
├── main.py                      # Main application entry point
├── models/
│   └── cnn_v3_final.h5         # Emotion detection CNN model
│
├── face_processor.py           # DeepFace integration & liveness
├── emotion_detector.py         # Emotion classification logic
├── stt_engine.py              # Speech-to-text handler
├── tts_engine.py              # Text-to-speech handler
├── logic_controller.py         # Command processing & state machine
├── database.py                # Face embeddings database
├── logger.py                  # Session logging to CSV
│
├── logs/                      # Session logs (CSV format)
└── README.md                  # This file
```

## System Logs

All sessions are automatically logged to:
```
logs\session_YYYYMMDD_HHMMSS.csv
```

Logs include:
- Timestamps
- Detected emotions
- Recognized persons
- Voice commands processed
- System events

## Performance Notes

- **Face Recognition:** ~30s initial model load, then real-time
- **Emotion Detection:** Runs at camera frame rate
- **STT Response:** ~1-2 seconds for command recognition
- **TTS Response:** Near-instant with Edge TTS, slight delay with SAPI
- **Liveness Check:** LBP variance > 18.0 required

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Arabic Vosk not found" | Download Arabic model from link in console |
| "Edge TTS timeout" | System auto-falls back to SAPI (Windows) |
| Face not recognized | Ensure good lighting, look directly at camera |
| False emotion readings | Check LBP score (should be > 18.0) |
| Mic not responding | Re-run calibration, check Windows mic permissions |
| "Command not recognized" | Speak clearly, reduce background noise |

## Raspberry Pi 4 Noise Cancellation & Echo Suppression

To optimize voice command accuracy in noisy environments when running the system on a Raspberry Pi 4, it is highly recommended to configure driver-level noise suppression (denoise) and Automatic Gain Control (AGC) using the SpeexDSP ALSA plugin.

### 1. Install Speex DSP ALSA Plugins
On Raspberry Pi OS (Debian-based), run:
```bash
sudo apt-get update
sudo apt-get install libasound2-plugins libspeexdsp-dev
```

### 2. Configure ALSA (`/etc/asound.conf`)
Create or edit your system-wide ALSA configuration file:
```bash
sudo nano /etc/asound.conf
```
Add the following configuration to define an automatic gain control (AGC) and denoising plug:

```text
# Default capture device with Speex pre-processing
pcm.speex_mic {
    type speex
    slave.pcm "plughw:1,0" # Change to match your USB mic card/device index
    frames 160
    denoise yes
    agc yes
    agc_level 8000
    dereverb no
    echo no
}

# Redirect default ALSA capture to use the Speex plug
pcm.!default {
    type asym
    playback.pcm "plug:hw:0,0" # Default audio output (e.g. headphone jack)
    capture.pcm "speex_mic"
}
```
*Note: Run `arecord -l` to find the correct card and device index for your USB microphone/HAT and replace `plughw:1,0` accordingly.*

### 3. Test the Setup
Re-run the system. The microphone input will automatically pass through the Speex preprocessor, filtering background hums and amplifying quiet speech before it reaches the STT engine.

## Technologies Used

- **DeepFace** — Face recognition & analysis
- **TensorFlow/Keras** — Emotion model inference
- **Pygame** — Audio playback handling
- **Vosk** — Offline speech recognition
- **Google Speech API** — Online speech recognition fallback
- **Edge TTS** — Neural text-to-speech
- **SAPI** — Windows native TTS fallback
- **OpenCV** — Computer vision operations

## License

This project was developed as a graduation/final year project.

## Authors

- [Your Name]
- [Supervisor Name]

---

**Note:** This system is designed for assistive purposes to help visually impaired individuals. Ensure compliance with privacy regulations when capturing and storing facial data.
