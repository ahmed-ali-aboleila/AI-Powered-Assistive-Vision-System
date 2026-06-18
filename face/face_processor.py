"""
face_processor.py — v6 Final
==============================
المشكلة في كل النسخ السابقة:
  DeepFace.represent() كانت بتتستدعى كل frame لكل وجه
  = 3 وجوه × 120ms = 360ms تأخير كل frame

الحل في v6:
  1. Detection:  Haar Cascade         (~5ms)
  2. Crop:       نقطع منطقة الوجه
  3. Embedding:  DeepFace مرة واحدة  (~120ms) في thread منفصل
  4. Matching:   Cosine على RAM       (~1ms)  فوري
  
  النتيجة: الكاميرا شغّالة بـ 30fps
           الـ recognition بيحصل كل 500ms تقريباً بدل كل frame
           
Liveness: LBP texture (~2ms)
Voting:   7 frames بالأغلبية لكل وجه منفصل
"""

import cv2
import numpy as np
import logging
import time
from typing import List, Tuple, Optional
from collections import Counter
import config

logger = logging.getLogger(__name__)

# ── DeepFace ──────────────────────────────────────────────────────────────────
try:
    from deepface import DeepFace
    DF_OK = True
    print("[FaceProc] DeepFace loaded")
except ImportError:
    DF_OK = False
    print("[FaceProc] DeepFace not found!")

# ── LBP ───────────────────────────────────────────────────────────────────────
try:
    from skimage.feature import local_binary_pattern as _lbp
    LBP_OK = True
except ImportError:
    LBP_OK = False

# ── Config ────────────────────────────────────────────────────────────────────
HAAR_XML      = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
MODEL         = "Facenet512"
BACKEND       = "opencv"
THRESHOLD     = 0.50    # cosine distance — أقل = أشبه
LBP_THRESHOLD = 18.0   # liveness
LBP_R, LBP_P  = 3, 24


class FaceProcessor:
    def __init__(self, threshold: float = None):
        self._cascade  = cv2.CascadeClassifier(HAAR_XML)
        if self._cascade.empty():
            raise RuntimeError("Haar Cascade not found")

        # تحميل كاشف الوجوه الجانبية (Profile Face)
        profile_path = cv2.data.haarcascades + "haarcascade_profileface.xml"
        self._profile_cascade = cv2.CascadeClassifier(profile_path)
        if self._profile_cascade.empty():
            logger.warning("[FaceProc] Profile Cascade not found! Side angles will not be detected.")

        self.threshold = threshold or THRESHOLD
        self._df_ok    = DF_OK

        if DF_OK:
            self._warmup()

        if LBP_OK:
            print(f"[FaceProc] Liveness ON (LBP>{LBP_THRESHOLD})")

        print(f"[FaceProc] Threshold={self.threshold}")

        # Voting منفصل لكل موقع وجه في الإطار
        # البفر 12 فريم، 72% أغلبية — كافي لمنع الأخطاء بدون إضافة تعقيد زيادة
        self._votes : dict = {}   # { grid_key: [name, ...] }
        self._vsize = 12
        self._last_known_by_grid : dict = {}  # { grid_key: (name, distance, timestamp) }

        # Pre-computed gamma LUT (1/1.5 gamma for low-light boost)
        # Computed once here instead of every frame
        self._gamma_lut = np.array(
            [(i / 255.0) ** (1.0 / 1.5) * 255 for i in range(256)],
            dtype=np.uint8
        )

    def _warmup(self):
        print("[FaceProc] Loading Facenet512... (first run ~30s)")
        try:
            dummy = np.zeros((160, 160, 3), dtype=np.uint8)
            DeepFace.represent(img_path=dummy, model_name=MODEL,
                               enforce_detection=False, detector_backend=BACKEND)
            print("[FaceProc] Model ready")
        except Exception as e:
            logger.warning(f"Warmup: {e}")

    # ── Detection ─────────────────────────────────────────────────────────────

    def _overlaps(self, box1: Tuple, box_list: List[Tuple]) -> bool:
        """يتحقق مما إذا كان المربع يتداخل بشكل كبير مع أي مربع آخر في القائمة لمنع التكرار."""
        x1, y1, w1, h1 = box1
        for x2, y2, w2, h2 in box_list:
            xi1 = max(x1, x2)
            yi1 = max(y1, y2)
            xi2 = min(x1 + w1, x2 + w2)
            yi2 = min(y1 + h1, y2 + h2)
            inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
            if inter_area > 0:
                area1 = w1 * h1
                area2 = w2 * h2
                overlap_ratio = inter_area / min(area1, area2)
                if overlap_ratio > 0.4:
                    return True
        return False

    def detect(self, frame: np.ndarray) -> List[Tuple]:
        """Haar detection — كشف الوجوه الأمامية والجانبية لمنع مشاكل الزوايا"""
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Gamma correction — uses pre-computed LUT (computed once in __init__)
        g = cv2.LUT(g, self._gamma_lut)
        
        # 1. كشف الوجوه الأمامية (Frontal)
        f = self._cascade.detectMultiScale(
            g, scaleFactor=1.1, minNeighbors=4,
            minSize=(45, 45)   # أصغر حجم للكشف عن الوجوه البعيدة
        )
        faces = [tuple(x) for x in f] if len(f) else []

        # 2. كشف الوجوه الجانبية (Profile - اليمين)
        if not self._profile_cascade.empty():
            p_faces = self._profile_cascade.detectMultiScale(
                g, scaleFactor=1.1, minNeighbors=4,
                minSize=(45, 45)
            )
            for pf in p_faces:
                pf_t = tuple(pf)
                if not self._overlaps(pf_t, faces):
                    faces.append(pf_t)

            # 3. كشف الوجوه الجانبية (Profile - اليسار عن طريق قلب الصورة أفقياً)
            g_flipped = cv2.flip(g, 1)
            p_faces_left = self._profile_cascade.detectMultiScale(
                g_flipped, scaleFactor=1.1, minNeighbors=4,
                minSize=(45, 45)
            )
            w_img = frame.shape[1]
            for pf in p_faces_left:
                x_flipped, y, w, h = pf
                x_orig = w_img - x_flipped - w
                pf_orig = (x_orig, y, w, h)
                if not self._overlaps(pf_orig, faces):
                    faces.append(pf_orig)

        return faces

    # ── Liveness ──────────────────────────────────────────────────────────────

    def is_live(self, frame: np.ndarray, box: Tuple) -> Tuple[bool, float]:
        if not LBP_OK: return True, 99.0
        x, y, w, h = box
        p   = int(min(w,h)*0.1)
        roi = frame[max(0,y-p):min(frame.shape[0],y+h+p),
                    max(0,x-p):min(frame.shape[1],x+w+p)]
        if roi.size == 0: return True, 0.0
        g   = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape)==3 else roi
        g   = cv2.resize(g, (64, 64))
        
        # Check brightness of the face area. In dark environments, LBP texture analysis is highly unstable.
        face_brightness = float(np.mean(g))
        if face_brightness < 55.0:
            return True, 99.0  # Bypass liveness check in low light to prevent false lockout
            
        lb  = _lbp(g, LBP_P, LBP_R, method="uniform")
        hist, _ = np.histogram(lb.ravel(), bins=LBP_P+2,
                               range=(0,LBP_P+2), density=True)
        var = float(np.var(hist)*10000)
        return var >= LBP_THRESHOLD, var

    # ── Embedding ─────────────────────────────────────────────────────────────

    def embed(self, frame: np.ndarray, box: Tuple) -> Optional[np.ndarray]:
        """
        يستخرج الـ embedding من الوجه.
        بيتستدعى من الـ inference thread — مش من الـ main thread.
        """
        if not self._df_ok: return self._embed_pixel(frame, box)
        return self._embed_df(frame, box)

    def _embed_df(self, frame, box) -> Optional[np.ndarray]:
        x, y, w, h = box
        # margin لتحسين الدقة
        pad = max(10, int(min(w,h)*0.15))
        roi = frame[max(0,y-pad):min(frame.shape[0],y+h+pad),
                    max(0,x-pad):min(frame.shape[1],x+w+pad)]
        if roi.size == 0: return None
        try:
            r = DeepFace.represent(
                img_path          = roi,
                model_name        = MODEL,
                enforce_detection = False,
                detector_backend  = BACKEND,
            )
            if r:
                v = np.array(r[0]["embedding"], dtype=np.float32)
                n = np.linalg.norm(v)
                return v/n if n > 0 else None
        except Exception as e:
            logger.debug(f"embed: {e}")
        return None

    def _embed_pixel(self, frame, box) -> Optional[np.ndarray]:
        """Fallback لو DeepFace مش موجود"""
        x, y, w, h = box
        roi = frame[y:y+h, x:x+w]
        if roi.size == 0: return None
        g   = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape)==3 else roi
        g   = cv2.createCLAHE(2.0,(8,8)).apply(g)
        v   = cv2.resize(g,(128,128)).astype(np.float32).flatten()
        n   = np.linalg.norm(v)
        return v/n if n > 0 else None

    # ── Identify ──────────────────────────────────────────────────────────────

    def identify(self, emb: np.ndarray, db: dict,
                 box: Tuple = None) -> Tuple[str, float]:
        """
        يطابق الـ embedding مع قاعدة البيانات باستخدام Cosine Distance.
        الخطوات:
          1. لكل شخص محفوظ: نحسب المسافة لكل الـ embeddings المحفوظة
          2. نأخذ أحسن 10 نتائج (أقرب embeddings)
          3. نحسب المتوسط المرجّح — الأقرب له وزن أعلى
          4. نختار الأقل مسافة إجمالاً
          5. فلتر: لو المسافة للثاني > 1.3x المسافة للأول → الأول مؤكد أكثر
          6. Vote buffer 12 فريم، 72% أغلبية قبل الإعلان
        """
        if not db or emb is None: return "Unknown", 0.0

        scores = {}   # { name: weighted_avg_dist }
        for name, rec in db.items():
            if not rec.embeddings or name.startswith("__blocked__"):
                continue
            stored  = np.array(rec.embeddings)         # (N, 512)
            dists   = 1.0 - (stored @ emb)             # cosine distance لكل embedding
            top_n   = sorted(dists)[:min(10, len(dists))]  # أحسن 10
            weights = [1.0 / (d + 1e-6) for d in top_n]
            w_sum   = sum(weights)
            avg     = float(sum(d * w / w_sum for d, w in zip(top_n, weights)))
            scores[name] = avg

        if not scores:
            return "Unknown", 0.0

        # الشخص الأقرب
        sorted_scores = sorted(scores.items(), key=lambda x: x[1])
        best_name, best_dist = sorted_scores[0]

        # فلتر الوضوح: لازم يكون الفارق واضح بين الأول والتاني
        # لو مافيش ثاني أو الثاني بعيد بـ 4% أكتر → الأول مؤكد
        if len(sorted_scores) >= 2:
            second_dist = sorted_scores[1][1]
            gap_ratio   = second_dist / (best_dist + 1e-6)
            min_gap = getattr(config, "FACE_GAP_RATIO", 1.04)
            strong_dist = getattr(config, "FACE_STRONG_MATCH_DISTANCE", 0.40)
            # لو الماتش قوي جداً، بنعتبره مؤكد مباشرة
            if best_dist <= strong_dist:
                confident = True
            else:
                # لو الماتش متوسط، بنشترط فجوة بنسبة 1.04 على الأقل لمنع الخلط بين الأشخاص
                confident = best_dist <= self.threshold and gap_ratio >= min_gap
        else:
            low_light_mode = self.threshold > getattr(config, "FACE_THRESHOLD", 0.53)
            single_threshold = (
                getattr(config, "FACE_SINGLE_PERSON_THRESHOLD_LOW_LIGHT", 0.52)
                if low_light_mode
                else getattr(config, "FACE_SINGLE_PERSON_THRESHOLD", 0.49)
            )
            confident = best_dist <= single_threshold

        raw_name = best_name if confident else "Unknown"
        score    = round(1.0 - best_dist, 3)

        # Vote buffer — 12 فريم، 72% أغلبية
        key = self._grid_key(box)
        now = time.time()
        if raw_name == "Unknown":
            held = self._last_known_by_grid.get(key)
            hold_sec = getattr(config, "FACE_RECENT_HOLD_SEC", 2.5)
            hold_dist = getattr(config, "FACE_RECENT_HOLD_DISTANCE", 0.53)
            if held:
                last_name, _last_dist, last_time = held
                if best_name == last_name and best_dist <= hold_dist and (now - last_time) <= hold_sec:
                    raw_name = last_name

        if key not in self._votes:
            self._votes[key] = []
        buf = self._votes[key]
        buf.append(raw_name)
        if len(buf) > self._vsize: buf.pop(0)

        voted_name = self._vote(buf)
        if voted_name != "Unknown":
            self._last_known_by_grid[key] = (voted_name, best_dist, now)
        return voted_name, score

    def identify_blocked(self, emb: np.ndarray, db: dict) -> Optional[str]:
        """
        هل الوجه ده محظور؟ لو أيوه يرجع اسم الشخص المحظور المطابق.
        بيستخدم threshold أضيق (0.35) عشان يتأكد إن الشخص ده هو هو المبلوك
        ومش أي شخص عنده شبه بعيد بالمبلوك
        """
        BLOCK_THRESHOLD = 0.35   # أضيق من الـ recognition threshold
        if not db or emb is None: return None
        for name, rec in db.items():
            if not name.startswith("__blocked__"): continue
            if not rec.embeddings: continue
            stored = np.array(rec.embeddings)
            dists  = 1.0 - (stored @ emb)
            # نأخذ أحسن 3 نتائج ومعدلهم للدقة
            top3   = sorted(dists)[:min(3, len(dists))]
            avg    = float(np.mean(top3))
            if avg <= BLOCK_THRESHOLD:
                return name
        return None

    # ── Voting ────────────────────────────────────────────────────────────────

    @staticmethod
    def _vote(buf: list) -> str:
        if not buf: return "Unknown"
        c = Counter(buf).most_common(1)[0]
        # نزلنا من 72% ل→ 65% — يتحمل حتى 35% من الفريمات فيها Unknown بسبب تعبير
        min_ratio = getattr(config, "RECOGNITION_VOTE_MIN_RATIO", 0.65)
        return c[0] if c[1]/len(buf) >= min_ratio else "Unknown"

    @staticmethod
    def _grid_key(box) -> str:
        if not box: return "0_0"
        x, y, w, h = box
        # Finer grid (80px cells) — avoids merging two nearby faces
        return f"{(x+w//2)//80}_{(y+h//2)//80}"

    def reset(self):
        self._votes.clear()
        self._last_known_by_grid.clear()

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, frame, box, label, score, lv=None):
        x, y, w, h = box
        if label == "Blocked":      col = (100,100,100)
        elif label == "Unknown":    col = (0,0,220)
        elif label == "Screen":     col = (0,165,255)
        else:                       col = (0,220,0)
        cv2.rectangle(frame, (x,y), (x+w,y+h), col, 2)
        txt = f"{label} ({score:.2f})"
        if lv is not None: txt += f" L:{lv:.0f}"
        cv2.putText(frame, txt, (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, col, 2)

    @staticmethod
    def _cos(a, b) -> float:
        d = np.linalg.norm(a)*np.linalg.norm(b)
        return float(np.dot(a,b)/d) if d > 0 else 0.0
