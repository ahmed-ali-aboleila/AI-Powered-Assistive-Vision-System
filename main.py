"""
main.py - Assistive Vision System
===================================
Integrates:
  - Face Recognition (Ismail)  → identifies known/unknown/blocked persons
  - Emotion Detection  (Ahmed) → reads emotions of recognized persons
  - Logic Controller           → decides what to say and when
  - Shared TTS                 → single voice output

Usage:
  python main.py

Press Q or ESC to quit.
"""

import cv2
import sys
import os
import time
import threading
import csv
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

# ── Load emotion model BEFORE DeepFace (critical for keras compatibility) ─────
os.environ['TF_USE_LEGACY_KERAS'] = '0'
import tensorflow as _tf
_emotion_model_global = None
if os.path.exists(config.MODEL_PATH):
    _emotion_model_global = _tf.keras.models.load_model(
        config.MODEL_PATH, compile=False
    )
    print('[Model] Loaded successfully before DeepFace')
else:
    print(f'ERROR: Model not found at {config.MODEL_PATH}')
    import sys; sys.exit(1)

# ── Shared TTS (must be created first — used by all modules) ──────────────────
from shared.tts import TTS
tts = TTS(rate=config.TTS_RATE)

# ── Face Recognition modules ──────────────────────────────────────────────────
from face.face_db        import FaceDB
from face.face_processor import FaceProcessor
from face.registration   import RegFlow
from shared.stt          import STT

# ── Emotion Detection modules ─────────────────────────────────────────────────
from emotion.face_detector  import FaceEmotionDetector
from emotion.audio_detector import AudioEmotionDetector
from emotion.display        import draw_results, draw_no_face, draw_fps

# ── Logic Controller ──────────────────────────────────────────────────────────
from logic_controller import LogicController


# ─────────────────────────────────────────────────────────────────────────────
#  Main Application
# ─────────────────────────────────────────────────────────────────────────────

class AssistiveVisionSystem:
    """
    Unified system combining Face Recognition + Emotion Detection.

    Pipeline per frame:
      1. Face Recognition  → who is this person?
      2. Logic Controller  → should we read emotions?
      3. Emotion Detection → what emotion is this person showing?
      4. TTS               → announce result
      5. Display           → draw on screen
    """

    def __init__(self):
        print("=" * 55)
        print("  Assistive Vision System — Starting Up")
        print("=" * 55)

        # ── Load emotion model ─────────────────────────────────────────────
        print("\n[1/5] Loading emotion model...")
        self._emotion_model = _emotion_model_global
        print(f"      Model loaded from: {config.MODEL_PATH}")

        # ── Face Recognition ───────────────────────────────────────────────
        print("\n[2/5] Initializing Face Recognition...")
        self._face_db   = FaceDB(path=config.FACE_DB_PATH)
        self._face_proc = FaceProcessor(threshold=config.FACE_THRESHOLD)
        self._stt       = STT()
        self._reg       = RegFlow(tts, self._stt, self._face_db, self._face_proc)
        print("      Face Recognition ready.")

        # ── Emotion Detection ──────────────────────────────────────────────
        print("\n[3/5] Initializing Emotion Detection...")
        self._emo_det   = FaceEmotionDetector(self._emotion_model)
        self._audio_det = AudioEmotionDetector()
        print("      Emotion Detection ready.")

        # ── Logic Controller ───────────────────────────────────────────────
        print("\n[4/5] Starting Logic Controller...")
        self._logic = LogicController(
            tts           = tts,
            stt           = self._stt,
            reg_flow      = self._reg,
            face_processor= self._face_proc,
            face_db       = self._face_db,
        )
        print("      Logic Controller ready.")

        # ── State ──────────────────────────────────────────────────────────
        self._frame_count        = 0
        self._fps                = 0.0
        self._fps_time           = time.time()
        self._fps_frames         = 0

        self._current_emotion    = "Neutral"
        self._current_conf       = 0.0
        self._current_source     = "face"
        self._current_face_box   = None
        self._current_name       = "Unknown"
        self._last_tts_time      = 0.0

        # ── Inference thread state ─────────────────────────────────────────
        self._inference_lock     = threading.Lock()
        self._inference_result   = None   # (name, score, emotion, conf, box)
        self._inference_busy     = False

        # ── Logger ────────────────────────────────────────────────────────
        self._log_file   = None
        self._log_writer = None
        self._init_logger()

        print("\n[5/5] Calibrating microphone...")
        self._stt.calibrate(duration=2.0)

        print("\n" + "=" * 55)
        print("  System Ready!")
        print("  Press Q or ESC to quit.")
        print("  Voice commands: yes / no / block / unblock /")
        print("                  quiet / speak / stop / list / delete")
        print("=" * 55 + "\n")

    # ── Logger ────────────────────────────────────────────────────────────────

    def _init_logger(self):
        if not config.LOG_ENABLED:
            return
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        path     = os.path.join(config.LOG_DIR, f"session_{ts}.csv")
        self._log_file   = open(path, "w", newline="")
        self._log_writer = csv.writer(self._log_file)
        self._log_writer.writerow(
            ["timestamp", "name", "emotion", "emo_conf", "source", "brightness", "action"]
        )
        print(f"      Logging to: {path}")

    def _log(self, name, emotion, emo_conf, source, brightness, action):
        if self._log_writer:
            self._log_writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                name, emotion, f"{emo_conf:.2f}",
                source, f"{brightness:.0f}", action,
            ])

    # ── FPS ───────────────────────────────────────────────────────────────────

    def _update_fps(self):
        self._fps_frames += 1
        now = time.time()
        if now - self._fps_time >= 1.0:
            self._fps        = self._fps_frames / (now - self._fps_time)
            self._fps_frames = 0
            self._fps_time   = now

    # ── Brightness ────────────────────────────────────────────────────────────

    @staticmethod
    def _brightness(frame_gray) -> float:
        return float(cv2.mean(frame_gray)[0])

    @staticmethod
    def _confidence_threshold(brightness: float) -> float:
        if brightness < config.BRIGHTNESS_THRESHOLD:
            return config.CONFIDENCE_MIN_LOW
        return config.CONFIDENCE_MIN

    # ── Inference (runs in background thread) ─────────────────────────────────

    def _run_inference(self, frame, frame_gray):
        """
        Runs face recognition + emotion detection in a background thread.
        Results are stored in self._inference_result.
        """
        if self._inference_busy:
            return
        self._inference_busy = True

        def _infer():
            try:
                result = self._infer_frame(frame.copy(), frame_gray.copy())
                with self._inference_lock:
                    self._inference_result = result
            except Exception as e:
                pass
            finally:
                self._inference_busy = False

        threading.Thread(target=_infer, daemon=True).start()

    def _infer_frame(self, frame, frame_gray):
        """
        Full inference pipeline supporting multiple faces.
        1. Detect ALL faces
        2. For each face: liveness + recognition + emotion
        3. Sort by box area (closest first)
        Returns list of (face_id, name, rec_score, emotion, emo_conf, box, box_area)
        """
        faces = self._face_proc.detect(frame)
        db    = self._face_db.all()
        results = []

        for box in faces:
            x, y, w, h = box
            area = w * h

            # Liveness check
            live, _ = self._face_proc.is_live(frame, box)
            if not live:
                continue

            # Face Recognition
            name, rec_score = "Unknown", 0.0
            emb = self._face_proc.embed(frame, box)
            if emb is not None:
                if self._face_proc.identify_blocked(emb, db):
                    block_label = next(
                        (b for b in db if b.startswith("__blocked__")),
                        "__blocked__unknown"
                    )
                    results.append((
                        self._face_proc._grid_key(box),
                        block_label, 1.0, "N/A", 0.0, box, area
                    ))
                    continue
                name, rec_score = self._face_proc.identify(emb, db, box)

            # Emotion Detection for this face
            face_gray = frame_gray[max(0,y):y+h, max(0,x):x+w]
            if face_gray.size > 0:
                import cv2 as _cv2
                import numpy as _np
                face_resized    = _cv2.resize(face_gray, config.IMG_SIZE)
                face_normalized = face_resized.astype("float32") / 255.0
                face_input      = _np.expand_dims(face_normalized, axis=(0, -1))
                preds      = self._emotion_model.predict(face_input, verbose=0)[0]
                idx        = int(_np.argmax(preds))
                emo_conf   = float(preds[idx])
                emotion    = config.EMOTIONS_EN[idx]
            else:
                emotion, emo_conf = "Neutral", 0.0

            results.append((
                self._face_proc._grid_key(box),
                name, rec_score, emotion, emo_conf, box, area
            ))

        # Sort by area descending (closest first)
        results.sort(key=lambda r: r[6], reverse=True)
        return results

    # ── Audio Fallback ────────────────────────────────────────────────────────

    def _on_audio_result(self, emotion, confidence):
        self._current_emotion = emotion
        self._current_conf    = confidence
        self._current_source  = "audio"
        print(f"[MIC] {emotion} ({confidence*100:.0f}%)")

    # ── Main Loop ─────────────────────────────────────────────────────────────

    def run(self):
        cap = cv2.VideoCapture(config.CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS,          config.TARGET_FPS)

        if not cap.isOpened():
            print("ERROR: Cannot open camera. Check CAMERA_INDEX in config.py")
            return

        print("Camera running...\n")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("ERROR: Failed to read frame.")
                    break

                self._update_fps()
                self._frame_count += 1
                frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brightness = self._brightness(frame_gray)
                threshold  = self._confidence_threshold(brightness)

                # Feed frame to registration if active
                if self._reg.active:
                    self._reg.feed(frame)

                # Check registration result
                reg_result = self._reg.result()
                if reg_result and reg_result != "PENDING":
                    if isinstance(reg_result, str) and reg_result.startswith("registered:"):
                        name = reg_result.replace("registered:", "")
                        self._logic.on_registered(name)

                # ── Run inference every N frames ──────────────────────────
                if self._frame_count % config.INFERENCE_EVERY_N == 0:
                    self._run_inference(frame, frame_gray)

                # ── Apply inference result ────────────────────────────────
                with self._inference_lock:
                    result = self._inference_result
                    self._inference_result = None

                if result is not None:
                    # result is now a list of faces sorted by size (closest first)
                    faces_data = []

                    for face_id, name, rec_score, emotion, emo_conf, face_box, area in result:
                        # Audio fallback for low confidence
                        if not name.startswith("__blocked__") and name != "Screen":
                            if emo_conf < threshold:
                                self._audio_det.analyze_async(self._on_audio_result)
                                emotion  = self._current_emotion
                                emo_conf = self._current_conf

                        faces_data.append((face_id, name, rec_score,
                                           emotion, emo_conf, area))

                    # Update display state from closest face
                    if result:
                        _, name, _, emotion, emo_conf, face_box, _ = result[0]
                        self._current_name     = name
                        self._current_face_box = face_box
                        self._current_emotion  = emotion
                        self._current_conf     = emo_conf
                        self._current_source   = "face"

                    # Send all faces to Logic Controller
                    self._logic.process_faces(
                        faces_data = faces_data,
                        brightness = brightness,
                        frame      = frame,
                    )

                    # Log closest face
                    if result:
                        self._log(self._current_name, self._current_emotion,
                                  self._current_conf, self._current_source,
                                  brightness, "multi_face")

                # ── Draw ─────────────────────────────────────────────────
                if config.SHOW_WINDOW:
                    if self._current_face_box is not None:
                        display_label = self._current_name
                        if self._current_emotion != "N/A":
                            display_label += f" | {self._current_emotion}"
                        frame = draw_results(
                            frame,
                            self._current_emotion,
                            self._current_conf,
                            self._current_face_box,
                            self._current_source,
                        )
                        # Draw name above face box
                        x, y, w, h = self._current_face_box
                        cv2.putText(frame, self._current_name,
                                    (x, y - 35),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                    (255, 255, 0), 2)
                    else:
                        frame = draw_no_face(frame)

                    frame = draw_fps(frame, self._fps)
                    cv2.imshow(config.WINDOW_TITLE, frame)

                # ── Key Handler ───────────────────────────────────────────
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:
                    print("Exiting...")
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()
            if self._log_file:
                self._log_file.close()
            print("System closed.")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    system = AssistiveVisionSystem()
    system.run()
