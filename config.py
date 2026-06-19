"""
config.py - Unified settings for the integrated system
"""
import os
import platform


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


IS_RASPBERRY_PI = (
    os.environ.get("VISION_RPI", "").strip().lower() in {"1", "true", "yes", "on"}
    or ("arm" in platform.machine().lower() or "aarch" in platform.machine().lower())
)
RPI_MODE = _env_bool("VISION_RPI_MODE", IS_RASPBERRY_PI)

# ══════════════════════════════════════════
#  Language ("en" = English, "ar" = Arabic)
#  User can switch at runtime via voice command
# ══════════════════════════════════════════
LANGUAGE = "en"   # default: English

# ══════════════════════════════════════════
#  Camera
# ══════════════════════════════════════════
CAMERA_INDEX  = 1
FRAME_WIDTH   = 640
FRAME_HEIGHT  = 480
TARGET_FPS    = 15

# ══════════════════════════════════════════
#  Emotion model
# ══════════════════════════════════════════
MODEL_PATH        = "models/cnn_v3_final.h5"
TFLITE_MODEL_PATH = "models/cnn_v3_final.tflite"
USE_TFLITE_EMOTION = _env_bool("VISION_USE_TFLITE", RPI_MODE)
IMG_SIZE          = (48, 48)
INFERENCE_EVERY_N = 10       # increased for TTA (5 passes per inference)

EMOTIONS_EN = {
    0: "Angry",
    1: "Disgust",
    2: "Fear",
    3: "Happy",
    4: "Neutral",
    5: "Sad",
    6: "Surprise",
}

# ══════════════════════════════════════════
#  Dynamic confidence threshold
# ══════════════════════════════════════════
CONFIDENCE_MIN       = 0.45
CONFIDENCE_MIN_LOW   = 0.40  # was 0.35 — less audio fallback
BRIGHTNESS_THRESHOLD = 70    # was 80 — less sensitive to lighting

# ══════════════════════════════════════════
#  Smoothing — faster emotion response
# ══════════════════════════════════════════
SMOOTHING_WINDOW = 12   # كان 8 — نزوده عشان يبقى أثبت
MIN_STABLE_RATIO = 0.60  # كان 0.55 — نزوده عشان يتأكد أكتر

# ══════════════════════════════════════════
#  Audio fallback
# ══════════════════════════════════════════
AUDIO_ENABLED      = True
AUDIO_SAMPLE_RATE  = 16000
AUDIO_RECORD_SEC   = 2.0    # was 2.5 — faster response
AUDIO_DEVICE_INDEX = None

# ══════════════════════════════════════════
#  TTS / STT
# ══════════════════════════════════════════
TTS_COOLDOWN_SEC = 1.5   # نزلنا من 3.0 ل→ 1.5 ثانية — يتيح للتعابير السريعة أن تتعلن بدون تجاهل
EMOTION_CHANGE_COOLDOWN = 0.8  # كولداون خاص لتغيير التعبير السريع — لو التعبير اتغيّر جذرياً
TTS_RATE         = 175   # زدنا السرعة لتقليل وقت نطق كل إعلان

# ══════════════════════════════════════════
#  Display
# ══════════════════════════════════════════
SHOW_WINDOW  = True
WINDOW_TITLE = "Assistive Vision System"

EMOTION_COLORS = {
    "Angry":    (0,   0,   255),
    "Disgust":  (0,   140, 255),
    "Fear":     (128, 0,   128),
    "Happy":    (0,   255, 0  ),
    "Neutral":  (200, 200, 200),
    "Sad":      (255, 100, 0  ),
    "Surprise": (0,   255, 255),
}

# ══════════════════════════════════════════
#  Face Recognition
# ══════════════════════════════════════════
FACE_DB_PATH   = "face_data.pkl"
BLOCKED_PATH   = "blocked.json"
FACE_THRESHOLD = 0.53   # رفعنا لـ 0.53 ليكون أكثر تسامحاً مع زوايا الرأس وتغير التعابير
LBP_THRESHOLD  = 18.0

# ══════════════════════════════════════════
#  Logic Controller
# ══════════════════════════════════════════
UNKNOWN_REASK_TIMEOUT      = 20.0   # رفعنا من 10 ل→ 20 ثانية — الشخص لازم يغيب 20 ثانية قبل ما يتعامل معاه كذا جديد
UNKNOWN_FRAMES_BEFORE_ASK  = 20

# ══════════════════════════════════════════
#  Logging
# ══════════════════════════════════════════
LOG_ENABLED = True
LOG_DIR     = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# ══════════════════════════════════════════
#  STT Settings
# ══════════════════════════════════════════
GOOGLE_STT_ENABLED = _env_bool("VISION_GOOGLE_STT", True)
GOOGLE_STT_TIMEOUT = _env_float("VISION_GOOGLE_STT_TIMEOUT", 5.0)
GOOGLE_STT_FAILS_BEFORE_OFFLINE = _env_int("VISION_GOOGLE_STT_FAILS_BEFORE_OFFLINE", 5)
GOOGLE_STT_ONLINE_CHECK_INTERVAL = _env_float("VISION_GOOGLE_STT_CHECK_INTERVAL", 5.0)
GOOGLE_STT_ONLINE_CHECK_TIMEOUT = _env_float("VISION_GOOGLE_STT_CHECK_TIMEOUT", 1.5)
GOOGLE_STT_ONLINE_HOSTS = (
    ("www.google.com", 443),
    ("www.gstatic.com", 80),
    ("8.8.8.8", 53),
)
VOSK_ENABLED = True   # False = Google only, True = Vosk fallback when offline
STT_DEVICE_INDEX = None  # None = auto-select available microphone

# ══════════════════════════════════════════
#  Performance & Quality Tuning
# ══════════════════════════════════════════

# TTA — only run 5-pass TTA when confidence is below this threshold
# Above threshold: single fast predict (~50ms)
# Below threshold: full TTA (~250ms) for better accuracy
TTA_CONFIDENCE_THRESHOLD = 0.55  # reduced — less TTA = faster response

# Emotion smoothing — history window per face
EMOTION_HISTORY_SIZE = 2     # نزلنا من 3 ل→ 2 — تأكيد أسرع للتعبير الجديد
EMOTION_STABLE_RATIO = 0.65  # رفعنا من 0.50 ل→ 0.65 لتعويض النافذة الأصغر

# Adaptive inference rate
INFERENCE_STABLE_N   = 5   # نزلنا من 8 ل→ 5 — السيستم يفضل مستجيباً حتى في وضع stable
INFERENCE_ACTIVE_N   = 3   # نزلنا من 4 ل→ 3 — كل 3 فريمات = 5 قراءات/ثانية عند 15fps
EMOTION_STABLE_FRAMES = 8  # نزلنا من 20 ل→ 8 — أقل وقت قبل اعتبار التعبير ثابتاً

# TTS audio cache — cache generated mp3 files for repeated phrases
TTS_CACHE_ENABLED = True
TTS_CACHE_MAX     = 50     # max phrases to cache in memory

# Face recognition adaptive threshold
FACE_THRESHOLD_LOW_LIGHT = 0.57   # أكثر تسامحاً في الإضاءة المنخفضة

# Quiet automatic announcements so listening remains available.
TTS_COOLDOWN_SEC = 8.0
EMOTION_CHANGE_COOLDOWN = 1.0
UNKNOWN_ANNOUNCE_COOLDOWN = 12.0
ANNOUNCE_EMOTION_STABLE_COUNT = 2

# Faster emotion reads while keeping automatic speech quiet.
INFERENCE_ACTIVE_N = 1
INFERENCE_STABLE_N = 3
EMOTION_STABLE_FRAMES = 5
TTA_CONFIDENCE_THRESHOLD = 0.45

# More stable identity reads after registration.
FACE_THRESHOLD = 0.51
FACE_THRESHOLD_LOW_LIGHT = 0.54
FACE_SINGLE_PERSON_THRESHOLD = 0.44
FACE_SINGLE_PERSON_THRESHOLD_LOW_LIGHT = 0.47
FACE_GAP_RATIO = 1.12
FACE_STRONG_MATCH_DISTANCE = 0.40
FACE_RECENT_HOLD_DISTANCE = 0.53
FACE_RECENT_HOLD_SEC = 2.5
FACE_TRACK_RESET_DISTANCE = 0.42
RECOGNITION_VOTE_MIN_COUNT = 3
RECOGNITION_VOTE_MIN_RATIO = 0.65
KNOWN_PERSON_UNKNOWN_SUPPRESS_SEC = 8.0
FACE_RECOGNITION_EVERY_N = _env_int("VISION_FACE_RECOGNITION_EVERY_N", 1)
FACE_RECOGNITION_CACHE_SEC = _env_float("VISION_FACE_RECOGNITION_CACHE_SEC", 1.2)
CAMERA_READ_FAIL_LIMIT = _env_int("VISION_CAMERA_READ_FAIL_LIMIT", 8)

if RPI_MODE:
    CAMERA_INDEX = int(os.environ.get("VISION_CAMERA_INDEX", "0"))
    FRAME_WIDTH = int(os.environ.get("VISION_FRAME_WIDTH", "640"))
    FRAME_HEIGHT = int(os.environ.get("VISION_FRAME_HEIGHT", "480"))
    TARGET_FPS = int(os.environ.get("VISION_TARGET_FPS", "12"))
    SHOW_WINDOW = _env_bool("VISION_SHOW_WINDOW", False)
    USE_TFLITE_EMOTION = _env_bool("VISION_USE_TFLITE", True)
    INFERENCE_ACTIVE_N = int(os.environ.get("VISION_INFERENCE_ACTIVE_N", "2"))
    INFERENCE_STABLE_N = int(os.environ.get("VISION_INFERENCE_STABLE_N", "4"))
    TTA_CONFIDENCE_THRESHOLD = float(os.environ.get("VISION_TTA_THRESHOLD", "0.40"))
    FACE_RECOGNITION_EVERY_N = _env_int("VISION_FACE_RECOGNITION_EVERY_N", 3)
    FACE_RECOGNITION_CACHE_SEC = _env_float("VISION_FACE_RECOGNITION_CACHE_SEC", 1.5)
