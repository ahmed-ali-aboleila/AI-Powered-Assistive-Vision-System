"""
src/face_detector.py - Face emotion detection using MTCNN
"""
import cv2
import numpy as np
from collections import Counter

import config
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from mtcnn import MTCNN
    _MTCNN_AVAILABLE = True
except ImportError:
    _MTCNN_AVAILABLE = False

class FaceEmotionDetector:
    """
    Detects faces and predicts emotions using:
    - MTCNN for face detection (more accurate than Haar Cascade)
    - CNN model trained on FER2013
    """

    def __init__(self, model):
        self.model   = model
        self._history: list = []

        # Initialize face detector
        if _MTCNN_AVAILABLE:
            self._detector = MTCNN()
            self._use_mtcnn = True
            print("Face detector: MTCNN")
        else:
            # Fallback to Haar Cascade if MTCNN not available
            self._detector = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            self._use_mtcnn = False
            print("Face detector: Haar Cascade (fallback)")

    def detect(self, frame_gray, frame_color):
        """
        Analyze a frame and return:
          (emotion, confidence, face_box)
          or None if no face detected
        """
        if self._use_mtcnn:
            return self._detect_mtcnn(frame_gray, frame_color)
        else:
            return self._detect_haar(frame_gray)

    def _detect_mtcnn(self, frame_gray, frame_color):
        """Detect face using MTCNN on color frame"""
        try:
            results = self._detector.detect_faces(frame_color)
        except Exception as e:
            return None

        if not results:
            return None

        # Pick the largest face (highest confidence)
        best = max(results, key=lambda r: r['confidence'])

        # Skip low confidence detections
        if best['confidence'] < 0.90:
            return None

        x, y, w, h = best['box']

        # Fix negative coordinates (MTCNN can return negative values)
        x = max(0, x)
        y = max(0, y)

        # Extract face from grayscale for model
        face_roi = frame_gray[y:y+h, x:x+w]
        if face_roi.size == 0:
            return None

        # Preprocess for model
        face_resized    = cv2.resize(face_roi, config.IMG_SIZE)
        face_normalized = face_resized.astype("float32") / 255.0
        face_input      = np.expand_dims(face_normalized, axis=(0, -1))  # (1, 48, 48, 1)

        # Predict
        preds      = self.model.predict(face_input, verbose=0)[0]
        idx        = int(np.argmax(preds))
        confidence = float(preds[idx])
        emotion    = config.EMOTIONS_EN[idx]

        # Smoothing
        self._history.append(idx)
        if len(self._history) > config.SMOOTHING_WINDOW:
            self._history.pop(0)

        counts = Counter(self._history)
        top_idx, top_count = counts.most_common(1)[0]
        ratio = top_count / len(self._history)

        if ratio >= config.MIN_STABLE_RATIO:
            stable_emotion = config.EMOTIONS_EN[top_idx]
        else:
            stable_emotion = emotion

        return stable_emotion, confidence, (x, y, w, h)

    def _detect_haar(self, frame_gray):
        """Fallback: Detect face using Haar Cascade"""
        faces = self._detector.detectMultiScale(
            frame_gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(48, 48),
        )

        if len(faces) == 0:
            return None

        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])

        face_roi        = frame_gray[y:y+h, x:x+w]
        face_resized    = cv2.resize(face_roi, config.IMG_SIZE)
        face_normalized = face_resized.astype("float32") / 255.0
        face_input      = np.expand_dims(face_normalized, axis=(0, -1))

        preds      = self.model.predict(face_input, verbose=0)[0]
        idx        = int(np.argmax(preds))
        confidence = float(preds[idx])
        emotion    = config.EMOTIONS_EN[idx]

        self._history.append(idx)
        if len(self._history) > config.SMOOTHING_WINDOW:
            self._history.pop(0)

        counts = Counter(self._history)
        top_idx, top_count = counts.most_common(1)[0]
        ratio = top_count / len(self._history)

        if ratio >= config.MIN_STABLE_RATIO:
            stable_emotion = config.EMOTIONS_EN[top_idx]
        else:
            stable_emotion = emotion

        return stable_emotion, confidence, (x, y, w, h)

    def reset_history(self):
        self._history.clear()
