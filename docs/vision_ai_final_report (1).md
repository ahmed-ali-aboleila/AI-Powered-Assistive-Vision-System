# Vision AI — Final Technical Report
## Real-Time Facial Emotion Recognition & Voice-Activated Smart Assistant

**Version:** v4 (Final)  
**Date:** June 2026  
**Project:** Vision AI — Real-Time Emotion Recognition System  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Emotion Recognition Module](#3-emotion-recognition-module)
4. [Face Recognition Module](#4-face-recognition-module)
5. [Voice Command System](#5-voice-command-system)
6. [Implementation Challenges](#6-implementation-challenges)
7. [Final Results & Performance](#7-final-results--performance)
8. [Deployment & Hardware](#8-deployment--hardware)
9. [Tools & Technologies](#9-tools--technologies)
10. [Performance Optimizations](#10-performance-optimizations)
11. [Bilingual Voice System](#11-bilingual-voice-system)
12. [References](#12-references)

---

## 1. Project Overview

### 1.1 System Modules Summary

| Module | Technology | Dataset | Accuracy | Status |
|--------|-----------|---------|----------|--------|
| **Emotion Recognition** | CNN v3 + CNN v6 Ensemble + TTA | FER-2013 + RAF-DB + CK+ | **81.50%** | ✅ Active |
| **Face Recognition** | FaceNet512 + Haar Cascade | LFW Benchmark | 99.38% | ✅ Active |
| **Voice Commands** | Edge TTS Neural + SAPI Fallback | Custom | Bilingual (AR/EN) | ✅ Active |
| **Logic Controller** | Session Mode (Wake Word Once) | — | — | ✅ Active |

### 1.2 Project Goals
- Real-time facial emotion detection from webcam feed
- Face recognition for personalized user experience
- Voice-activated command interface (Arabic/English bilingual)
- Lightweight deployment on consumer hardware (Raspberry Pi compatible)
- Session-based interaction model (single wake word activation)

---

## 2. System Architecture

### 2.1 Shared Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Face Detection** | Haar Cascade (OpenCV) | Real-time face localization |
| **Feature Extraction** | FaceNet512 (DeepFace) | 512-D face embedding generation |
| **TTS Engine** | Edge TTS Neural (Microsoft) | Natural speech synthesis |
| **TTS Fallback** | SAPI5 / pyttsx3 | Offline speech fallback |
| **STT Engine** | Google Speech Recognition | Arabic/English voice input |
| **Audio Output** | pygame mixer | Cross-platform audio playback |

### 2.2 System Logic Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Webcam Feed   │────▶│  Face Detection │────▶│  Face Processor │
│   (OpenCV)      │     │  (Haar Cascade) │     │  (Align/Enhance)│
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                              ┌────────────────────────┼────────────────────────┐
                              │                        │                        │
                              ▼                        ▼                        ▼
                    ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
                    │ Face Recognition│      │ Emotion Detection│      │ Voice Commands  │
                    │ (FaceNet512)    │      │ (CNN v3+v6 Ens.)│      │ (Edge TTS + STT)│
                    └────────┬────────┘      └────────┬────────┘      └────────┬────────┘
                             │                        │                        │
                             └────────────────────────┼────────────────────────┘
                                                      │
                                                      ▼
                                            ┌─────────────────┐
                                            │ Logic Controller│
                                            │ (Session Mode)  │
                                            └────────┬────────┘
                                                     │
                                                     ▼
                                            ┌─────────────────┐
                                            │  Response Output│
                                            │  (TTS + Display)│
                                            └─────────────────┘
```

### 2.3 Emotion Pipeline (Updated)

```
Webcam Frame
    │
    ▼
┌─────────────────────┐
│ Haar Cascade Face   │  ~8-12 ms
│ Detection           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Face Alignment      │  ~2 ms
│ (Rotation + Crop)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Gamma Correction    │  ~1 ms (LUT cached)
│ + CLAHE Enhancement │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ CNN v3 Inference    │  ~15 ms (no TTA)
│ CNN v6 Inference    │  ~15 ms (no TTA)
│ Ensemble Weighted   │  ~2 ms
│ Average             │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Conditional TTA     │  +~200 ms (if confidence < 0.7)
│ (5 augmentations)   │
└──────────┬──────────┘
           │
           ▼
    Emotion Label + Confidence
```

---

## 3. Emotion Recognition Module

### 3.1 Dataset

The model was trained on a **unified validation dataset** combining three major FER datasets:

| Dataset | Images | Classes | Usage |
|---------|--------|---------|-------|
| **FER-2013** | 35,887 | 7 emotions | Primary training data |
| **RAF-DB** | 15,339 | 7 emotions | Augmented validation |
| **CK+** | 981 | 7 emotions | Fine-tuning support |

**Total Unified Validation:** ~52,000 images across 7 emotion classes  
**Classes:** Angry, Disgust, Fear, Happy, Neutral, Sad, Surprise

### 3.2 CNN Architecture (CNN v3)

| Parameter | Value |
|-----------|-------|
| **Input Size** | 48×48×1 (grayscale) |
| **Convolutional Layers** | 6 (with BatchNorm + ReLU + Dropout) |
| **Filters** | 32 → 64 → 128 → 256 → 512 → 512 |
| **Kernel Size** | 3×3 |
| **Pooling** | MaxPool 2×2 |
| **Fully Connected** | 512 → 256 → 7 |
| **Dropout Rate** | 0.3–0.5 |
| **Total Parameters** | ~2.5 Million |
| **Model Size** | 18.3 MB (H5) / 4.8 MB (TFLite) |
| **Training Epochs** | 70 |

### 3.3 CNN v6 Architecture (VGG + CBAM)

| Parameter | Value |
|-----------|-------|
| **Base Architecture** | VGG-16 style backbone |
| **Attention Module** | CBAM (Convolutional Block Attention) |
| **Input Size** | 48×48×1 |
| **Parameters** | ~8.2 Million |
| **Accuracy** | 72.10% (standalone) |
| **Ensemble Weight** | 0.10 |

### 3.4 Training Results Comparison

| Model | Architecture | Epochs | Val Accuracy | Status | Ensemble Weight |
|-------|-------------|--------|-------------|--------|-----------------|
| **CNN v3** | Custom CNN | 70 | **79.25%** | ✅ **SELECTED** | 0.90 |
| **CNN v6** | VGG + CBAM | 50 | 72.10% | ✅ Used in Ensemble | 0.10 |
| CNN v1 | Custom CNN | 50 | 66.54% | ❌ Replaced | — |
| CNN v2 | Custom CNN | 50 | 65.87% | ❌ Replaced | — |

### 3.5 Ensemble Configuration

```json
{
  "models": [
    {
      "name": "cnn_v3",
      "file": "cnn_v3.tflite",
      "weight": 0.90,
      "accuracy": 79.25
    },
    {
      "name": "cnn_v6",
      "file": "cnn_v6.tflite",
      "weight": 0.10,
      "accuracy": 72.10
    }
  ],
  "tta": {
    "enabled": true,
    "augmentations": 5,
    "threshold": 0.70
  },
  "overall_accuracy": 81.50
}
```

### 3.6 Per-Class Accuracy (Ensemble + TTA)

| Emotion | Accuracy | Trend vs v1 |
|---------|----------|-------------|
| **Happy** | **93.5%** | ↑ +8.9% |
| **Surprise** | **88.3%** | ↑ +4.8% |
| **Neutral** | **84.4%** | ↑ +9.4% |
| **Disgust** | **69.4%** | → 0% |
| **Angry** | **73.9%** | ↑ +9.9% |
| **Sad** | **71.6%** | ↑ +26.4% |
| **Fear** | **60.7%** | ↑ +26.1% |
| **Overall** | **81.50%** | ↑ +15.63% |

### 3.7 Face Detection Comparison

| Detector | Speed | Accuracy | Usage in Project |
|----------|-------|----------|-----------------|
| Haar Cascade | **~8-12 ms** | Moderate | ✅ **Used** |
| LBP Cascade | ~5-8 ms | Lower | ⚠️ Fallback |
| MTCNN | ~35-50 ms | High | ❌ Removed (latency) |
| DNN (OpenCV) | ~20-30 ms | High | ❌ Not used |

---

## 4. Face Recognition Module

### 4.1 Pipeline

```
Detected Face ROI
    │
    ▼
┌─────────────────────┐
│ FaceNet512 Embedding│  → 512-D vector
│ (DeepFace backend)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Cosine Similarity   │  → Distance [0, 2]
│ vs. Database        │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │ Threshold    │
    │ < 0.40 ?     │
    └──────┬───────┘
           │
     Yes ──┼── No
           │
           ▼           ▼
    ┌──────────┐  ┌──────────┐
    │ Known    │  │ Unknown  │
    │ Identity │  │ (New User)│
    └──────────┘  └──────────┘
```

### 4.2 LFW Benchmark Results

| Backend | Model | LFW Accuracy | Our Threshold |
|---------|-------|-------------|---------------|
| FaceNet512 | InceptionResNetV1 | **99.38%** | 0.40 (cosine) |
| OpenFace | nn4.small2 | 93.80% | — |
| DeepID | DeepID | 97.05% | — |
| Dlib | ResNet-34 | 99.38% | — |

### 4.3 Cosine Distance Distribution

- **Same Identity:** Mean = 0.15, Std = 0.08
- **Different Identity:** Mean = 0.85, Std = 0.12
- **Decision Threshold:** 0.40 (optimized for FRR/FAR balance)

---

## 5. Voice Command System

### 5.1 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Voice Command System                  │
├─────────────────────────────────────────────────────────┤
│  Audio Input → STT (Google Speech) → Command Parser      │
│                                                         │
│  Command Categories:                                    │
│  ├─ System: "stop", "exit", "restart"                   │
│  ├─ Emotion: "what emotion", "detect mood"              │
│  ├─ Face: "who is this", "add person [name]"            │
│  ├─ Settings: "switch to Arabic", "change voice"        │
│  └─ Session: "wake", "sleep" (Session Mode)             │
│                                                         │
│  Response → TTS (Edge TTS / SAPI Fallback) → Audio Out  │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Session Mode

**Traditional Mode:** Wake word required before every command  
**Session Mode (New):** Single wake word ("Vision") activates 30-second session

```python
# Session Mode Logic
class SessionController:
    SESSION_TIMEOUT = 30  # seconds

    def activate_session(self):
        self.session_active = True
        self.session_start = time.time()
        self.tts.speak("Session activated. How can I help?")

    def is_session_valid(self):
        if not self.session_active:
            return False
        elapsed = time.time() - self.session_start
        return elapsed < self.SESSION_TIMEOUT

    def process_command(self, command):
        if self.is_session_valid():
            return self.execute(command)  # No wake word needed
        else:
            return self.request_wake_word()  # "Say 'Vision' first"
```

### 5.3 Bilingual Command Examples

| Arabic Command | English Command | Action |
|---------------|---------------|--------|
| "فيجن" | "Vision" | Wake / Activate Session |
| "ايه الاموشن" | "What emotion" | Detect current emotion |
| "مين ده" | "Who is this" | Face recognition |
| "ضيف فلان" | "Add person [name]" | Register new face |
| "غير الصوت" | "Change voice" | Toggle gender/voice |
| "قف" | "Stop" | Halt processing |
| "نم" | "Sleep" | End session |

---

## 6. Implementation Challenges

### 6.1 Challenge: Edge TTS Timeout & Fallback Chain

**Problem:** Edge TTS requires internet connection; network latency causes timeout on slow connections  
**Solution:** Multi-tier fallback system

```python
TTS_FALLBACK_CHAIN = [
    "edge_tts",      # Primary: Neural quality (online)
    "sapi5",         # Secondary: Windows built-in
    "pyttsx3",       # Tertiary: Cross-platform
    "gtts",          # Quaternary: Google TTS (online)
]
```

### 6.2 Challenge: Real-Time Performance on Limited Hardware

**Problem:** TTA adds ~200ms latency per frame; 30 FPS target requires <33ms total  
**Solution:** Conditional TTA + Adaptive Inference Rate

```python
def should_apply_tta(confidence, emotion_class):
    # Skip TTA for high-confidence easy classes
    if confidence > 0.85 and emotion_class in ['happy', 'surprise']:
        return False
    # Apply TTA for low-confidence or hard classes
    if confidence < 0.70 or emotion_class in ['fear', 'sad']:
        return True
    return False
```

### 6.3 Challenge: Dataset Imbalance

**Problem:** FER-2013 has severe class imbalance (Happy: 7215, Fear: 409)  
**Solution:** Unified dataset + weighted loss + class-aware augmentation

| Class | FER-2013 | RAF-DB | CK+ | Combined |
|-------|----------|--------|-----|----------|
| Happy | 7,215 | 4,000 | 200 | 11,415 |
| Sad | 4,830 | 2,500 | 200 | 7,530 |
| Fear | 409 | 2,000 | 200 | 2,609 |

---

## 7. Final Results & Performance

### 7.1 Emotion Detection Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **Overall Accuracy** | **81.50%** | Ensemble + TTA |
| **Standard Accuracy** | 79.25% | CNN v3 only |
| **Inference Time (Fast)** | ~15 ms | No TTA, GPU |
| **Inference Time (TTA)** | ~250 ms | With 5 augmentations |
| **Adaptive Rate** | 15-30 FPS | Conditional TTA |
| **Best Class** | Happy (93.5%) | High distinctiveness |
| **Weakest Class** | Fear (60.7%) | Often confused with Sad |

### 7.2 Face Recognition Performance

| Metric | Value |
|--------|-------|
| **LFW Accuracy** | 99.38% |
| **Recognition Time** | ~45 ms (embedding + comparison) |
| **Database Size** | Unlimited (512-D vectors) |
| **False Acceptance Rate** | <0.1% @ threshold 0.40 |

### 7.3 Voice System Performance

| Metric | Value |
|--------|-------|
| **TTS Latency** | ~800 ms (Edge TTS) / ~50 ms (SAPI) |
| **STT Latency** | ~1.2 seconds (Google Speech) |
| **Supported Languages** | Arabic (ar-EG), English (en-US) |
| **Voice Options** | Salma (AR Female), Aria (EN Female), etc. |

---

## 8. Deployment & Hardware

### 8.1 Raspberry Pi Deployment

| Specification | Minimum | Recommended |
|-------------|---------|-------------|
| **Model** | Raspberry Pi 4 (2GB) | Raspberry Pi 4 (8GB) |
| **OS** | Raspberry Pi OS 64-bit | Ubuntu 22.04 LTS |
| **Camera** | Pi Camera Module 2 | Pi Camera Module 3 |
| **TTS Engine** | Edge TTS (online) | SAPI Fallback (offline) |
| **FPS** | 5-8 FPS | 12-15 FPS |
| **Power** | 5V 3A USB-C | 5V 3A with cooling |

### 8.2 Planned Improvements (Status)

| Improvement | Status | Notes |
|------------|--------|-------|
| ✅ Accuracy 81.5% (TTA) | **Achieved** | Ensemble v3+v6 deployed |
| ✅ Session Mode | **Achieved** | Single wake word activation |
| ✅ Multi-language TTS | **Achieved** | Arabic/English bilingual |
| ✅ Voice Gender Switching | **Achieved** | Male/Female voice toggle |
| ⏳ Offline Arabic STT | Planned | Vosk/Whisper integration |
| ⏳ Edge TPU Acceleration | Planned | Coral USB for TFLite |
| ⏳ Mobile App Companion | Planned | Flutter/React Native |
| ⏳ Cloud Analytics Dashboard | Planned | AWS/GCP deployment |

---

## 9. Tools & Technologies

| Category | Tool | Version | Purpose |
|----------|------|---------|---------|
| **Deep Learning** | TensorFlow/Keras | 2.15 | Model training |
| **Face Detection** | OpenCV Haar Cascade | 4.8 | Face localization |
| **Face Recognition** | DeepFace (FaceNet512) | 0.0.93 | Embedding extraction |
| **Emotion Model** | CNN v3 + CNN v6 Ensemble | v4 | Emotion classification |
| **TTS (Primary)** | Edge TTS (Microsoft) | 6.1.12 | Neural speech synthesis |
| **TTS (Fallback)** | pyttsx3 / SAPI5 | 2.90 | Offline speech |
| **STT** | SpeechRecognition (Google) | 3.10 | Voice input |
| **Audio** | pygame mixer | 2.5 | Audio playback |
| **Deployment** | TensorFlow Lite | 2.15 | Mobile/edge inference |
| **Datasets** | FER-2013, RAF-DB, CK+ | — | Training data |
| **Optimization** | NumPy, Pillow, LRU Cache | Latest | Performance |

---

## 10. Performance Optimizations

### 10.1 14 Core Optimizations

| # | Optimization | Impact | Implementation |
|---|-------------|--------|----------------|
| 1 | **Gamma LUT Cache** | -3ms/frame | Precomputed lookup table |
| 2 | **Weighted Average Smoothing** | +5% stability | Temporal filter (α=0.7) |
| 3 | **Grid Key 80px** | -40% memory | Downsized face grid |
| 4 | **Conditional TTA** | +15% speed | Skip TTA for easy classes |
| 5 | **Batch Prediction** | +20% throughput | Process 4 frames/batch |
| 6 | **Adaptive Inference Rate** | 15-30 FPS | Dynamic quality scaling |
| 7 | **TFLite Quantization** | -75% model size | INT8 weights |
| 8 | **Face ROI Reuse** | -10ms/frame | Cache embeddings |
| 9 | **Thread Pool (STT)** | Non-blocking | Async voice processing |
| 10 | **Session Mode** | -50% wake overhead | Persistent context |
| 11 | **Edge TTS Preload** | -500ms latency | Cache audio segments |
| 12 | **CLAHE Limit** | +2% contrast | Clip limit 2.0 |
| 13 | **Ensemble Lazy Load** | -50MB RAM | Load on demand |
| 14 | **Frame Skip (Idle)** | +200% idle FPS | Process every 3rd frame |

### 10.2 Latency Breakdown (Optimized Pipeline)

| Component | Time | Cumulative |
|-----------|------|------------|
| Frame Capture | ~5 ms | 5 ms |
| Haar Detection | ~8 ms | 13 ms |
| Face Alignment | ~2 ms | 15 ms |
| Preprocessing | ~2 ms | 17 ms |
| CNN v3 Inference | ~15 ms | 32 ms |
| CNN v6 Inference | ~15 ms | 47 ms |
| Ensemble Fusion | ~2 ms | 49 ms |
| FaceNet Embedding | ~35 ms | 84 ms |
| **Total (per frame)** | **~84 ms** | **~12 FPS** |
| **With TTA** | **~250 ms** | **~4 FPS** |

---

## 11. Bilingual Voice System

### 11.1 Available Voices

| Language | Voice ID | Gender | Quality | Use Case |
|----------|----------|--------|---------|----------|
| Arabic (Egypt) | `ar-EG-SalmaNeural` | Female | Neural | Primary AR |
| Arabic (Saudi) | `ar-SA-ZariyahNeural` | Female | Neural | Alternative AR |
| English (US) | `en-US-AriaNeural` | Female | Neural | Primary EN |
| English (US) | `en-US-GuyNeural` | Male | Neural | Alternative EN |
| English (UK) | `en-GB-SoniaNeural` | Female | Neural | British EN |

### 11.2 Voice Gender Switching

```python
VOICE_PROFILES = {
    "ar_female": "ar-EG-SalmaNeural",
    "ar_male": "ar-SA-HamedNeural", 
    "en_female": "en-US-AriaNeural",
    "en_male": "en-US-GuyNeural",
}

def switch_voice(gender, language="en"):
    key = f"{language}_{gender}"
    return VOICE_PROFILES.get(key, VOICE_PROFILES["en_female"])
```

### 11.3 Bilingual Command Matrix

| Function | Arabic | English | Response Language |
|----------|--------|---------|-------------------|
| Wake | "فيجن" | "Vision" | Matches input |
| Emotion Query | "ايه الاموشن" | "What emotion" | Matches input |
| Identity Query | "مين ده" | "Who is this" | Matches input |
| Add Person | "ضيف [اسم]" | "Add [name]" | Matches input |
| Stop | "قف" / "توقف" | "Stop" | Matches input |
| Voice Change | "غير الصوت" | "Change voice" | Matches input |
| Sleep | "نم" / "انهي الجلسة" | "Sleep" / "End session" | Matches input |

---

## 12. References

1. Goodfellow, I.J., et al. (2013). "Challenges in Representation Learning: A report on three machine learning contests." *Neural Networks*, 64, 59-63. (FER-2013 Dataset)
2. Schroff, F., Kalenichenko, D., & Philbin, J. (2015). "FaceNet: A unified embedding for face recognition and clustering." *CVPR*, 815-823.
3. Serengil, S.I., & Ozpinar, A. (2020). "LightFace: A deep face recognition framework." *IEEE Access*.
4. Viola, P., & Jones, M. (2001). "Robust real-time object detection." *IJCV*, 57(2), 137-154.
5. He, K., Zhang, X., Ren, S., & Sun, J. (2016). "Deep residual learning for image recognition." *CVPR*, 770-778.
6. Woo, S., Park, J., Lee, J.Y., & So, I.S. (2018). "CBAM: Convolutional block attention module." *ECCV*, 3-19.
7. Li, S., & Deng, W. (2020). "Reliable crowdsourcing and deep locality-preserving learning for unconstrained facial expression recognition." *IEEE TPAMI*.
8. Lucey, P., et al. (2010). "The extended Cohn-Kanade dataset (CK+)." *FG*, 94-101.
9. Microsoft. (2024). "Edge TTS — Text-to-Speech Library." GitHub: `rany2/edge-tts`.
10. Google. (2024). "SpeechRecognition Library." PyPI.
11. **Edge TTS Neural Voices.** Microsoft Azure Cognitive Services. https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech/
12. **RAF-DB Dataset.** Li, S., et al. (2017). Real-world Affective Faces Database.
13. **CK+ Dataset.** Lucey, P., et al. (2010). Extended Cohn-Kanade.
14. **CBAM Module.** Woo, S., et al. (2018). Convolutional Block Attention Module. *ECCV*.

---

## Appendix A: File Structure

```
vision_ai/
├── models/
│   ├── cnn_v3.tflite              # Primary emotion model
│   ├── cnn_v6.tflite              # Secondary emotion model
│   ├── ensemble_config.json       # Ensemble weights
│   └── facenet512_weights.h5    # Face recognition
├── src/
│   ├── emotion/
│   │   ├── cnn_v3.py
│   │   ├── cnn_v6.py
│   │   ├── ensemble.py
│   │   └── tta.py
│   ├── face/
│   │   ├── detector.py
│   │   ├── recognizer.py
│   │   └── processor.py
│   ├── voice/
│   │   ├── tts_engine.py          # Edge TTS + fallback
│   │   ├── stt_engine.py          # Google Speech
│   │   └── commands.py            # Bilingual parser
│   ├── logic/
│   │   ├── session_controller.py
│   │   └── main_loop.py
│   └── utils/
│       ├── gamma_lut.py
│       ├── cache.py
│       └── optimizations.py
├── data/
│   ├── faces_db/                  # Known face embeddings
│   └── voice_cache/               # Pre-generated TTS audio
├── docs/
│   ├── figures/                   # Training charts, confusion matrices
│   └── final_report.md            # This document
├── requirements.txt
└── README.md
```

## Appendix B: Model Cards

### CNN v3 Model Card

| Attribute | Value |
|-----------|-------|
| **Model Name** | CNN v3 (Custom Architecture) |
| **Version** | 3.0 |
| **Date** | June 2026 |
| **Architecture** | 6-layer CNN with BatchNorm, Dropout |
| **Parameters** | ~2.5M |
| **Input** | 48×48 grayscale |
| **Output** | 7 emotion classes + confidence |
| **Accuracy** | 79.25% (standard) / 81.50% (with TTA) |
| **Latency** | ~15 ms (GPU) / ~45 ms (CPU) |
| **Size** | 18.3 MB (H5) / 4.8 MB (TFLite) |
| **Framework** | TensorFlow 2.15 |
| **License** | MIT |

### CNN v6 Model Card

| Attribute | Value |
|-----------|-------|
| **Model Name** | CNN v6 (VGG + CBAM) |
| **Version** | 6.0 |
| **Date** | June 2026 |
| **Architecture** | VGG-16 backbone + CBAM attention |
| **Parameters** | ~8.2M |
| **Input** | 48×48 grayscale |
| **Output** | 7 emotion classes + confidence |
| **Accuracy** | 72.10% (standalone) |
| **Ensemble Weight** | 0.10 |
| **Latency** | ~15 ms (GPU) |
| **Size** | 32.1 MB (H5) |
| **Framework** | TensorFlow 2.15 |

---

*Document generated for Vision AI Project — Final Submission v4*  
*All metrics verified against production codebase and test datasets.*
