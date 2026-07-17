import importlib.util
import json
import os
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("VISION_RPI_MODE", "1")

import config


def ok(label, detail=""):
    print(f"[OK]   {label}{': ' + detail if detail else ''}")


def warn(label, detail=""):
    print(f"[WARN] {label}{': ' + detail if detail else ''}")


def fail(label, detail=""):
    print(f"[FAIL] {label}{': ' + detail if detail else ''}")


def has_module(name):
    return importlib.util.find_spec(name) is not None


def check_imports():
    print("\n== Imports ==")
    required = {
        "cv2": "OpenCV",
        "numpy": "NumPy",
        "speech_recognition": "SpeechRecognition",
        "pyaudio": "PyAudio",
        "vosk": "Vosk",
        "pygame": "Pygame",
        "deepface": "DeepFace",
    }
    success = True
    for module, label in required.items():
        if has_module(module):
            ok(label)
        else:
            fail(label, module)
            success = False
    if has_module("ai_edge_litert") or has_module("tflite_runtime") or has_module("tensorflow"):
        ok("TFLite runtime")
    else:
        fail("TFLite runtime")
        success = False
    return success


def check_models():
    print("\n== Models ==")
    success = True
    paths = [
        ("TFLite emotion", config.TFLITE_MODEL_PATH),
        ("Keras emotion fallback", config.MODEL_PATH),
        ("English Vosk", "models/vosk-model"),
        ("Arabic Vosk", "models/vosk-model-ar-mgb2-0.4"),
        ("Arabic Vosk words", "models/vosk-model-ar-mgb2-0.4/graph/words.txt"),
    ]
    for label, raw_path in paths:
        path = ROOT / raw_path
        if path.exists():
            size = path.stat().st_size if path.is_file() else 0
            ok(label, f"{raw_path}" + (f" ({size} bytes)" if size else ""))
        else:
            fail(label, raw_path)
            success = False
    return success


def check_camera():
    print("\n== Camera ==")
    if os.environ.get("VISION_SKIP_CAMERA_TEST", "0").strip().lower() in {"1", "true", "yes", "on"}:
        warn("Camera test skipped", "VISION_SKIP_CAMERA_TEST=1")
        return True

    try:
        import cv2
    except Exception as e:
        fail("OpenCV import for camera", repr(e))
        return False

    success = False
    tested_indices = []
    for index in [config.CAMERA_INDEX, 0, 1, 2]:
        if index in tested_indices:
            continue
        tested_indices.append(index)
        cap = cv2.VideoCapture(int(index))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(config.FRAME_WIDTH))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(config.FRAME_HEIGHT))
        cap.set(cv2.CAP_PROP_FPS, int(config.TARGET_FPS))
        opened = cap.isOpened()
        frames = 0
        start = time.time()
        shape = None
        if opened:
            deadline = time.time() + 3.0
            while time.time() < deadline:
                ret, frame = cap.read()
                if ret and frame is not None:
                    frames += 1
                    shape = frame.shape
        cap.release()
        elapsed = max(0.001, time.time() - start)
        fps = frames / elapsed
        if opened and frames > 0:
            ok(f"Camera index {index}", f"{frames} frames, {fps:.1f} FPS, shape={shape}")
            success = True
            break
        else:
            warn(f"Camera index {index}", f"opened={opened}, frames={frames}")
    return success


def check_microphones():
    print("\n== Microphones ==")
    try:
        import pyaudio
    except Exception as e:
        fail("PyAudio import", repr(e))
        return False

    try:
        pa = pyaudio.PyAudio()
        found_input = False
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            channels = int(info.get("maxInputChannels", 0))
            name = str(info.get("name", ""))
            if channels > 0:
                found_input = True
                ok(f"Input mic #{i}", f"{name}, channels={channels}")
        pa.terminate()
        if not found_input:
            fail("Input microphones", "none found")
        return found_input
    except Exception as e:
        fail("Microphone enumeration", repr(e))
        return False


def check_vosk_load():
    print("\n== Vosk Load ==")
    try:
        from vosk import Model, KaldiRecognizer, SetLogLevel
        SetLogLevel(-1)
    except Exception as e:
        fail("Vosk import", repr(e))
        return False

    success = True
    for label, path in [
        ("English Vosk", ROOT / "models/vosk-model"),
        ("Arabic Vosk", ROOT / "models/vosk-model-ar-mgb2-0.4"),
    ]:
        try:
            if not path.exists():
                fail(label, "missing")
                success = False
                continue
            model = Model(str(path))
            KaldiRecognizer(model, 16000)
            ok(label, "model loads")
        except Exception as e:
            fail(label, repr(e))
            success = False
    return success


def check_tflite_emotion():
    print("\n== TFLite Emotion ==")
    try:
        import numpy as np
        from src.utils.model_runtime import TFLiteEmotionModel
        model_path = ROOT / config.TFLITE_MODEL_PATH
        model = TFLiteEmotionModel(str(model_path))
        x = np.zeros((1, 48, 48, 1), dtype="float32")
        start = time.time()
        y = model.predict(x, verbose=0)
        elapsed_ms = (time.time() - start) * 1000
        ok("TFLite emotion inference", f"shape={getattr(y, 'shape', None)}, {elapsed_ms:.1f} ms")
        return True
    except Exception as e:
        fail("TFLite emotion inference", repr(e))
        return False


def check_commands():
    print("\n== Voice Command Parser ==")
    try:
        import unittest
        import test_speech_and_commands
        suite = unittest.defaultTestLoader.loadTestsFromModule(test_speech_and_commands)
        result = unittest.TextTestRunner(verbosity=0).run(suite)
        if result.wasSuccessful():
            ok("Command parser tests", f"{result.testsRun} tests")
            return True
        fail("Command parser tests", f"failures={len(result.failures)}, errors={len(result.errors)}")
        return False
    except Exception as e:
        fail("Command parser tests", repr(e))
        return False


def main():
    print("Assistive Vision Raspberry Pi Deep Test")
    print(f"Platform: {platform.platform()}")
    print(f"Machine: {platform.machine()}")
    print(f"RPI_MODE: {config.RPI_MODE}")
    print(f"Camera: index={config.CAMERA_INDEX}, size={config.FRAME_WIDTH}x{config.FRAME_HEIGHT}, fps={config.TARGET_FPS}")

    checks = [
        check_imports(),
        check_models(),
        check_camera(),
        check_microphones(),
        check_vosk_load(),
        check_tflite_emotion(),
        check_commands(),
    ]

    print("\n== Result ==")
    if all(checks):
        print("DEEP TEST READY")
        raise SystemExit(0)
    print("DEEP TEST NOT READY")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
