import importlib.util
import os
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config


CHECKS = [
    ("OpenCV", "cv2"),
    ("NumPy", "numpy"),
    ("SpeechRecognition", "speech_recognition"),
    ("PyAudio", "pyaudio"),
    ("Vosk", "vosk"),
    ("Pygame", "pygame"),
    ("DeepFace", "deepface"),
]


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def main():
    print("Assistive Vision Raspberry Pi preflight")
    print(f"Platform: {platform.platform()}")
    print(f"Machine: {platform.machine()}")
    print(f"RPI_MODE: {config.RPI_MODE}")

    ok = True
    for label, module in CHECKS:
        found = has_module(module)
        ok = ok and found
        print(f"{label:20} {'OK' if found else 'MISSING'}")

    tflite_ok = has_module("ai_edge_litert") or has_module("tflite_runtime")
    print(f"{'TFLite runtime':20} {'OK' if tflite_ok else 'MISSING'}")
    if config.USE_TFLITE_EMOTION and not tflite_ok:
        ok = False

    paths = [
        ("Keras emotion model", config.MODEL_PATH),
        ("TFLite emotion model", config.TFLITE_MODEL_PATH),
        ("English Vosk model", "models/vosk-model"),
    ]
    for label, path in paths:
        exists = Path(path).exists()
        print(f"{label:20} {'OK' if exists else 'MISSING'} ({path})")

    if not Path(config.MODEL_PATH).exists() and not Path(config.TFLITE_MODEL_PATH).exists():
        ok = False

    if not Path("models/vosk-model").exists():
        print("Warning: offline English commands will be limited without models/vosk-model.")

    ar_vosk_paths = [
        Path("models/vosk-model-ar"),
        Path("models/vosk-model-ar-mgb2-0.4"),
    ]
    ar_vosk_ok = any(path.exists() for path in ar_vosk_paths)
    print(f"{'Arabic Vosk model':20} {'OK' if ar_vosk_ok else 'MISSING'}")
    if not ar_vosk_ok:
        print("Warning: offline Arabic commands will be limited without an Arabic Vosk model.")

    print("READY" if ok else "NOT READY")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
