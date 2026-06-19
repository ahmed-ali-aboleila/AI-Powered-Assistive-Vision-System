"""
main.py - Assistive Vision System
===================================
Integrates:
  - Face Recognition  → identifies known/unknown/blocked persons
  - Emotion Detection → reads emotions using CNN + TTA
  - Logic Controller  → decides what to say and when
  - Shared TTS        → single voice output (Edge TTS neural)

Optimizations applied:
  [1] imports moved outside loops
  [2] TTA only when confidence < TTA_CONFIDENCE_THRESHOLD
  [3] Batch prediction for multiple faces
  [4] Per-face emotion smoothing (history window)
  [5] Adaptive inference rate (stable vs changing)
  [6] Audio fallback only for closest face
  [7] TTS cache for repeated phrases
  [8] Log flush after every write
  [9] Adaptive face threshold in low light
  [10] Fixed unused display_label variable

Press Q or ESC to quit.
"""

import sys
import os
import time
import threading
import csv
import numpy as np
from datetime import datetime
from collections import deque, Counter

if os.environ.get("VISION_RPI_MODE", "").strip().lower() in {"1", "true", "yes", "on"}:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2

# ── Fix: UTF-8 output on Windows to prevent UnicodeEncodeError ────────────────
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from shared.model_runtime import TFLiteEmotionModel

if getattr(config, "RPI_MODE", False):
    cv2.setNumThreads(int(os.environ.get("VISION_OPENCV_THREADS", "2")))

# ── Load emotion model BEFORE DeepFace (critical for keras compatibility) ─────
os.environ['TF_USE_LEGACY_KERAS'] = '0'
_emotion_model_global = None
if getattr(config, "USE_TFLITE_EMOTION", False) and os.path.exists(config.TFLITE_MODEL_PATH):
    try:
        _emotion_model_global = TFLiteEmotionModel(config.TFLITE_MODEL_PATH)
        print(f"[Model] Loaded TFLite emotion model: {config.TFLITE_MODEL_PATH}")
    except Exception as e:
        print(f"[Model] TFLite load failed: {e}")
        print("[Model] Falling back to Keras emotion model.")

if _emotion_model_global is None and os.path.exists(config.MODEL_PATH):
    import tensorflow as _tf
    _emotion_model_global = _tf.keras.models.load_model(
        config.MODEL_PATH, compile=False
    )
    print("[Model] Loaded Keras emotion model before DeepFace")

if _emotion_model_global is None:
    print(f"ERROR: Model not found at {config.MODEL_PATH} or {config.TFLITE_MODEL_PATH}")
    sys.exit(1)

# ── Shared TTS ────────────────────────────────────────────────────────────────
from shared.tts import TTS
tts = TTS(rate=config.TTS_RATE)

# ── Face Recognition ──────────────────────────────────────────────────────────
from face.face_db        import FaceDB
from face.face_processor import FaceProcessor
from face.registration   import RegFlow
from shared.stt          import STT
from shared.draw_utils   import draw_text_unicode

# ── Emotion Detection ─────────────────────────────────────────────────────────
from emotion.audio_detector import AudioEmotionDetector
from emotion.display        import draw_results, draw_no_face, draw_fps

# ── Logic Controller ──────────────────────────────────────────────────────────
from logic_controller import LogicController

import logging
logger = logging.getLogger(__name__)




# ─────────────────────────────────────────────────────────────────────────────
#  Main Application
# ─────────────────────────────────────────────────────────────────────────────

class AssistiveVisionSystem:

    def __init__(self):
        print("=" * 55)
        print("  Assistive Vision System — Starting Up")
        print("=" * 55)

        # ── Emotion model ──────────────────────────────────────────────────
        print("\n[1/5] Loading emotion model...")
        self._emotion_model = _emotion_model_global
        print(f"      Model: {config.MODEL_PATH}")

        # ── Face Recognition ───────────────────────────────────────────────
        print("\n[2/5] Initializing Face Recognition...")
        self._face_db   = FaceDB(path=config.FACE_DB_PATH)
        self._face_proc = FaceProcessor(threshold=config.FACE_THRESHOLD)
        self._stt       = STT()
        self._reg       = RegFlow(tts, self._stt, self._face_db, self._face_proc)
        print("      Face Recognition ready.")

        # ── Emotion Detection ──────────────────────────────────────────────
        print("\n[3/5] Initializing Emotion Detection...")
        self._audio_det = AudioEmotionDetector()
        print("      Emotion Detection ready.")

        # ── Logic Controller ───────────────────────────────────────────────
        print("\n[4/5] Starting Logic Controller...")
        self._logic = LogicController(
            tts            = tts,
            stt            = self._stt,
            reg_flow       = self._reg,
            face_processor = self._face_proc,
            face_db        = self._face_db,
        )


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

        # ── Inference thread ───────────────────────────────────────────────
        self._inference_lock   = threading.Lock()
        self._inference_result = None
        self._inference_busy   = False
        self._recognition_cycle = 0
        self._recognition_cache = {}

        # ── Per-face emotion smoothing ─────────────────────────────────────
        # {face_id: deque of emotion indices}
        _hist_size = getattr(config, 'EMOTION_HISTORY_SIZE', 8)
        self._emotion_history: dict = {}
        self._emotion_history_size  = _hist_size

        # ── Adaptive inference rate ────────────────────────────────────────
        self._stable_frames     = 0   # consecutive frames with same emotion
        self._last_emotion_set  = ""  # for stability tracking
        self._stable_n  = getattr(config, 'INFERENCE_STABLE_N',  15)
        self._active_n  = getattr(config, 'INFERENCE_ACTIVE_N',   8)
        self._stable_threshold = getattr(config, 'EMOTION_STABLE_FRAMES', 20)

        # ── Logger ────────────────────────────────────────────────────────
        self._log_file   = None
        self._log_writer = None
        self._init_logger()

        print("\n[5/5] Calibrating microphone...")
        self._stt.calibrate(duration=2.0)

        print("\n" + "=" * 55)
        print("  System Ready! Press Q or ESC to quit.")
        print("  Say 'vision' or 'فيجن' to activate voice commands.")
        print("=" * 55 + "\n")

    # ── Logger ────────────────────────────────────────────────────────────────

    def _init_logger(self):
        if not config.LOG_ENABLED:
            return
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(config.LOG_DIR, f"session_{ts}.csv")
        self._log_file   = open(path, "w", newline="", encoding="utf-8")
        self._log_writer = csv.writer(self._log_file)
        self._log_writer.writerow(
            ["timestamp", "name", "emotion", "emo_conf",
             "source", "brightness", "inference_mode"]
        )
        print(f"      Logging to: {path}")

    def _log(self, name, emotion, emo_conf, source, brightness, mode="normal"):
        if self._log_writer:
            self._log_writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                name, emotion, f"{emo_conf:.2f}",
                source, f"{brightness:.0f}", mode,
            ])
            self._log_file.flush()   # [FIX #8] flush immediately — no data loss on crash

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

    def _confidence_threshold(self, brightness: float) -> float:
        if brightness < config.BRIGHTNESS_THRESHOLD:
            return config.CONFIDENCE_MIN_LOW
        return config.CONFIDENCE_MIN

    def _face_threshold(self, brightness: float) -> float:
        """[OPT #9] Adaptive face threshold — more lenient in low light."""
        if brightness < config.BRIGHTNESS_THRESHOLD:
            return getattr(config, 'FACE_THRESHOLD_LOW_LIGHT', 0.55)
        return config.FACE_THRESHOLD

    # ── Adaptive inference interval ───────────────────────────────────────────

    def _get_inference_n(self) -> int:
        """[OPT #5] Use faster inference when emotion is changing."""
        if self._stable_frames >= self._stable_threshold:
            return self._stable_n   # emotion stable → less frequent
        return self._active_n       # emotion changing → more frequent

    # ── Emotion smoothing ─────────────────────────────────────────────────────

    def _smooth_emotion(self, face_id: str, raw_idx: int) -> int:
        """[OPT #4] Per-face emotion history smoothing."""
        if face_id not in self._emotion_history:
            self._emotion_history[face_id] = deque(
                maxlen=self._emotion_history_size
            )
        hist = self._emotion_history[face_id]
        hist.append(raw_idx)

        stable_ratio = getattr(config, 'EMOTION_STABLE_RATIO', 0.55)
        most_common, count = Counter(hist).most_common(1)[0]
        if count / len(hist) >= stable_ratio:
            return most_common
        return raw_idx   # not stable yet — use raw

    def _cleanup_stale_histories(self, active_face_ids: set):
        """Remove emotion history for faces no longer in frame — prevents memory leak."""
        stale = [k for k in self._emotion_history if k not in active_face_ids]
        for k in stale:
            del self._emotion_history[k]

    # ── Predict emotion (single face input) ───────────────────────────────────

    def _predict_emotion(self, face_input: np.ndarray) -> tuple:
        """
        [OPT #2] Conditional TTA:
          - If confidence ≥ TTA_CONFIDENCE_THRESHOLD → single fast predict
          - If confidence <  TTA_CONFIDENCE_THRESHOLD → full 5-pass TTA
        """
        tta_threshold = getattr(config, 'TTA_CONFIDENCE_THRESHOLD', 0.65)

        # Fast single predict first
        preds = self._emotion_model.predict(face_input, verbose=0)[0]

        if float(preds.max()) >= tta_threshold:
            # High confidence — no TTA needed
            return preds, "fast"

        # Low confidence — run full TTA for better accuracy
        tta_preds = [preds]   # already have pass 1

        # Pass 2: horizontal flip
        flipped = face_input[:, :, ::-1, :]
        tta_preds.append(
            self._emotion_model.predict(flipped, verbose=0)[0])

        # Pass 3: brightness +10%
        bright = np.clip(face_input * 1.1, 0.0, 1.0).astype("float32")
        tta_preds.append(
            self._emotion_model.predict(bright, verbose=0)[0])

        # Pass 4: brightness -10%
        dark = np.clip(face_input * 0.9, 0.0, 1.0).astype("float32")
        tta_preds.append(
            self._emotion_model.predict(dark, verbose=0)[0])

        # Pass 5: tiny Gaussian noise
        noisy = np.clip(
            face_input + np.random.normal(0, 0.02, face_input.shape),
            0.0, 1.0
        ).astype("float32")
        tta_preds.append(
            self._emotion_model.predict(noisy, verbose=0)[0])

        return np.mean(tta_preds, axis=0), "tta"

    # ── Inference (background thread) ─────────────────────────────────────────

    def _run_inference(self, frame, frame_gray, brightness):
        if self._inference_busy:
            return
        self._inference_busy = True

        def _infer():
            try:
                result = self._infer_frame(
                    frame.copy(), frame_gray.copy(), brightness
                )
                with self._inference_lock:
                    self._inference_result = result
            except Exception as e:
                logger.error(f"Inference error: {e}", exc_info=True)
            finally:
                self._inference_busy = False

        threading.Thread(target=_infer, daemon=True).start()

    def _infer_frame(self, frame, frame_gray, brightness):
        """
        Full inference pipeline:
          1. Detect all faces (Haar)
          2. Liveness check (LBP)
          3. Face recognition (Facenet512 + cosine)
          4. Batch emotion prediction (CNN + conditional TTA)
          5. Per-face smoothing
          6. Sort by area (closest first)
        """
        faces = self._face_proc.detect(frame)
        if not faces:
            return []

        db          = self._face_db.all()
        face_thresh = self._face_threshold(brightness)
        results     = []
        self._recognition_cycle += 1
        rec_every = max(1, int(getattr(config, "FACE_RECOGNITION_EVERY_N", 1)))
        rec_cache_sec = float(getattr(config, "FACE_RECOGNITION_CACHE_SEC", 1.2))
        now = time.time()

        # ── Per-face: liveness + recognition + crop ────────────────────────
        face_inputs = []   # batch for emotion model
        face_meta   = []   # parallel metadata

        for box in faces:
            x, y, w, h = box
            area = w * h
            face_id = self._face_proc._grid_key(box)

            # Liveness
            live, _ = self._face_proc.is_live(frame, box)
            if not live:
                continue

            # Recognition — use adaptive threshold
            name, rec_score = "Unknown", 0.0
            cached = self._recognition_cache.get(face_id)
            use_cache = (
                cached is not None
                and rec_every > 1
                and self._recognition_cycle % rec_every != 0
                and (now - cached[2]) <= rec_cache_sec
            )
            if use_cache:
                name, rec_score = cached[0], cached[1]
            else:
                emb = self._face_proc.embed(frame, box)
                if emb is not None:
                    # Use local threshold to avoid race condition with main thread
                    local_thresh = face_thresh
                    blocked_match = self._face_proc.identify_blocked(emb, db)
                    if blocked_match:
                        self._recognition_cache[face_id] = (blocked_match, 1.0, now)
                        results.append((
                            face_id,
                            blocked_match, 1.0, "N/A", 0.0, box, area
                        ))
                        continue
                    original_thresh = self._face_proc.threshold
                    self._face_proc.threshold = local_thresh
                    name, rec_score = self._face_proc.identify(emb, db, box)
                    self._face_proc.threshold = original_thresh
                    self._recognition_cache[face_id] = (name, rec_score, now)

            # Crop face for emotion — collect for batch
            face_gray = frame_gray[max(0,y):y+h, max(0,x):x+w]
            if face_gray.size > 0:
                face_resized    = cv2.resize(face_gray, config.IMG_SIZE)
                face_normalized = face_resized.astype("float32") / 255.0
                face_input      = np.expand_dims(face_normalized, axis=(0, -1))
                face_inputs.append(face_input)
            else:
                face_inputs.append(None)

            face_meta.append((face_id, name, rec_score, box, area))

        # ── Batch emotion prediction [OPT #3] ─────────────────────────────
        # Collect all valid face inputs into one batch
        valid_indices = [i for i, fi in enumerate(face_inputs) if fi is not None]
        final_preds = {}   # ← must init here to avoid UnboundLocalError

        if valid_indices:
            # Build batch
            batch = np.concatenate(
                [face_inputs[i] for i in valid_indices], axis=0
            )  # (N, 48, 48, 1)

            # Fast single-pass predict for all faces
            batch_preds = self._emotion_model.predict(batch, verbose=0)

            # Check which faces need TTA (low confidence)
            tta_threshold = getattr(config, 'TTA_CONFIDENCE_THRESHOLD', 0.65)

            for local_i, orig_i in enumerate(valid_indices):
                preds = batch_preds[local_i]
                if float(preds.max()) < tta_threshold:
                    # Run TTA for this specific face only
                    tta_result, _ = self._predict_emotion(face_inputs[orig_i])
                    final_preds[orig_i] = tta_result
                else:
                    final_preds[orig_i] = preds

        # ── Assemble results ───────────────────────────────────────────────
        for i, (face_id, name, rec_score, box, area) in enumerate(face_meta):
            if i in final_preds:
                preds    = final_preds[i]
                raw_idx  = int(np.argmax(preds))
                # Minimal smoothing — only 3 frames, prevents flicker
                # Logic Controller applies its own cooldown for announcements
                smooth_idx = self._smooth_emotion(face_id, raw_idx)
                emo_conf   = float(preds[raw_idx])   # use raw confidence
                emotion    = config.EMOTIONS_EN[smooth_idx]
            else:
                emotion, emo_conf = "Neutral", 0.0

            results.append((face_id, name, rec_score, emotion, emo_conf, box, area))

        # Sort by area descending (closest first)
        results.sort(key=lambda r: r[6], reverse=True)

        # Cleanup stale emotion histories every 500 frames
        if self._frame_count % 500 == 0:
            active_ids = {r[0] for r in results}
            self._cleanup_stale_histories(active_ids)
            stale_cache = [
                key for key, (_name, _score, ts) in self._recognition_cache.items()
                if key not in active_ids or (now - ts) > rec_cache_sec * 3
            ]
            for key in stale_cache:
                self._recognition_cache.pop(key, None)

        return results

    # ── Audio Fallback ────────────────────────────────────────────────────────

    def _on_audio_result(self, emotion, confidence):
        self._current_emotion = emotion
        self._current_conf    = confidence
        self._current_source  = "audio"
        print(f"[MIC] {emotion} ({confidence*100:.0f}%)")

    # ── Main Loop ─────────────────────────────────────────────────────────────

    def _open_camera(self):
        cap = cv2.VideoCapture(config.CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS,          config.TARGET_FPS)
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass
        return cap

    def run(self):
        cap = self._open_camera()

        if not cap.isOpened():
            print("ERROR: Cannot open camera. Check CAMERA_INDEX in config.py")
            return

        print("Camera running...\n")
        read_failures = 0
        read_fail_limit = max(1, int(getattr(config, "CAMERA_READ_FAIL_LIMIT", 8)))

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    read_failures += 1
                    print(f"WARNING: Failed to read frame ({read_failures}/{read_fail_limit}).")
                    time.sleep(0.2)
                    if read_failures < read_fail_limit:
                        continue

                    print("WARNING: Reopening camera...")
                    cap.release()
                    time.sleep(1.0)
                    cap = self._open_camera()
                    if not cap.isOpened():
                        print("ERROR: Cannot reopen camera. Check cable, power, and CAMERA_INDEX.")
                        break
                    read_failures = 0
                    continue
                read_failures = 0

                self._update_fps()
                self._frame_count += 1
                frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brightness = self._brightness(frame_gray)
                threshold  = self._confidence_threshold(brightness)

                # Feed to registration
                if self._reg.active:
                    self._reg.feed(frame)

                # Check registration result
                reg_result = self._reg.result()
                if reg_result and reg_result != "PENDING":
                    if isinstance(reg_result, str):
                        if reg_result.startswith("registered:"):
                            name = reg_result.replace("registered:", "")
                            self._logic.on_registered(name)
                        elif reg_result.startswith("improved:"):
                            name = reg_result.replace("improved:", "")
                            self._logic.on_registered(name)
                            self._face_proc.reset()
                        elif reg_result.startswith("deleted:"):
                            name = reg_result.replace("deleted:", "")
                            if name == "__all__":
                                if hasattr(self._logic, "on_all_deleted"):
                                    self._logic.on_all_deleted()
                            else:
                                self._logic.on_deleted(name)
                            self._face_proc.reset()   # امسح vote buffer فوراً
                        elif reg_result.startswith("blocked:"):
                            name = reg_result.replace("blocked:", "")
                            self._face_proc.reset()   # امسح vote buffer
                        elif reg_result.startswith("unblocked:"):
                            self._face_proc.reset()

                # ── [OPT #5] Adaptive inference rate ─────────────────────
                inference_n = self._get_inference_n()
                if self._frame_count % inference_n == 0:
                    self._run_inference(frame, frame_gray, brightness)

                # ── Apply inference result ────────────────────────────────
                with self._inference_lock:
                    result = self._inference_result
                    self._inference_result = None

                if result is not None:
                    faces_data = []

                    # [OPT #6] Audio fallback only for closest face (prevents conflicts when STT is listening)
                    closest_needs_audio = (
                        result and
                        not result[0][1].startswith("__blocked__") and
                        result[0][4] < threshold and
                        not self._stt.is_listening
                    )
                    if closest_needs_audio:
                        self._audio_det.analyze_async(self._on_audio_result)

                    for face_id, name, rec_score, emotion, emo_conf, face_box, area \
                            in result:
                        # Apply audio fallback result to close face if needed
                        if closest_needs_audio and \
                           face_id == result[0][0] and \
                           not name.startswith("__blocked__"):
                            emotion  = self._current_emotion
                            emo_conf = self._current_conf

                        faces_data.append(
                            (face_id, name, rec_score, emotion, emo_conf, area)
                        )

                    # Update display state + stability tracking
                    if result:
                        _, name, _, emotion, emo_conf, face_box, _ = result[0]
                        self._current_name     = name
                        self._current_face_box = face_box
                        self._current_emotion  = emotion
                        self._current_conf     = emo_conf
                        self._current_source   = "face"

                        # Track stability for adaptive inference
                        if emotion == self._last_emotion_set:
                            self._stable_frames += 1
                        else:
                            self._stable_frames    = 0
                            self._last_emotion_set = emotion
                    else:
                        self._current_face_box = None
                        self._current_name     = "Unknown"

                    # Send to Logic Controller
                    self._logic.process_faces(
                        faces_data = faces_data,
                        brightness = brightness,
                        frame      = frame,
                    )

                    # Log
                    if result:
                        mode = "stable" if self._stable_frames >= \
                               self._stable_threshold else "active"
                        self._log(
                            self._current_name, self._current_emotion,
                            self._current_conf, self._current_source,
                            brightness, mode
                        )

                # ── Draw ─────────────────────────────────────────────────
                if config.SHOW_WINDOW:
                    # Draw visual subtitle guidance during active flows (e.g. registration, delete)
                    if self._reg.active:
                        inst = getattr(self._reg, "current_instruction", "")
                        if inst:
                            h_f, w_f = frame.shape[:2]
                            banner_h = 50
                            overlay = frame.copy()
                            cv2.rectangle(overlay, (0, 0), (w_f, banner_h), (20, 20, 20), -1)
                            cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
                            frame = draw_text_unicode(frame, inst, (20, 12), 18, (0, 255, 255))

                    if self._current_face_box is not None:
                        # [FIX #10] Use name + emotion properly
                        frame = draw_results(
                            frame,
                            self._current_emotion,
                            self._current_conf,
                            self._current_face_box,
                            self._current_source,
                        )
                        x, y, w, h = self._current_face_box
                        label = self._current_name
                        if self._current_emotion not in ("N/A", ""):
                            label += f" | {self._current_emotion}"
                        frame = draw_text_unicode(
                            frame, label, (x, y - 10),
                            20, (255, 255, 0)
                        )
                    else:
                        frame = draw_no_face(frame)

                    frame = draw_fps(frame, self._fps)
                    cv2.imshow(config.WINDOW_TITLE, frame)

                # ── Key Handler ───────────────────────────────────────────
                if config.SHOW_WINDOW:
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or key == 27:
                        print("Exiting...")
                        break

        finally:
            cap.release()
            if config.SHOW_WINDOW:
                cv2.destroyAllWindows()
            if self._log_file:
                self._log_file.close()
            print("System closed.")


if __name__ == "__main__":
    system = AssistiveVisionSystem()
    system.run()
