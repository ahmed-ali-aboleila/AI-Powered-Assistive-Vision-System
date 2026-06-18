"""
shared/stt.py — v8
===================
- STT عربي/إنجليزي حسب config.LANGUAGE
- Google بيجرب اللغة الحالية أولاً
- Vosk fallback (EN أو AR حسب اللغة)
- get_name() بينظف التكرار تلقائياً
"""
import speech_recognition as sr
import audioop
import logging, time, threading, os, json, re
import config

logger = logging.getLogger(__name__)

YES_EN = {"yes","yeah","yep","yup","y","sure","ok","okay","correct","right","indeed", "agree", "confirm"}
YES_AR = {"نعم","أيوه","ايوه","أيوة","ايوة","تمام","ماشي","اوكي","صح","موافق","اه","أه","مظبوط","بالتأكيد", "فعلا", "طبعا"}
NO_EN  = {"no","nope","nah","n","skip","cancel","stop","wrong","negative","don't","dont","refuse", "deny"}
NO_AR  = {"لأ","لا","بلاش","الغي","الغ","مش","لا يا","خطأ","غلط","ارفض","إلغاء","الغاء"}

_VOSK_NOISE_COMMAND_WORDS = {
    "vision", "register", "save", "add", "person", "new", "learn",
    "delete", "del", "remove", "erase", "forget", "clear", "wipe",
    "block", "unblock", "allow", "all", "names", "arabic", "english",
    "male", "female", "voice", "number", "one", "two", "three", "four",
    "five", "six", "seven", "eight", "nine", "ten", "yes", "no",
    "goodbye", "bye", "quiet", "mute", "silence", "unmute", "standby",
    "pause", "resume", "continue",
}


def _looks_like_vosk_noise(text: str) -> bool:
    words = re.findall(r"[a-zA-Z0-9]+", str(text or "").lower())
    if len(words) < 5:
        return False
    hits = sum(1 for word in words if word in _VOSK_NOISE_COMMAND_WORDS)
    return hits >= 3


VOSK_MODEL_EN = os.environ.get("VOSK_MODEL_EN", "models/vosk-model")

VOSK_MODEL_AR_CANDIDATES = (
    os.environ.get("VOSK_MODEL_AR", ""),
    "models/vosk-model-ar",
    "models/vosk-model-ar-mgb2-0.4",
)


def _first_existing_path(paths):
    for path in paths:
        if path and os.path.exists(path):
            return path
    return next((p for p in paths if p), "models/vosk-model-ar")


VOSK_MODEL_AR = _first_existing_path(VOSK_MODEL_AR_CANDIDATES)

_NON_NAME_FRAGMENTS = {
    "ah", "uh", "um", "huh", "eh", "mm", "hm", "ha", "oh", "او", "اه",
}

_ARABIC_NAME_OVERRIDES = {
    "علي": "Ali",
    "على": "Ali",
    "احمد": "Ahmed",
    "أحمد": "Ahmed",
    "إحمد": "Ahmed",
    "محمد": "Mohamed",
    "محمود": "Mahmoud",
    "مصطفى": "Mostafa",
    "مصطفي": "Mostafa",
    "ابراهيم": "Ibrahim",
    "إبراهيم": "Ibrahim",
    "اسماعيل": "Ismail",
    "إسماعيل": "Ismail",
    "يوسف": "Youssef",
    "عمر": "Omar",
    "عمرو": "Amr",
    "حسن": "Hassan",
    "حسين": "Hussein",
    "خالد": "Khaled",
    "كريم": "Karim",
    "مريم": "Mariam",
    "فاطمة": "Fatma",
    "فاطمه": "Fatma",
    "نور": "Nour",
}


_ARABIC_NAME_OVERRIDES.update({
    "\u0633\u0639\u064a\u062f": "Said",
    "\u0633\u064a\u062f": "Said",
    "\u0639\u0644\u064a": "Ali",
    "\u0639\u0644\u0649": "Ali",
    "\u0627\u062d\u0645\u062f": "Ahmed",
    "\u0623\u062d\u0645\u062f": "Ahmed",
    "\u0645\u062d\u0645\u062f": "Mohamed",
    "\u0645\u062d\u0645\u0648\u062f": "Mahmoud",
    "\u0645\u0635\u0637\u0641\u0649": "Mostafa",
    "\u0645\u0635\u0637\u0641\u064a": "Mostafa",
    "\u0627\u0628\u0631\u0627\u0647\u064a\u0645": "Ibrahim",
    "\u0625\u0628\u0631\u0627\u0647\u064a\u0645": "Ibrahim",
    "\u0627\u0633\u0645\u0627\u0639\u064a\u0644": "Ismail",
    "\u064a\u0648\u0633\u0641": "Youssef",
    "\u0639\u0645\u0631": "Omar",
    "\u0639\u0645\u0631\u0648": "Amr",
    "\u062d\u0633\u0646": "Hassan",
    "\u062d\u0633\u064a\u0646": "Hussein",
    "\u062e\u0627\u0644\u062f": "Khaled",
    "\u0643\u0631\u064a\u0645": "Karim",
    "\u0645\u0631\u064a\u0645": "Mariam",
    "\u0641\u0627\u0637\u0645\u0629": "Fatma",
    "\u0646\u0648\u0631": "Nour",
})

_ARABIC_TRANSLIT = {
    "\u0627": "a", "\u0623": "a", "\u0625": "i", "\u0622": "a",
    "\u0628": "b", "\u062a": "t", "\u062b": "th", "\u062c": "g",
    "\u062d": "h", "\u062e": "kh", "\u062f": "d", "\u0630": "z",
    "\u0631": "r", "\u0632": "z", "\u0633": "s", "\u0634": "sh",
    "\u0635": "s", "\u0636": "d", "\u0637": "t", "\u0638": "z",
    "\u0639": "a", "\u063a": "gh", "\u0641": "f", "\u0642": "q",
    "\u0643": "k", "\u0644": "l", "\u0645": "m", "\u0646": "n",
    "\u0647": "h", "\u0648": "w", "\u064a": "y", "\u0649": "a",
    "\u0629": "a", "\u0624": "w", "\u0626": "y", "\u0621": "",
}


def _contains_arabic(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06ff]", text or ""))


def _normalize_arabic_name_token(token: str) -> str:
    return (token or "").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي").replace("ة", "ه")


def _transliterate_arabic_word(word: str) -> str:
    clean = re.sub(r"[^\u0600-\u06ff]", "", word or "")
    if not clean:
        return word
    result = "".join(_ARABIC_TRANSLIT.get(ch, "") for ch in clean)
    result = re.sub(r"aa+", "a", result)
    return result.title()


def _arabic_name_to_latin(text: str) -> str:
    words = str(text or "").split()
    converted = []
    for word in words[:3]:
        clean = re.sub(r"[^\w\u0600-\u06ff]", "", word)
        converted.append(
            _ARABIC_NAME_OVERRIDES.get(clean)
            or _ARABIC_NAME_OVERRIDES.get(_normalize_arabic_name_token(clean))
            or _transliterate_arabic_word(clean)
        )
    return " ".join(converted).strip()


def _looks_like_bad_name(name: str) -> bool:
    n = str(name or "").strip().lower()
    compact = re.sub(r"[^a-z\u0600-\u06ff]", "", n)
    if compact in _NON_NAME_FRAGMENTS:
        return True
    if re.fullmatch(r"[a-z]{1,2}", compact) and compact not in {"li", "jo"}:
        return True
    return False

OFFLINE_COMMANDS_EN = [
    "vision","start vision","hi vision","hey vision","close system","goodbye",
    "register","save","add","record","new person","learn",
    "block","ban","blacklist","unblock","allow","unlock",
    "delete","remove","erase","forget","clear","wipe","list","names","show names",
    "who","identify","tell me","who is",
    "quiet","silence","mute","speak","resume","continue","stop",
    "yes","no","yeah","nope","okay","cancel",
    "english","arabic","exit","all","number","one","two","three","four","five",
    "six","seven","eight","nine","ten"
]
OFFLINE_COMMANDS_AR = [
    "فيجن","فيجين","ابدا فيجن","ابدأ فيجن","بصر","مساعد","اغلق","اقفل","وداعا","مع السلامة",
    "سجل","تسجيل","اضف","ضيف","احفظ","احظر","حظر","امنع","فك حظر","ارفع الحظر",
    "احذف","امسح","شيل","حذف","قائمة","اسماء","الاسامي",
    "مين","عرفني","هو مين","من هذا","اسكت","سكوت","صمت","اتكلم","كمل","استمر","وقف",
    "نعم","لا","أيوه","ايوه","تمام","بلاش","عربي","انجليزي","الكل","كل","رقم",
    "واحد","اتنين","اثنين","تلاتة","ثلاثة","اربعة","خمسة","ستة","سبعة",
    "ثمانية","تسعة","عشرة"
]

OFFLINE_COMMANDS_EN = [
    "vision", "start vision",
    "vision standby", "vision pause", "standby", "pause",
    "vision resume", "vision continue", "resume", "continue",
    "close vision", "goodbye", "bye vision",
    "vision who is this", "vision identify", "who is this", "identify",
    "vision register", "vision add person", "vision save person",
    "vision new person", "vision register new person",
    "register", "add person", "save person", "new person", "register new person",
    "vision improve person", "vision update person",
    "vision improve registration", "vision update registration",
    "vision improved person", "vision improved registration",
    "improve person", "improved person", "update person",
    "improve registration", "improved registration", "update registration",
    "vision delete", "vision del", "vision remove",
    "vision delete person", "vision remove person", "vision delete number",
    "delete", "del", "remove", "delete person", "remove person", "delete number",
    "vision delete all", "vision delete all names", "delete all", "delete all names",
    "vision list names", "vision show names", "vision registered names",
    "list names", "show names", "registered names",
    "vision block", "vision block person", "block", "block person",
    "vision unblock", "vision unblock person", "unblock", "unblock person",
    "vision arabic", "vision english", "arabic", "english",
    "switch to arabic", "switch to english",
    "vision arabic male voice", "vision arabic female voice",
    "vision english male voice", "vision english female voice",
    "arabic male voice", "arabic female voice",
    "english male voice", "english female voice",
    "vision quiet", "vision mute", "vision silence", "vision unmute",
    "quiet", "mute", "silence", "unmute",
    "yes", "no", "yeah", "nope", "okay", "cancel",
    "number", "one", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "ten"
]

OFFLINE_COMMANDS_AR = [
    "فيجن", "فيجين", "ابدأ فيجن", "ابدا فيجن",
    "فيجن هدوء", "فيجن استنى", "هدوء", "استنى",
    "فيجن تابع", "فيجن كمل", "تابع", "كمل",
    "اغلق", "أغلق", "اقفل", "أقفل", "مع السلامة",
    "فيجن مين ده", "فيجن عرفني", "فيجن من هذا", "مين ده", "عرفني", "من هذا",
    "فيجن سجل", "فيجن ضيف شخص", "فيجن احفظ الشخص",
    "فيجن شخص جديد", "فيجن سجل شخص جديد",
    "سجل", "ضيف شخص", "احفظ الشخص", "شخص جديد", "سجل شخص جديد",
    "فيجن حسن الشخص", "فيجن حسن التسجيل", "فيجن حدث التسجيل",
    "حسن الشخص", "حسن التسجيل", "حدث التسجيل",
    "فيجن احذف", "فيجن امسح",
    "فيجن احذف شخص", "فيجن امسح شخص", "فيجن احذف رقم",
    "احذف", "امسح", "احذف شخص", "امسح شخص", "احذف رقم",
    "فيجن امسح الكل", "فيجن احذف كل الاسماء", "فيجن احذف كل الأسماء",
    "امسح الكل", "احذف كل الاسماء", "احذف كل الأسماء",
    "فيجن اسماء", "فيجن أسماء", "فيجن مين مسجل",
    "فيجن اعرض الاسماء", "فيجن اعرض الأسماء",
    "اسماء", "أسماء", "مين مسجل", "اعرض الاسماء", "اعرض الأسماء",
    "فيجن احظر", "فيجن احظر الشخص", "احظر", "احظر الشخص",
    "فيجن فك حظر", "فيجن ارفع الحظر", "فك حظر", "ارفع الحظر",
    "فيجن عربي", "فيجن انجليزي", "فيجن إنجليزي", "عربي", "انجليزي", "إنجليزي",
    "فيجن صوت رجالي عربي", "فيجن صوت نسائي عربي",
    "فيجن صوت رجالي انجليزي", "فيجن صوت نسائي انجليزي",
    "فيجن صوت رجالي إنجليزي", "فيجن صوت نسائي إنجليزي",
    "صوت رجالي عربي", "صوت نسائي عربي",
    "صوت رجالي انجليزي", "صوت نسائي انجليزي",
    "صوت رجالي إنجليزي", "صوت نسائي إنجليزي",
    "فيجن اسكت", "فيجن صمت", "فيجن شغل الصوت",
    "اسكت", "صمت", "شغل الصوت",
    "نعم", "لا", "أيوه", "ايوه", "تمام", "بلاش", "الغاء", "إلغاء",
    "الكل", "كل", "رقم",
    "واحد", "واحدة", "اتنين", "اثنين", "تلاتة", "ثلاثة", "اربعة", "أربعة",
    "خمسة", "ستة", "سبعة", "ثمانية", "تمانية", "تسعة", "عشرة"
]


class STT:
    def __init__(self):
        self.r = sr.Recognizer()
        self.r.pause_threshold          = 0.85
        self.r.phrase_threshold         = 0.25
        self.r.non_speaking_duration    = 0.45
        self.r.dynamic_energy_threshold = False
        # خفضنا الحساسية لـ 150 للاستجابة الفورية والتوافق مع سماعات AirPods والميكروفونات الضعيفة
        self.r.energy_threshold         = 150
        self._mic = self._select_microphone()
        self._online = True
        self._google_fail_count = 0      # عداد فشل Google المتتالي — يحتاج 3 فشل متتالي لإيقاف Google
        self._last_online_check = 0
        self.is_listening = False

        # Vosk — يحمّل الاتنين في الخلفية
        self._vosk_en = None
        self._vosk_en_names = None
        self._vosk_ar = None
        self._vosk_en_ready = False
        self._vosk_en_names_ready = False
        self._vosk_ar_ready = False
        self._init_vosk()
        self._start_online_checker()

    def _select_microphone(self):
        configured = getattr(config, "STT_DEVICE_INDEX", None)
        if configured is not None:
            print(f"[STT] Using configured microphone index: {configured}")
            return configured

        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            try:
                input_devices = []
                for i in range(pa.get_device_count()):
                    info = pa.get_device_info_by_index(i)
                    if int(info.get("maxInputChannels", 0)) <= 0:
                        continue
                    name = str(info.get("name", "")).strip()
                    rate = int(float(info.get("defaultSampleRate", 16000)))
                    input_devices.append((i, name, rate))

                if not input_devices:
                    print("[STT] No input microphones found; using system default.")
                    return None

                priority_words = (
                    "headset", "hands-free", "airpods", "freebuds",
                    "microphone", "mic", "input", "capture",
                )
                ordered = []
                for word in priority_words:
                    for device in input_devices:
                        idx, name, _rate = device
                        if device not in ordered and word in name.lower():
                            ordered.append(device)
                for device in input_devices:
                    if device not in ordered:
                        ordered.append(device)

                for idx, name, _rate in ordered:
                    if self._microphone_works(idx):
                        print(f"[STT] Auto microphone: #{idx} {name}")
                        return idx
                    print(f"[STT] Skipping microphone #{idx}: {name}")

                print("[STT] No tested microphone worked; using system default.")
                return None
            finally:
                pa.terminate()
        except Exception as e:
            print(f"[STT] Microphone auto-select failed: {e!r}; using system default.")
            return None

    def _microphone_works(self, index) -> bool:
        try:
            with sr.Microphone(device_index=index) as src:
                self.r.adjust_for_ambient_noise(src, duration=0.05)
            return True
        except Exception:
            return False

    def _recover_microphone(self) -> bool:
        old = self._mic
        configured = getattr(config, "STT_DEVICE_INDEX", None)
        if configured is not None:
            return False
        self._mic = self._select_microphone()
        return self._mic != old

    def _start_online_checker(self):
        def _check_loop():
            while True:
                try:
                    import socket
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(2.0)
                    try:
                        s.connect(("www.google.com", 80))
                        self._online = True
                        self._google_fail_count = 0   # استعاد عند نجاح الاتصال
                    finally:
                        s.close()
                except Exception:
                    self._online = False
                # تحقق كل 10 ثواني بدل 30 — استعادة أسرع
                time.sleep(10.0)
        threading.Thread(target=_check_loop, daemon=True).start()

    # ══════════════════════════════════════════════════════
    #  Vosk init
    # ══════════════════════════════════════════════════════

    def _init_vosk(self):
        def _load():
            try:
                from vosk import Model, KaldiRecognizer, SetLogLevel
                SetLogLevel(-1)

                # English
                if os.path.exists(VOSK_MODEL_EN):
                    print(f"[STT] Loading English Vosk model: {VOSK_MODEL_EN}")
                    m = Model(VOSK_MODEL_EN)
                    self._vosk_en = KaldiRecognizer(
                        m, 16000, json.dumps(OFFLINE_COMMANDS_EN))
                    # Open recognizer for names only; commands stay grammar-limited.
                    self._vosk_en_names = KaldiRecognizer(m, 16000)
                    self._vosk_en_ready = True
                    self._vosk_en_names_ready = True
                    print("[STT] English Vosk ready")
                else:
                    print("[STT] English Vosk model not found")

                # Arabic
                if os.path.exists(VOSK_MODEL_AR):
                    print(f"[STT] Loading Arabic Vosk model: {VOSK_MODEL_AR}")
                    m2 = Model(VOSK_MODEL_AR)
                    # Some Arabic Vosk models do not support runtime grammar FSTs.
                    # Loading without a grammar keeps those models usable offline.
                    self._vosk_ar = KaldiRecognizer(m2, 16000)
                    self._vosk_ar_ready = True
                    print("[STT] Arabic Vosk ready")
                else:
                    print("[STT] Arabic Vosk not found. Expected one of:")
                    for path in VOSK_MODEL_AR_CANDIDATES:
                        if path:
                            print(f"[STT]   - {path}")
                    print("[STT] Download:")
                    print("[STT] https://alphacephei.com/vosk/models/vosk-model-ar-mgb2-0.4.zip")

            except Exception as e:
                print(f"[STT] Vosk init failed: {e}")

        threading.Thread(target=_load, daemon=True).start()

    # ══════════════════════════════════════════════════════
    #  Online check
    # ══════════════════════════════════════════════════════

    def _check_online(self) -> bool:
        return self._online

    # ══════════════════════════════════════════════════════
    #  Calibrate
    # ══════════════════════════════════════════════════════

    def calibrate(self, duration: float = 2.0):
        print("[STT] Calibrating mic...")
        try:
            with sr.Microphone(device_index=self._mic) as src:
                self.r.adjust_for_ambient_noise(src, duration=duration)
            # حد أدنى 150 لدعم AirPods والميكروفونات ضعيفة الالتقاط
            # حد أقصى 2000 لو بيئة ضوضاء عالية جداً
            self.r.energy_threshold = max(150, min(2000, self.r.energy_threshold))
            print(f"[STT] Ready. Threshold = {self.r.energy_threshold:.0f}")
        except Exception as e:
            logger.warning(f"Calibrate: {e!r}")
            print(f"[STT] Mic calibration failed on index {self._mic}: {type(e).__name__} {e!r}")
            if self._recover_microphone():
                print("[STT] Retrying calibration with recovered microphone...")
                try:
                    with sr.Microphone(device_index=self._mic) as src:
                        self.r.adjust_for_ambient_noise(src, duration=duration)
                    self.r.energy_threshold = max(150, min(2000, self.r.energy_threshold))
                    print(f"[STT] Ready. Threshold = {self.r.energy_threshold:.0f}")
                    return
                except Exception as retry_error:
                    print(f"[STT] Retry calibration failed: {type(retry_error).__name__} {retry_error!r}")
            self.r.energy_threshold = 150
            print("[STT] Using default threshold = 150")

    # ══════════════════════════════════════════════════════
    #  Listen
    # ══════════════════════════════════════════════════════

    def listen(self, timeout: float = 8.0,
               phrase_limit: float = 10.0,
               recal: bool = False,
               tts=None,
               names_mode: bool = False) -> str | None:
        """
        tts: مرجع لـ TTS object — لو موجود ينتظر لحد ما الـ TTS يخلص
             عشان الميكروفون ميلتقطش صوت السيستم نفسه
        """
        # استنى لحد ما الـ TTS يخلص كلامه (max 10 ثواني)
        if tts is not None:
            deadline = time.time() + 10.0
            while tts.busy() and time.time() < deadline:
                time.sleep(0.02)
            # انتظار قصير جدا بعد انتهاء الكلام لتجنب التقاط آخر صوت من الـ TTS
            time.sleep(0.02)

        if recal:
            try:
                with sr.Microphone(device_index=self._mic) as src:
                    self.r.adjust_for_ambient_noise(src, duration=0.5)
                # حد أدنى 150 لدعم سماعات البلوتوث والميكروفونات منخفضة الالتقاط
                self.r.energy_threshold = max(150, min(2000, self.r.energy_threshold))
            except Exception:
                pass

        try:
            with sr.Microphone(device_index=self._mic) as src:
                print(f"[STT] Listening... (E={self.r.energy_threshold:.0f})")
                self.is_listening = True
                audio = self.r.listen(src, timeout=timeout,
                                      phrase_time_limit=phrase_limit)
        except sr.WaitTimeoutError:
            print("[STT] No speech detected.")
            return None
        except Exception as e:
            logger.warning(f"Mic: {e!r}")
            print(f"[STT] Mic listen failed on index {self._mic}: {type(e).__name__} {e!r}")
            if self._recover_microphone():
                print("[STT] Retrying listen with recovered microphone...")
                try:
                    with sr.Microphone(device_index=self._mic) as src:
                        print(f"[STT] Listening... (E={self.r.energy_threshold:.0f})")
                        self.is_listening = True
                        audio = self.r.listen(src, timeout=timeout,
                                              phrase_time_limit=phrase_limit)
                except sr.WaitTimeoutError:
                    print("[STT] No speech detected.")
                    return None
                except Exception as retry_error:
                    print(f"[STT] Retry listen failed: {type(retry_error).__name__} {retry_error!r}")
                    return None
                finally:
                    self.is_listening = False
            else:
                return None
        finally:
            self.is_listening = False
        # ── فلتر 2: مدة الصوت — اتجاهل لو أقل من 0.2 ثانية (مش أمر حقيقي)
        try:
            duration = len(audio.get_raw_data()) / (audio.sample_rate * audio.sample_width)
            if duration < 0.2:
                print(f"[STT] Audio too short ({duration:.2f}s) — ignoring.")
                return None
            rms = audioop.rms(audio.get_raw_data(convert_width=2), 2)
            min_rms = max(70, int(self.r.energy_threshold * 0.35))
            if rms < min_rms:
                print(f"[STT] Audio too quiet (RMS={rms}, min={min_rms}) — ignoring.")
                return None
        except Exception:
            pass

        lang = getattr(config, "LANGUAGE", "en")

        result = None
        if self._check_online():
            result = self._google(audio, lang, names_mode=names_mode)
            if not result:
                print("[STT] Google failed — trying Vosk")
                result = self._vosk(audio, lang, names_mode=names_mode)
        else:
            result = self._vosk(audio, lang, names_mode=names_mode)

        # ── فلتر 3: نص قصير جداً — ممكن يكون ضوضاء اتعرف عليها غلط (مع استثناء الأرقام الفردية)
        if result and len(result.strip()) < 2 and not result.strip().isdigit():
            print(f"[STT] Text too short ('{result}') — ignoring.")
            return None

        return result

    # ══════════════════════════════════════════════════════
    #  Google STT — بيجرب اللغة الحالية أولاً
    # ══════════════════════════════════════════════════════

    def _google(self, audio, lang: str, names_mode: bool = False) -> str | None:
        google_lang = "ar-EG" if lang == "ar" else "en-US"
        import socket
        old_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(7.0)
            text = self.r.recognize_google(audio, language=google_lang)
            print(f"[STT] Google ({google_lang}): '{text}'")
            # نجاح → صفر عداد الفشل
            self._google_fail_count = 0
            result = text.lower().strip()
            if names_mode and _looks_like_bad_name(result):
                alt_lang = "ar-EG" if google_lang == "en-US" else "en-US"
                try:
                    alt = self.r.recognize_google(audio, language=alt_lang)
                    print(f"[STT] Google ({alt_lang} name retry): '{alt}'")
                    alt_result = alt.lower().strip()
                    if alt_result and not _looks_like_bad_name(alt_result):
                        return alt_result
                except Exception:
                    pass
            return result
        except sr.UnknownValueError:
            # مافهمش الكلام — مش مشكلة شبكة، نجاح Google بس مافيشش كلام واضح
            if lang == "ar":
                try:
                    text = self.r.recognize_google(audio, language="en-US")
                    print(f"[STT] Google (en-US fallback): '{text}'")
                    self._google_fail_count = 0
                    return text.lower().strip()
                except Exception:
                    return None
            else: # lang == "en"
                try:
                    text = self.r.recognize_google(audio, language="ar-EG")
                    print(f"[STT] Google (ar-EG fallback): '{text}'")
                    self._google_fail_count = 0
                    return text.lower().strip()
                except Exception:
                    return None
            return None
        except sr.RequestError as e:
            print(f"[STT] Google network error: {e}")
            self._google_fail_count += 1
            # فقط لو فشل 3 مرات متتالية → نعتبره غير متصل
            # مشكلة واحدة ماتخليش السيستم فوراً
            if self._google_fail_count >= 3:
                self._online = False
                print("[STT] Google offline after 3 consecutive failures.")
            return None
        except Exception as e:
            print(f"[STT] Google exception/timeout error: {e}")
            self._google_fail_count += 1
            if self._google_fail_count >= 3:
                self._online = False
                print("[STT] Google offline after 3 consecutive failures.")
            return None
        finally:
            socket.setdefaulttimeout(old_timeout)

    # ══════════════════════════════════════════════════════
    #  Vosk STT — يختار EN أو AR حسب اللغة
    # ══════════════════════════════════════════════════════

    def _vosk(self, audio, lang: str, names_mode: bool = False) -> str | None:
        # اختار الـ recognizer المناسب
        if lang == "ar" and self._vosk_ar_ready:
            rec = self._vosk_ar
            label = "AR"
        elif names_mode and self._vosk_en_names_ready:
            rec = self._vosk_en_names
            label = "EN-NAME"
        elif self._vosk_en_ready:
            rec = self._vosk_en
            label = "EN"
        else:
            print("[STT] Vosk not ready.")
            return None

        try:
            # Reset the recognizer state to clear any past audio context
            if hasattr(rec, "Reset"):
                rec.Reset()
                
            wav = audio.get_raw_data(convert_rate=16000, convert_width=2)
            rec.AcceptWaveform(wav)
            result = json.loads(rec.Result())
            text   = result.get("text", "").strip()
            if text:
                if not names_mode and _looks_like_vosk_noise(text):
                    print(f"[STT] Vosk {label} noise-like phrase ignored: '{text}'")
                    return None
                print(f"[STT] Vosk {label}: '{text}'")
                return text.lower()
            return None
        except Exception as e:
            logger.warning(f"Vosk: {e}")
            return None

    # ══════════════════════════════════════════════════════
    #  yes_no
    # ══════════════════════════════════════════════════════

    def yes_no(self, tries: int = 4, timeout: float = 8.0, tts=None) -> bool | None:
        import re
        yes_words = YES_EN | YES_AR
        no_words  = NO_EN  | NO_AR

        def _has_word(text_str, patterns):
            for pat in patterns:
                rx = r'(?<!\w)' + re.escape(pat) + r'(?!\w)'
                if re.search(rx, text_str, re.IGNORECASE):
                    return True
            return False

        for i in range(1, tries + 1):
            text = self.listen(timeout=timeout, phrase_limit=4.0, recal=(i > 1), tts=tts)
            is_ar = getattr(config, "LANGUAGE", "en") == "ar"
            if not text:
                if tts is not None and i < tries:
                    prompt = "لم أسمعك جيداً. من فضلك قل نعم أو لا." if is_ar else "I did not hear you. Please say yes or no."
                    tts.say_wait(prompt)
                continue
            t_clean = text.lower().strip()
            words = re.findall(r"[\w\u0600-\u06ff]+", t_clean)
            if len(words) > 3 or _looks_like_vosk_noise(t_clean):
                print(f"[STT] '{text}' not a clear yes/no — attempt {i}/{tries}")
                if tts is not None and i < tries:
                    prompt = "عذراً، قل نعم أو لا فقط." if is_ar else "Sorry, please say only yes or no."
                    tts.say_wait(prompt)
                continue
            # التحقق من النفي أولاً
            if _has_word(t_clean, no_words):
                print("[STT] NO")
                return False
            # التحقق من التأكيد ثانياً
            if _has_word(t_clean, yes_words):
                print("[STT] YES")
                return True
            print(f"[STT] '{text}' not yes/no — attempt {i}/{tries}")
            if tts is not None and i < tries:
                prompt = "عذراً، هل يمكنك قول نعم أو لا؟" if is_ar else "Sorry, could you say yes or no?"
                tts.say_wait(prompt)
        return None

    # ══════════════════════════════════════════════════════
    #  get_name — بينظف التكرار والكلمات التعريفية الزائدة
    # ══════════════════════════════════════════════════════

    def get_name(self, tries: int = 3, timeout: float = 9.0, tts=None) -> str | None:
        for i in range(1, tries + 1):
            text = self.listen(timeout=timeout, phrase_limit=6.0, recal=(i > 1), tts=tts, names_mode=True)
            is_ar = getattr(config, "LANGUAGE", "en") == "ar"
            if not text:
                if tts is not None and i < tries:
                    prompt = "لم أسمع الاسم جيداً. من فضلك أعد قول الاسم." if is_ar else "I did not hear the name. Please say the name again."
                    tts.say_wait(prompt)
                continue

            t = text.strip()
            t_lower = t.lower()

            # كلمات تعريفية شائعة للبدء قبل نطق الاسم
            prefixes_en = [
                "my name is", "his name is", "her name is", "this is", "it is",
                "register name", "register", "name is"
            ]
            prefixes_ar = [
                "اسمي هو", "اسمه هو", "اسمها هو", "الاسم هو", "اسمي", "اسمه", "اسمها",
                "هذا هو", "هذه هي", "هذا", "هذه", "ده", "دي", "سجل الاسم", "سجل", "سجلي", "الاسم"
            ]

            prefixes_ar += [
                "\u0627\u0633\u0645\u064a \u0647\u0648", "\u0627\u0633\u0645\u0647 \u0647\u0648", "\u0627\u0633\u0645\u0647\u0627 \u0647\u0648",
                "\u0627\u0644\u0627\u0633\u0645 \u0647\u0648", "\u0627\u0633\u0645\u064a", "\u0627\u0633\u0645\u0647\u0627", "\u0627\u0633\u0645\u0647",
                "\u0647\u0630\u0627 \u0647\u0648", "\u0647\u0630\u0647 \u0647\u064a", "\u0647\u0630\u0627", "\u0647\u0630\u0647",
                "\u062f\u0647", "\u062f\u064a", "\u0633\u062c\u0644 \u0627\u0644\u0627\u0633\u0645", "\u0633\u062c\u0644\u064a",
                "\u0633\u062c\u0644", "\u0627\u0644\u0627\u0633\u0645"
            ]

            stripped = False
            for p in sorted(prefixes_en, key=len, reverse=True):
                if t_lower.startswith(p):
                    t = t[len(p):].strip()
                    stripped = True
                    break

            if not stripped:
                for p in sorted(prefixes_ar, key=len, reverse=True):
                    if t_lower.startswith(p):
                        t = t[len(p):].strip()
                        break

            words = t.split()
            if not words:
                if tts is not None and i < tries:
                    prompt = "لم أسمع الاسم جيداً. من فضلك أعد قول الاسم." if is_ar else "I did not hear the name. Please say the name again."
                    tts.say_wait(prompt)
                continue

            # إزالة "is" إذا كانت الكلمة الأولى المتبقية (مثال: "name is john" -> تم مسح "name" وبقي "is john")
            if words[0].lower() == "is" and len(words) > 1:
                words = words[1:]

            # تنظيف التكرارات المتجاورة (مثل "احمد احمد" -> "احمد")
            deduped = []
            for w in words:
                if not deduped or w.lower() != deduped[-1].lower():
                    deduped.append(w)
            words = deduped

            # أخذ أول كلمتين فقط للاسم
            name = " ".join(words[:3]).strip()
            if not is_ar and _contains_arabic(name):
                name = _arabic_name_to_latin(name)
            name = name.title()

            if _looks_like_bad_name(name):
                print(f"[STT] Weak name candidate '{name}' — retrying.")
                if tts is not None and i < tries:
                    prompt = "I heard only part of the name. Please say the full name clearly." if not is_ar else "سمعت جزءاً من الاسم فقط. من فضلك قل الاسم كاملاً بوضوح."
                    tts.say_wait(prompt)
                continue

            if len(name) >= 2:
                print(f"[STT] Name: '{name}'")
                return name
            print(f"[STT] Name too short — attempt {i}/{tries}")
            if tts is not None and i < tries:
                prompt = "الاسم قصير جداً، يرجى إعادة نطق الاسم بوضوح." if is_ar else "The name is too short. Please say the name clearly again."
                tts.say_wait(prompt)
        return None
