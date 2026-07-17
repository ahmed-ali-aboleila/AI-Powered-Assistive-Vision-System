"""
shared/tts.py — v8
===================
- set_language(lang) → يغير الصوت فوراً للعربي أو الإنجليزي
- Edge TTS Neural: ar-EG-SalmaNeural / en-US-AriaNeural
- Fallback: SAPI → pyttsx3
- MP3 cache للجمل المتكررة
"""
import threading, queue, time, logging, os, asyncio, hashlib, sys, subprocess
import config

logger = logging.getLogger(__name__)
_STOP  = object()

VOICES = {
    ("ar", "female"): "ar-EG-SalmaNeural",
    ("ar", "male"):   "ar-EG-ShakirNeural",
    ("en", "female"): "en-US-AriaNeural",
    ("en", "male"):   "en-US-GuyNeural",
}

# الصوت الافتراضي لكل لغة
VOICES_DEFAULT = {
    "ar": ("ar", "female"),
    "en": ("en", "female"),
}

CACHE_DIR = "tts_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


class TTS:
    def __init__(self, rate: int = 150):
        self._q      = queue.Queue()
        self._done   = threading.Event()
        self._done.set()
        self._rate   = rate
        self._ready  = threading.Event()
        self._quiet  = False
        self._mixer_lock = threading.Lock()

        # اللغة والجنس الحاليين
        self._lang   = getattr(config, "LANGUAGE", "en")
        self._gender = "female"
        self._voice  = VOICES[VOICES_DEFAULT[self._lang]]

        # Edge TTS متاح؟
        self._edge_ok = False
        self._pygame_ok = False
        self._check_edge()

        # SAPI fallback
        self._sapi_speaker = None

        t = threading.Thread(target=self._worker, daemon=True)
        t.start()
        self._ready.wait(timeout=10)

    def _check_edge(self):
        try:
            import edge_tts
            import pygame
            pygame.mixer.init()
            self._edge_ok   = True
            self._pygame_ok = True
        except Exception:
            self._edge_ok = False

    # ══════════════════════════════════════════════════════
    #  Public API
    # ══════════════════════════════════════════════════════

    def set_language(self, lang: str):
        """يغير لغة الصوت مع الاحتفاظ بالجنس الحالي."""
        self._lang  = lang
        key = (lang, self._gender)
        self._voice = VOICES.get(key, VOICES[VOICES_DEFAULT.get(lang, ("en","female"))])
        print(f"[TTS] Voice → {self._voice}")

    def set_voice(self, lang: str, gender: str):
        """يغير لغة الصوت وجنسه معاً."""
        self._lang   = lang
        self._gender = gender
        config.LANGUAGE = lang
        key = (lang, gender)
        self._voice = VOICES.get(key, VOICES[("en", "female")])
        print(f"[TTS] Voice → {self._voice}")

    def say(self, text: str):
        """غير blocking — بيتخطى لو quiet mode."""
        if self._quiet:
            print(f"[TTS-QUIET] {text}")
            return
        print(f"[TTS] {text}")
        self._done.clear()
        self._q.put(text)

    def say_wait(self, text: str, pause: float = 0.05):
        """Blocking — بيشتغل حتى في quiet mode (رسائل النظام)."""
        print(f"[TTS] {text}")
        self._done.clear()
        self._q.put(text)
        self._done.wait(timeout=30)
        time.sleep(max(0.0, pause))

    def stop(self):
        while not self._q.empty():
            try: self._q.get_nowait()
            except: pass
        self._done.set()
        if self._pygame_ok:
            try:
                import pygame
                with self._mixer_lock:
                    pygame.mixer.music.stop()
            except Exception:
                pass

    def set_quiet(self, quiet: bool):
        self._quiet = quiet
        if quiet:
            self.stop()
        print(f"[TTS] Quiet={'ON' if quiet else 'OFF'}")

    def is_quiet(self) -> bool:
        return self._quiet

    def wait(self, timeout: float = 15.0):
        self._done.wait(timeout=timeout)

    def busy(self) -> bool:
        return not self._done.is_set()

    # ══════════════════════════════════════════════════════
    #  Worker
    # ══════════════════════════════════════════════════════

    def _worker(self):
        self._init_sapi()
        self._ready.set()

        while True:
            try:
                text = self._q.get(timeout=0.1)
            except queue.Empty:
                self._done.set()
                continue

            if text is _STOP:
                break

            try:
                self._speak(text)
            except Exception as e:
                logger.warning(f"[TTS] speak error: {e}")

            if self._q.empty():
                self._done.set()

    def _speak(self, text: str):
        # Edge TTS أولاً
        if self._edge_ok:
            if self._speak_edge(text):
                return
        # SAPI fallback (Windows only)
        if self._sapi_speaker:
            self._speak_sapi(text)
            return
        # espeak fallback (Linux / Raspberry Pi)
        if sys.platform != 'win32':
            self._speak_espeak(text)
            return
        # print فقط
        print(f"[TTS-PRINT] {text}")

    # ══════════════════════════════════════════════════════
    #  Edge TTS
    # ══════════════════════════════════════════════════════

    def _speak_edge(self, text: str) -> bool:
        try:
            import pygame
            import edge_tts

            # cache key
            key  = hashlib.md5(f"{self._voice}_{text}".encode()).hexdigest()
            path = os.path.join(CACHE_DIR, f"{key}.mp3")

            # Check if file exists and has size > 0 (prevents loading corrupted/empty cache files)
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                if os.path.exists(path):
                    try: os.remove(path)
                    except: pass
                # توليد الملف
                ok = self._edge_generate(text, path)
                if not ok:
                    if os.path.exists(path):
                        try: os.remove(path)
                        except: pass
                    return False

            # تشغيل الملف
            with self._mixer_lock:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
            
            while True:
                with self._mixer_lock:
                    is_busy = pygame.mixer.music.get_busy()
                if not is_busy:
                    break
                time.sleep(0.05)
            return True

        except Exception as e:
            print(f"[TTS] Edge TTS error: {e}")
            return False

    def _edge_generate(self, text: str, path: str) -> bool:
        """يولد ملف MP3 من Edge TTS مع timeout 5 ثواني."""
        import edge_tts

        result = [False]

        async def _gen():
            try:
                comm = edge_tts.Communicate(text, self._voice)
                await comm.save(path)
                result[0] = True
            except Exception as e:
                print(f"[TTS] Edge generate error: {e}")

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_gen())
            loop.close()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=5.0)

        if not result[0]:
            print("[TTS] Edge TTS timeout — falling back to SAPI")
            return False
        return True

    # ══════════════════════════════════════════════════════
    #  SAPI
    # ══════════════════════════════════════════════════════

    def _init_sapi(self):
        if sys.platform != 'win32':
            self._sapi_speaker = None
            return
        try:
            import pythoncom
            pythoncom.CoInitialize()
            import win32com.client
            self._sapi_speaker = win32com.client.Dispatch("SAPI.SpVoice")
            sapi_rate = max(-5, min(5, int((self._rate - 150) / 20)))
            self._sapi_speaker.Rate = sapi_rate
            print(f"[TTS] SAPI ready")
        except Exception as e:
            logger.warning(f"[TTS] SAPI init failed: {e}")
            self._sapi_speaker = None

    def _speak_sapi(self, text: str):
        try:
            lang   = self._lang
            gender = self._gender
            voices = self._sapi_speaker.GetVoices()
            chosen = None

            # أسماء أصوات SAPI الشائعة
            male_ar   = ["naayf", "hamed"]
            female_ar = ["hoda", "salma"]
            male_en   = ["david", "mark", "guy", "richard"]
            female_en = ["zira", "aria", "hazel", "susan"]

            # Try to match BOTH language and gender first
            for i in range(voices.Count):
                v    = voices.Item(i)
                desc = v.GetDescription().lower()
                if lang == "ar":
                    pool = male_ar if gender == "male" else female_ar
                    if any(n in desc for n in pool):
                        chosen = v
                        break
                else:
                    pool = male_en if gender == "male" else female_en
                    if any(n in desc for n in pool):
                        chosen = v
                        break

            # If not found, fall back to matching language only (regardless of gender)
            if not chosen:
                for i in range(voices.Count):
                    v    = voices.Item(i)
                    desc = v.GetDescription().lower()
                    if lang == "ar" and ("arabic" in desc or any(n in desc for n in male_ar + female_ar)):
                        chosen = v
                        break
                    elif lang != "ar" and ("english" in desc or any(n in desc for n in male_en + female_en)):
                        chosen = v
                        break

            if chosen:
                self._sapi_speaker.Voice = chosen
            self._sapi_speaker.Speak(text)
        except Exception as e:
            logger.warning(f"[TTS] SAPI speak error: {e}")

    # ══════════════════════════════════════════════════════
    #  espeak (Linux / Raspberry Pi fallback)
    # ══════════════════════════════════════════════════════

    def _speak_espeak(self, text: str):
        """Linux fallback: uses espeak-ng or espeak for speech output."""
        try:
            lang_code = "ar" if self._lang == "ar" else "en"
            # Try espeak-ng first, then espeak
            for cmd in ("espeak-ng", "espeak"):
                try:
                    subprocess.run(
                        [cmd, "-v", lang_code, text],
                        timeout=10,
                        capture_output=True,
                    )
                    return
                except FileNotFoundError:
                    continue
            print(f"[TTS-PRINT] {text}")
        except Exception as e:
            logger.warning(f"[TTS] espeak error: {e}")
            print(f"[TTS-PRINT] {text}")
