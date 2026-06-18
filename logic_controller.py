"""
logic_controller.py — v8 Updated
================================
1. السيستم صامت تماماً حتى يسمع wake word
2. بعد wake word → session مفتوحة، أوامر مباشرة بدون "vision" تاني
3. session بتقفل بـ "close system / goodbye / وداعا / اغلق" إلخ أو بعد 20 ثانية خمول
4. أثناء أي أمر → لا إعلانات نهائياً
5. عربي/إنجليزي كامل وصحيح
"""

import time
import threading
import logging
import re
import difflib
import unicodedata
import config

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════
#  نصوص اللغتين
# ══════════════════════════════════════════════════════════════
_STRINGS = {
    "en": {
        "welcome":         "Vision system is ready. How can I help?",
        "goodbye":         "Vision system closed. Say start vision to activate again.",
        "no_command":      "I did not hear a command. Please try again.",
        "no_person":       "No person in front of the camera.",
        "already_reg":     "{name} is already registered.",
        "confirm_new_person": "I think this is {name}. Is this a new person? Say yes or no.",
        "cannot_block":    "Cannot block a registered person. Use delete instead.",
        "unknown_emotion": "Unknown person, they look {emotion}.",
        "known_emotion":   "{name} looks {emotion}.",
        "known_unsure":    "I think this is {name}, they look {emotion}.",
        "no_registered":   "No registered persons.",
        "reg_list":        "Registered persons: {names}.",
        "quiet_on":        "Quiet mode on.",
        "quiet_off":       "Resuming announcements.",
        "not_recognized":  "Command not recognized. Please try again.",
        "low_light":       "Low light detected. Relying on audio analysis.",
        "lang_en":         "Switched to English.",
        "lang_ar":         "Switched to Arabic.",
        "voice_male_ar":   "Switched to Arabic male voice.",
        "voice_female_ar": "Switched to Arabic female voice.",
        "voice_male_en":   "Switched to English male voice.",
        "voice_female_en": "Switched to English female voice.",
        "session_timeout": "Going to standby due to inactivity.",
    },
    "ar": {
        "welcome":         "نظام الرؤية جاهز. كيف أساعدك؟",
        "goodbye":         "تم إغلاق النظام. قل ابدأ فيجن للتفعيل من جديد.",
        "no_command":      "لم أسمع أمراً. من فضلك حاول مرة أخرى.",
        "no_person":       "لا يوجد شخص أمام الكاميرا.",
        "already_reg":     "{name} مسجل بالفعل.",
        "confirm_new_person": "أظن أن هذا {name}. هل هذا شخص جديد؟ قل نعم أو لا.",
        "cannot_block":    "لا يمكن حظر شخص مسجل. استخدم أمر الحذف.",
        "unknown_emotion": "شخص غير معروف، يبدو {emotion}.",
        "known_emotion":   "{name} يبدو {emotion}.",
        "known_unsure":    "أظن أن هذا {name}، يبدو {emotion}.",
        "no_registered":   "لا يوجد أشخاص مسجلون.",
        "reg_list":        "الأشخاص المسجلون: {names}.",
        "quiet_on":        "تم تفعيل وضع الصمت.",
        "quiet_off":       "استئناف الإعلانات.",
        "not_recognized":  "الأمر غير معروف. من فضلك حاول مرة أخرى.",
        "low_light":       "الإضاءة منخفضة. سيتم الاعتماد على تحليل الصوت.",
        "lang_en":         "تم التبديل إلى الإنجليزية.",
        "lang_ar":         "تم التبديل إلى العربية.",
        "voice_male_ar":   "تم التبديل إلى صوت رجالي عربي.",
        "voice_female_ar": "تم التبديل إلى صوت نسائي عربي.",
        "voice_male_en":   "تم التبديل إلى صوت رجالي إنجليزي.",
        "voice_female_en": "تم التبديل إلى صوت نسائي إنجليزي.",
        "session_timeout": "تم الانتقال إلى وضع الاستعداد لعدم النشاط.",
    },
}

EMOTIONS_AR = {
    "Angry":    "غاضب",
    "Disgust":  "مشمئز",
    "Fear":     "خائف",
    "Happy":    "سعيد",
    "Neutral":  "طبيعي",
    "Sad":      "حزين",
    "Surprise": "متفاجئ",
}

# كلمات تفعيل الـ session
_WAKE_WORDS = [
    "start vision", "hi vision", "hey vision", "activate vision", "open vision", "vision",
    "ابدأ فيجن", "ابدا فيجن", "فيجن", "فيجين",
    "تفعيل", "مساعد", "بصر",
]

# كلمات إغلاق الـ session
_CLOSE_WORDS = [
    "close system", "goodbye", "good bye", "bye vision",
    "stop vision", "exit vision", "deactivate", "shutdown",
    "close vision", "exit",
    "اغلق", "أغلق", "وداعا", "وداعً", "مع السلامة",
    "اوقف", "أوقف", "انهي", "أنهي", "اقفل", "أقفل",
    "اغلق النظام", "اوقف النظام",
]

# أوامر اللغة
_AR_WORDS = ["arabic", "عربي", "بالعربي", "عربية", "غير للعربي",
             "switch to arabic", "كلمني عربي", "تحويل عربي"]
_EN_WORDS = ["english", "انجليزي", "إنجليزي", "بالانجليزي",
             "غير للانجليزي", "switch to english", "كلمني انجليزي"]

# أوامر التسجيل
_REG_WORDS   = ["register","save","add","enroll","record","new person","learn",
                "سجل","تسجيل","اضف","ضيف","احفظ","اعرفني","سجلني","اعرف"]
_DEL_WORDS   = ["delete","remove","erase","forget","clear","wipe","unregister",
                "احذف","امسح","شيل","ازيل","حذف","الغ التسجيل"]
_CLEAR_ALL_WORDS = ["clear all", "delete all", "wipe database", "wipe names",
                    "امسح الكل", "احذف الكل", "فرمتة الاسماء", "احذف جميع الاسماء", "حذف الكل"]
_BLOCK_WORDS = ["block","ban","blacklist","restrict",
                "احظر","حظر","امنع","منع","حجب","بلوك"]
_UNBLK_WORDS = ["unblock","allow","unlock","whitelist","remove block",
                "فك حظر","الغ الحظر","ارفع الحظر","سمح","اسمح"]
_WHO_WORDS   = ["who","identify","tell me","who is",
                "مين","عرفني","هو مين","من هو","من هذا"]
_LIST_WORDS  = ["list","names","show names","registered",
                "قائمة","الاسامي","مين مسجل","اسماء"]
_QUIET_WORDS = ["quiet","silence","mute","shut up",
                "اسكت","سكوت","كفاية","صمت","اصمت"]
_SPEAK_WORDS = ["speak","resume","unmute","continue",
                "اتكلم","كمل","استمر","تكلم","شغل الصوت"]

# أوامر تغيير جنس الصوت
_MALE_AR_WORDS   = [
    "صوت رجالي", "صوت راجل", "صوت ذكر", "صوت رجل", "صوت ولد", "صوت ذكوري",
    "رجالي", "راجل", "رجل", "ذكوري", "ذكر", "ولد", "تغيير لصوت رجالي",
    "male arabic", "arabic male", "arabic man", "man arabic", "arabic male voice", 
    "arabic man voice", "arabic boy", "boy arabic", "arabic guy", "guy arabic",
    "رجالي عربي", "راجل عربي", "رجل عربي", "ذكر عربي", "ولد عربي", "عربي رجالي", 
    "عربي راجل", "عربي ذكر", "صوت رجالي عربي", "صوت رجل عربي"
]
_FEMALE_AR_WORDS = [
    "صوت ستات", "صوت بنت", "صوت انثى", "صوت أنثى", "صوت نسائي", "صوت نسوي", "صوت بناتي",
    "نسائي", "نسوي", "ست", "بنت", "بناتي", "أنثى", "انثى", "تغيير لصوت نسائي",
    "female arabic", "arabic female", "arabic woman", "woman arabic", "arabic female voice", 
    "arabic woman voice", "arabic girl", "girl arabic", "arabic lady", "lady arabic",
    "نسائي عربي", "نسوي عربي", "بناتي عربي", "بنت عربي", "انثى عربي", "عربي نسائي", 
    "عربي بناتي", "عربي بنت", "صوت نسائي عربي", "صوت بنت عربي", "صوت انثى عربي"
]
_MALE_EN_WORDS   = [
    "male english", "english male", "male voice", "man voice", "boy voice", "guy voice", 
    "english man", "man english", "male", "man", "boy", "guy", "gentleman", "change to male", 
    "change to man", "switch to male", "switch to man", "english male voice", "english man voice",
    "صوت رجالي انجليزي", "صوت ذكر انجليزي", "صوت رجل انجليزي", "رجالي انجليزي", "رجل انجليزي", "ذكر انجليزي"
]
_FEMALE_EN_WORDS = [
    "female english", "english female", "female voice", "woman voice", "girl voice", "lady voice", 
    "english woman", "woman english", "english girl", "female", "woman", "girl", "lady", 
    "change to female", "change to woman", "switch to female", "switch to woman", "english female voice", 
    "english woman voice", "english girl voice",
    "صوت نسائي انجليزي", "صوت انثى انجليزي", "صوت بنت انجليزي", "نسائي انجليزي", "بنت انجليزي", "انثى انجليزي"
]


# Final controlled voice-command set. These override the older broad lists above.
_WAKE_WORDS = ["start vision", "vision", "ابدأ فيجن", "ابدا فيجن", "فيجن", "فيجين"]
_CLOSE_WORDS = ["close vision", "goodbye", "bye vision", "اغلق", "أغلق", "اقفل", "أقفل", "مع السلامة"]
_AUTO_PAUSE_WORDS = ["standby", "pause", "هدوء", "استنى"]
_AUTO_RESUME_WORDS = ["resume", "continue", "تابع", "كمل"]
_AR_WORDS = ["arabic", "switch to arabic", "عربي"]
_EN_WORDS = ["english", "switch to english", "انجليزي", "إنجليزي"]
_REG_WORDS = ["register", "add person", "save person", "new person", "register new person", "سجل", "ضيف شخص", "احفظ الشخص", "شخص جديد", "سجل شخص جديد"]
_IMPROVE_WORDS = [
    "improve person", "improved person", "update person",
    "improve registration", "improved registration", "update registration",
    "حسن التسجيل", "حدث التسجيل", "حسن الشخص"
]
_DEL_WORDS = ["delete", "del", "remove", "delete person", "remove person", "delete number", "احذف", "امسح", "احذف شخص", "امسح شخص", "احذف رقم"]
_CLEAR_ALL_WORDS = ["delete all", "delete all names", "امسح الكل", "احذف كل الاسماء", "احذف كل الأسماء"]
_BLOCK_WORDS = ["block", "block person", "احظر", "احظر الشخص"]
_UNBLK_WORDS = ["unblock", "unblock person", "فك حظر", "ارفع الحظر"]
_WHO_WORDS = ["who is this", "identify", "مين ده", "عرفني", "من هذا"]
_LIST_WORDS = ["list names", "show names", "registered names", "اسماء", "أسماء", "مين مسجل", "اعرض الاسماء", "اعرض الأسماء"]
_QUIET_WORDS = ["quiet", "mute", "silence", "اسكت", "صمت"]
_SPEAK_WORDS = ["unmute", "شغل الصوت"]
_MALE_AR_WORDS = ["arabic male voice", "صوت رجالي عربي"]
_FEMALE_AR_WORDS = ["arabic female voice", "صوت نسائي عربي"]
_MALE_EN_WORDS = ["english male voice", "صوت رجالي انجليزي", "صوت رجالي إنجليزي"]
_FEMALE_EN_WORDS = ["english female voice", "صوت نسائي انجليزي", "صوت نسائي إنجليزي"]


class LogicController:

    def __init__(self, tts, stt, reg_flow, face_processor, face_db):
        self.tts  = tts
        self.stt  = stt
        self.reg  = reg_flow
        self.proc = face_processor
        self.db   = face_db

        self._last_announced  = {}
        self._last_seen       = {}
        self._last_emotion    = {}
        self._emotion_candidate = {}

        self._current_name    = None
        self._current_emotion = None

        self._announce_queue  = []
        self._announcing      = False
        self._auto_announce_enabled = True
        self._low_light_warned = False

        # ── بفر تأكيد وجود الشخص ────────────────────────────────────────────
        self._presence_buf: dict = {}    # { name: deque([True/False, ...]) }
        self._presence_n   = 6          # حجم البفر
        self._presence_min = 4          # تأكيد أسرع مع حماية كافية

        # ── حالة النظام ──────────────────────────────────────────────────────
        self._session_active      = False
        self._command_in_progress = False
        self._last_command_time   = time.time()  # لتتبع وقت عدم النشاط

        # نزلنا من 5.0 ل→ 1.0 ثانية — السيستم جاهز للأوامر تقريباً فوراً بعد التشغيل
        threading.Timer(1.0, self._start_listener).start()
        print("      Logic Controller ready.")

    # ══════════════════════════════════════════════════════════════
    #  مساعدات اللغة
    # ══════════════════════════════════════════════════════════════

    def _lang(self) -> str:
        return getattr(config, "LANGUAGE", "en")

    def _t(self, key: str, **kwargs) -> str:
        lang = self._lang()
        text = _STRINGS.get(lang, _STRINGS["en"]).get(key, key)
        if kwargs:
            text = text.format(**kwargs)
        return text

    def _emotion_str(self, emotion: str) -> str:
        if self._lang() == "ar":
            return EMOTIONS_AR.get(emotion, emotion)
        return emotion

    def _normalize_command(self, text: str) -> str:
        t = unicodedata.normalize("NFKC", str(text or "")).lower().strip()
        t = re.sub(r"[\u064b-\u065f\u0670\u0640]", "", t)
        t = t.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789"))
        for src, dst in {
            "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
            "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي",
        }.items():
            t = t.replace(src, dst)
        t = re.sub(r"[^\w\s\u0600-\u06ff]", " ", t)
        return re.sub(r"\s+", " ", t).strip()

    def _similar_enough(self, text: str, pattern: str) -> bool:
        t = self._normalize_command(text)
        p = self._normalize_command(pattern)
        if not t or not p:
            return False
        if t == p:
            return True
        if len(p) <= 3 or len(t) <= 3:
            return difflib.SequenceMatcher(None, t, p).ratio() >= 0.85

        def has_marker(value: str, markers: tuple[str, ...]) -> bool:
            for marker in markers:
                m = self._normalize_command(marker)
                if re.fullmatch(r"[a-z0-9_]+", m):
                    if re.search(rf"\b{re.escape(m)}\b", value):
                        return True
                elif m in value:
                    return True
            return False

        protected_groups = (
            (("mute",), ("unmute",)),
            (("block", "احظر"), ("unblock", "فك", "ارفع", "رفع")),
            (("save", "احفظ", "حفظ"), ("block", "احظر", "حظر")),
            (("male", "رجالي", "راجل", "رجل"), ("female", "نسائي", "بنت", "انثي", "انثى")),
        )
        for left_group, right_group in protected_groups:
            if (
                has_marker(t, left_group) and has_marker(p, right_group)
                or has_marker(t, right_group) and has_marker(p, left_group)
            ):
                return False

        if difflib.SequenceMatcher(None, t, p).ratio() >= 0.84:
            return True

        t_words = t.split()
        p_words = p.split()
        if len(p_words) == 1:
            return any(difflib.SequenceMatcher(None, word, p).ratio() >= 0.84 for word in t_words)

        if len(t_words) >= len(p_words):
            for i in range(0, len(t_words) - len(p_words) + 1):
                window = " ".join(t_words[i:i + len(p_words)])
                if difflib.SequenceMatcher(None, window, p).ratio() >= 0.84:
                    return True
        return False

    def _has_command(self, text: str, command_list: list) -> bool:
        """يتحقق ما إذا كانت الكلمة/الجملة موجودة كأمر كامل وليس كجزء من كلمة أخرى."""
        for pattern in command_list:
            regex = r'(?<!\w)' + re.escape(pattern) + r'(?!\w)'
            if re.search(regex, text, re.IGNORECASE):
                return True
        for pattern in command_list:
            if self._similar_enough(text, pattern):
                logger.debug("[Logic] Fuzzy command match: %r ~= %r", text, pattern)
                return True
        return False

    # ══════════════════════════════════════════════════════════════
    #  طابور الإعلانات
    # ══════════════════════════════════════════════════════════════

    def _queue_announcement(self, msg: str):
        """لا يضيف أي إعلان لو النظام نائم أو في وسط أمر."""
        if not self._session_active:
            return
        if not self._auto_announce_enabled:
            return
        if self._command_in_progress or self.reg.active:
            return
        if self._announce_queue and self._announce_queue[-1] == msg:
            return
        # Keep only the newest automatic announcement so TTS cannot build a backlog.
        self._announce_queue[:] = [msg]
        if not self._announcing:
            threading.Thread(target=self._flush_queue, daemon=True).start()

    def _flush_queue(self):
        self._announcing = True
        while self._announce_queue:
            if self._command_in_progress or self.reg.active or not self._session_active:
                self._announce_queue.clear()
                break
            if self.tts.busy():
                time.sleep(0.2)
                continue
            msg = self._announce_queue.pop(0)
            self.tts.say(msg)
            time.sleep(0.3)
            self.tts.wait(timeout=10.0)
        self._announcing = False

    # ══════════════════════════════════════════════════════════════
    #  الـ Listener الرئيسي
    # ══════════════════════════════════════════════════════════════

    def _start_listener(self):
        def _loop():
            while True:
                try:
                    if self._session_active:
                        self._handle_session()
                    else:
                        self._wait_for_wake_word()
                except Exception as e:
                    logger.debug(f"Listener: {e}")
                    time.sleep(0.5)
        threading.Thread(target=_loop, daemon=True).start()

    def _strip_wake_word(self, text: str) -> str:
        """يستخرج كلمة التفعيل من بداية أو وسط الجملة ويرجع باقي الجملة كأمر."""
        t = text.lower().strip()
        for pattern in _WAKE_WORDS:
            regex = r'(?<!\w)' + re.escape(pattern) + r'(?!\w)'
            # استبدال أول تطابق بمسافة ثم تنظيف الفراغات
            t_new, count = re.subn(regex, "", t, count=1)
            if count > 0:
                return t_new.strip()
        words = t.split()
        for pattern in sorted(_WAKE_WORDS, key=lambda p: len(p.split()), reverse=True):
            p_words = pattern.lower().split()
            if len(words) < len(p_words):
                continue
            prefix = " ".join(words[:len(p_words)])
            if self._similar_enough(prefix, pattern):
                return " ".join(words[len(p_words):]).strip()
        return t

    def _wait_for_wake_word(self):
        """ينتظر wake word فقط — النظام صامت تماماً."""
        text = self.stt.listen(timeout=5.0, phrase_limit=5.0, tts=self.tts)
        if not text:
            return
        t = text.lower().strip()
        if self._has_command(t, _WAKE_WORDS):
            self._command_in_progress = True
            self._announce_queue.clear()
            self.tts.stop()
            
            # استخراج الأمر المصاحب لكلمة التفعيل (مثل: "فيجن مين ده")
            cmd = self._strip_wake_word(t)
            if cmd:
                # يوجد أمر مصاحب، نقوم بتنفيذه مباشرة ونفعل الجلسة
                self._session_active = True
                logger.info(f"[Logic] Waking up with one-shot command: '{cmd}'")
                try:
                    self._handle_command(cmd)
                except Exception as e:
                    logger.error(f"Command execution error: {e}")
                self._command_in_progress = False
            else:
                # قيلت كلمة التفعيل بمفردها، نفتح الجلسة
                self._session_active = True
                self.tts.say_wait(self._t("welcome"), pause=0.15)
                self._command_in_progress = False

    def _handle_session(self):
        """الجلسة مفعلة — نعلن التعابير والأسماء، ونستقبل الأوامر المسبوقة بكلمة التفعيل لمنع الأخطاء."""
        if self.reg.active or self.tts.busy():
            time.sleep(0.3)
            return

        text = self.stt.listen(timeout=5.0, phrase_limit=6.0, tts=self.tts)
        if not text:
            return

        t = text.lower().strip()
        
        # إغلاق الـ session صراحة (وداعا / اغلق) - نسمح بها بكلمة تفعيل أو بدونها للسهولة
        if self._has_command(t, _CLOSE_WORDS):
            self._command_in_progress = True
            self._session_active = False
            self._announce_queue.clear()
            self.tts.stop()
            self.tts.say_wait(self._t("goodbye"), pause=0.15)
            self._command_in_progress = False
            return

        # للتأكد من أن الكلام موجه للنظام كأمر، يجب أن يحتوي على كلمة التفعيل (فيجن/vision)
        if not self._has_command(t, _WAKE_WORDS):
            # ليس أمراً موحداً بالمناداة، نتجاهله ككلام خلفية
            return

        cmd = self._strip_wake_word(t)
        if not cmd:
            # نطق كلمة التفعيل فقط، نرحب به مجدداً
            self.tts.say_wait(self._t("welcome"), pause=0.15)
            return

        # تنفيذ الأمر
        self._command_in_progress = True
        self._announce_queue.clear()
        self.tts.stop()
        try:
            self._handle_command(cmd)
        except Exception as e:
            logger.error(f"Command error: {e}")
        finally:
            self._command_in_progress = False
            # الجلسة تظل مفعلة ليستمر النظام في إعلان الوجوه والمشاعر


    # ══════════════════════════════════════════════════════════════
    #  معالج الأوامر
    # ══════════════════════════════════════════════════════════════

    def _handle_command(self, text: str):
        # لو المستخدم نطق الـ wake word وهي الجلسة مفعلة أصلاً، نرحب بيه تاني بس
        if self._has_command(text, _WAKE_WORDS):
            self.tts.say_wait(self._t("welcome"), pause=0.15)
            return

        # Determine target language from command content to prevent substring/word boundary conflicts
        is_ar_cmd = self._has_command(text, ["arabic", "عربي", "بالعربي", "عربية", "تحويل عربي", "كلمني عربي"])
        is_en_cmd = self._has_command(text, ["english", "انجليزي", "إنجليزي", "بالانجليزي", "تحويل انجليزي", "كلمني انجليزي"])

        # ── تغيير جنس الصوت ──────────────────────────────────────────────────
        if self._has_command(text, _AUTO_PAUSE_WORDS):
            self._auto_announce_enabled = False
            self._announce_queue.clear()
            msg = "تم إيقاف قراءة الأشخاص والمشاعر." if self._lang() == "ar" else "Automatic person and emotion reading paused."
            self.tts.say_wait(msg, pause=0.15)
            return

        if self._has_command(text, _AUTO_RESUME_WORDS):
            self._auto_announce_enabled = True
            msg = "تم تشغيل قراءة الأشخاص والمشاعر." if self._lang() == "ar" else "Automatic person and emotion reading resumed."
            self.tts.say_wait(msg, pause=0.15)
            return

        if self._has_command(text, _MALE_AR_WORDS) and not is_en_cmd:
            if hasattr(self.tts, "set_voice"):
                self.tts.set_voice("ar", "male")
            self.tts.say_wait(self._t("voice_male_ar"))
            return

        if self._has_command(text, _FEMALE_AR_WORDS) and not is_en_cmd:
            if hasattr(self.tts, "set_voice"):
                self.tts.set_voice("ar", "female")
            self.tts.say_wait(self._t("voice_female_ar"))
            return

        if self._has_command(text, _MALE_EN_WORDS) and not is_ar_cmd:
            if hasattr(self.tts, "set_voice"):
                self.tts.set_voice("en", "male")
            self.tts.say_wait(self._t("voice_male_en"))
            return

        if self._has_command(text, _FEMALE_EN_WORDS) and not is_ar_cmd:
            if hasattr(self.tts, "set_voice"):
                self.tts.set_voice("en", "female")
            self.tts.say_wait(self._t("voice_female_en"))
            return

        # ── تبديل اللغة ──────────────────────────────────────────────────────
        if self._has_command(text, _AR_WORDS):
            config.LANGUAGE = "ar"
            if hasattr(self.tts, "set_language"):
                self.tts.set_language("ar")
            self.tts.say_wait(self._t("lang_ar"), pause=0.15)
            return
        if self._has_command(text, _EN_WORDS):
            config.LANGUAGE = "en"
            if hasattr(self.tts, "set_language"):
                self.tts.set_language("en")
            self.tts.say_wait(self._t("lang_en"), pause=0.15)
            return

        # ── تسجيل ────────────────────────────────────────────────────────────
        if self._has_command(text, _IMPROVE_WORDS):
            names = [n for n in self.db.names() if not n.startswith("__blocked__")]
            if not names:
                self.tts.say_wait(self._t("no_registered"))
            elif self._current_name and self._current_name != "Unknown":
                self.reg.start_improve(self._current_name)
            else:
                self.reg.start_improve()
            return

        if self._has_command(text, _REG_WORDS):
            if self._current_name is None:
                self.tts.say_wait(self._t("no_person"))
            elif self._current_name != "Unknown":
                self.tts.say_wait(self._t("confirm_new_person", name=self._current_name), pause=0.15)
                if self.stt.yes_no(tries=4, timeout=6.0, tts=self.tts) is True:
                    self.reg.start_register()
                else:
                    self.tts.say_wait(self._t("already_reg", name=self._current_name))
            else:
                self.reg.start_register()
            return

        # ── رفع حظر ──────────────────────────────────────────────────────
        if self._has_command(text, _UNBLK_WORDS):
            if self._lang() == "ar":
                self.tts.say_wait("هل تريد رفع الحظر؟ قل نعم للتأكيد.", pause=0.15)
            else:
                self.tts.say_wait("Unblock a person? Say yes to confirm.", pause=0.15)
            if self.stt.yes_no(tries=4, timeout=6.0, tts=self.tts) is True:
                self.reg.start_unblock()
            return

        # ── حظر ──────────────────────────────────────────────────────
        if self._has_command(text, _BLOCK_WORDS):
            if self._current_name is None:
                self.tts.say_wait(self._t("no_person"))
            elif self._current_name != "Unknown":
                self.tts.say_wait(self._t("cannot_block"))
            else:
                if self._lang() == "ar":
                    self.tts.say_wait("هل تريد حظر هذا الشخص؟ قل نعم للتأكيد.", pause=0.15)
                else:
                    self.tts.say_wait("Block this person? Say yes to confirm.", pause=0.15)
                if self.stt.yes_no(tries=4, timeout=6.0, tts=self.tts) is True:
                    self.reg.start_block()
            return

        # ── من هذا ───────────────────────────────────────────────────────────
        if self._has_command(text, _WHO_WORDS):
            emo = self._emotion_str(self._current_emotion or "Neutral")
            if self._current_name is None or self._current_name == "Unknown":
                self.tts.say_wait(self._t("unknown_emotion", emotion=emo))
            else:
                self.tts.say_wait(self._t("known_emotion",
                                          name=self._current_name, emotion=emo))
            return

        # ── مسح جميع الأسماء ──────────────────────────────────────────────────
        if self._has_command(text, _CLEAR_ALL_WORDS):
            if self._lang() == "ar":
                self.tts.say_wait("هل أنت متأكد تماماً من رغبتك في حذف جميع الأسماء المسجلة؟ قل نعم للتأكيد.", pause=0.15)
            else:
                self.tts.say_wait("Are you absolutely sure you want to delete all registered names? Say yes to confirm.", pause=0.15)
            
            if self.stt.yes_no(tries=4, timeout=6.0, tts=self.tts) is True:
                normal_names = [n for n in self.db.names() if not n.startswith("__blocked__")]
                for name in normal_names:
                    self.db.delete(name)
                    self.on_deleted(name)
                
                if self._lang() == "ar":
                    self.tts.say_wait("تم حذف جميع الأسماء بنجاح.")
                else:
                    self.tts.say_wait("All registered names have been successfully deleted.")
            return

        # ── حذف ──────────────────────────────────────────────────────────────
        if self._has_command(text, _DEL_WORDS):
            if self._lang() == "ar":
                self.tts.say_wait("هل تريد حذف شخص متسجل؟ قل نعم للتأكيد.", pause=0.15)
            else:
                self.tts.say_wait("Delete a registered person? Say yes to confirm.", pause=0.15)
            if self.stt.yes_no(tries=4, timeout=6.0, tts=self.tts) is True:
                self.reg.start_delete()
            return

        # ── قائمة ────────────────────────────────────────────────────────────
        if self._has_command(text, _LIST_WORDS):
            names = [n for n in self.db.names() if not n.startswith("__blocked__")]
            if names:
                numbered_list = [f"{i+1} {name}" for i, name in enumerate(names)]
                self.tts.say_wait(self._t("reg_list", names="، ".join(numbered_list)
                                           if self._lang() == "ar" else ", ".join(numbered_list)))
            else:
                self.tts.say_wait(self._t("no_registered"))
            return

        # ── صمت ──────────────────────────────────────────────────────────────
        if self._has_command(text, _QUIET_WORDS):
            self._announce_queue.clear()
            self.tts.set_quiet(True)
            self.tts.say_wait(self._t("quiet_on"))
            return

        # ── استئناف ──────────────────────────────────────────────────────────
        if self._has_command(text, _SPEAK_WORDS):
            self.tts.set_quiet(False)
            self.tts.say_wait(self._t("quiet_off"))
            return

        self.tts.say_wait(self._t("not_recognized"))

    # ══════════════════════════════════════════════════════════════
    #  معالجة الوجوه (الحلقة الرئيسية)
    # ══════════════════════════════════════════════════════════════

    def process_faces(self, faces_data: list, brightness: float, frame=None) -> str:
        now = time.time()
        # تحذير الإضاءة — مرة واحدة فقط
        if brightness < config.BRIGHTNESS_THRESHOLD and not self._low_light_warned:
            self._low_light_warned = True
            self._queue_announcement(self._t("low_light"))

        if not faces_data:
            self._current_name    = None
            self._current_emotion = None
            # سجّل غياب كل الأشخاص في بفر الوجود
            for name in list(self._presence_buf.keys()):
                self._record_presence(name, False)
            return "no_face"

        # سجّل الأشخاص الموجودين والغائبين
        present_names = {fd[1] for fd in faces_data
                         if not fd[1].startswith("__blocked__") and fd[1] != "Unknown"}
        for name in list(self._presence_buf.keys()):
            self._record_presence(name, name in present_names)
        for name in present_names:
            if name not in self._presence_buf:
                self._record_presence(name, True)

        self._current_name    = faces_data[0][1]
        self._current_emotion = faces_data[0][3]

        # لو النظام نائم أو في وسط أمر → لا إعلانات
        if not self._session_active or self._command_in_progress or self.reg.active:
            return "silent"

        for face_id, name, rec_score, emotion, emo_conf, box_area in faces_data:
            if name.startswith("__blocked__"):
                continue
            if name != "Unknown":
                # تحقق إن الشخص ده فعلاً موجود قدام الكاميرا
                if self._is_person_confirmed(name):
                    self._process_known(name, rec_score, emotion, now)
            else:
                self._process_unknown(face_id, emotion, now)

        return "processed"

    def process(self, face_id, name, recognition_score, emotion,
                emotion_confidence, brightness, frame=None):
        return self.process_faces(
            [(face_id, name, recognition_score, emotion, emotion_confidence, 1)],
            brightness, frame
        )

    # ══════════════════════════════════════════════════════════════
    #  معالجة الأشخاص
    # ══════════════════════════════════════════════════════════════

    def _record_presence(self, name: str, present: bool):
        """يسجّل ظهور أو غياب الشخص في بفر الوجود."""
        from collections import deque
        if name not in self._presence_buf:
            self._presence_buf[name] = deque(maxlen=self._presence_n)
        self._presence_buf[name].append(present)

    def _is_person_confirmed(self, name: str) -> bool:
        """
        يتحقق إن الشخص موجود فعلاً — لازم يكون ظاهر
        في self._presence_min من آخر self._presence_n فريمات.
        """
        buf = self._presence_buf.get(name)
        if buf is None or len(buf) < self._presence_n:
            return False
        return sum(buf) >= self._presence_min

    def _emotion_is_stable_for_announcement(self, key: str, emotion: str) -> bool:
        last, count = self._emotion_candidate.get(key, ("", 0))
        if emotion == last:
            count += 1
        else:
            last, count = emotion, 1
        self._emotion_candidate[key] = (last, count)
        needed = getattr(config, "ANNOUNCE_EMOTION_STABLE_COUNT", 3)
        return count >= needed

    def _process_known(self, name, score, emotion, now):
        last_seen     = self._last_seen.get(name, 0)
        just_returned = (now - last_seen) > config.UNKNOWN_REASK_TIMEOUT
        self._last_seen[name] = now

        last_announced = self._last_announced.get(name, 0)
        last_emotion   = self._last_emotion.get(name, "")
        emotion_changed = (emotion != last_emotion)

        if not just_returned and not emotion_changed:
            return

        if not self._emotion_is_stable_for_announcement(name, emotion):
            return

        elapsed = now - last_announced

        change_cooldown = getattr(config, "EMOTION_CHANGE_COOLDOWN", 0.8)
        std_cooldown    = config.TTS_COOLDOWN_SEC
        effective_cooldown = change_cooldown if emotion_changed else std_cooldown

        cooldown_passed = elapsed >= effective_cooldown

        if just_returned or (emotion_changed and cooldown_passed):
            self._last_announced[name] = now
            self._last_emotion[name] = emotion
            emo = self._emotion_str(emotion)
            if score >= 0.75:
                msg = self._t("known_emotion", name=name, emotion=emo)
            else:
                msg = self._t("known_unsure", name=name, emotion=emo)
            self._queue_announcement(msg)

    def _process_unknown(self, face_id, emotion, now):
        recent_known = [
            seen_at for name, seen_at in self._last_seen.items()
            if name != "unknown"
        ]
        suppress_for = getattr(config, "KNOWN_PERSON_UNKNOWN_SUPPRESS_SEC", 0.0)
        if recent_known and (now - max(recent_known)) < suppress_for:
            return

        key             = "unknown"
        last_announced  = self._last_announced.get(key, 0)
        last_emotion    = self._last_emotion.get(key, "")
        emotion_changed = (emotion != last_emotion)
        if emotion_changed:
            effective_cooldown = getattr(config, "EMOTION_CHANGE_COOLDOWN", 0.8)
        else:
            effective_cooldown = getattr(config, "UNKNOWN_ANNOUNCE_COOLDOWN", 20.0)
        cooldown_passed = (now - last_announced) >= effective_cooldown

        if emotion_changed and cooldown_passed and self._emotion_is_stable_for_announcement(key, emotion):
            self._last_announced[key] = now
            self._last_emotion[key]   = emotion
            self._queue_announcement(
                self._t("unknown_emotion", emotion=self._emotion_str(emotion))
            )

    # ══════════════════════════════════════════════════════════════
    #  Callbacks
    # ══════════════════════════════════════════════════════════════

    def on_person_left(self, name):
        self._last_announced.pop(name, None)
        self._last_emotion.pop(name, None)
        self._emotion_candidate.pop(name, None)

    def on_registered(self, name):
        emotion = self._emotion_str(self._current_emotion or "Neutral")
        self._announce_queue.clear()
        self._queue_announcement(self._t("known_emotion", name=name, emotion=emotion))
        t = time.time()
        self._last_announced[name] = t
        self._last_seen[name]      = t
        self._last_emotion[name]   = self._current_emotion or "Neutral"

    def on_deleted(self, name: str):
        """
        بعد حذف شخص — امسح كل بياناته من الـ memory فوراً.
        """
        self._last_announced.pop(name, None)
        self._last_seen.pop(name, None)
        self._last_emotion.pop(name, None)
        self._emotion_candidate.pop(name, None)
        self._presence_buf.pop(name, None)
        self._announce_queue = [
            m for m in self._announce_queue if name not in m
        ]
        logger.info(f"[Logic] Cleared all memory for deleted person: '{name}'")

    def on_all_deleted(self):
        """
        بعد حذف جميع الأشخاص — امسح الذاكرة بالكامل فوراً.
        """
        self._last_announced.clear()
        self._last_seen.clear()
        self._last_emotion.clear()
        self._emotion_candidate.clear()
        self._presence_buf.clear()
        self._announce_queue.clear()
        logger.info("[Logic] Cleared all memory for all deleted persons.")
