"""
shared/tts.py - Unified TTS engine (Windows)
Single instance shared between Face Recognition and Emotion Detection.
Uses win32com SpVoice for reliability on Windows.
"""
import threading
import queue
import time
import logging

logger = logging.getLogger(__name__)
_STOP  = object()


class TTS:
    def __init__(self, rate: int = 140):
        self._q      = queue.Queue()
        self._done   = threading.Event()
        self._done.set()
        self._rate   = rate
        self._ready  = threading.Event()
        self._quiet  = False   # quiet mode

        t = threading.Thread(target=self._worker, daemon=True)
        t.start()
        self._ready.wait(timeout=10)

    # ── Public API ────────────────────────────────────────────────────────────

    def say(self, text: str):
        """Non-blocking — skips if quiet mode is on"""
        if self._quiet:
            print(f"[TTS-QUIET] {text}")
            return
        print(f"[TTS] {text}")
        self._done.clear()
        self._q.put(text)

    def say_wait(self, text: str, pause: float = 1.6):
        """Blocking — always speaks even in quiet mode (for system messages)"""
        print(f"[TTS] {text}")
        self._done.clear()
        self._q.put(text)
        self._done.wait(timeout=30)
        time.sleep(pause)

    def stop(self):
        """Stop current speech immediately"""
        while not self._q.empty():
            try: self._q.get_nowait()
            except: pass
        self._done.set()

    def set_quiet(self, quiet: bool):
        """Enable/disable quiet mode"""
        self._quiet = quiet
        if quiet:
            self.stop()
            print("[TTS] Quiet mode ON")
        else:
            print("[TTS] Quiet mode OFF")

    def is_quiet(self) -> bool:
        return self._quiet

    def wait(self, timeout: float = 15.0):
        self._done.wait(timeout=timeout)

    def busy(self) -> bool:
        return not self._done.is_set()

    # ── Worker ────────────────────────────────────────────────────────────────

    def _worker(self):
        speak_fn = self._init_engine()
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
                speak_fn(text)
            except Exception as e:
                logger.warning(f"[TTS] speak error: {e}")
                try:
                    speak_fn = self._init_engine()
                    speak_fn(text)
                except Exception as e2:
                    logger.error(f"[TTS] reinit failed: {e2}")

            if self._q.empty():
                self._done.set()

    def _init_engine(self):
        # Method 1: win32com SpVoice
        try:
            import pythoncom
            pythoncom.CoInitialize()
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            sapi_rate = max(-5, min(5, int((self._rate - 150) / 20)))
            speaker.Rate = sapi_rate

            def speak_sapi(text):
                speaker.Speak(text)

            print("[TTS] Using win32com SpVoice")
            return speak_sapi
        except Exception as e:
            logger.warning(f"[TTS] SpVoice failed: {e}")

        # Method 2: pyttsx3 with CoInitialize
        try:
            import pythoncom
            pythoncom.CoInitialize()
            import pyttsx3
            eng = pyttsx3.init()
            eng.setProperty("rate", self._rate)

            def speak_pyttsx3(text):
                eng.say(text)
                eng.runAndWait()

            print("[TTS] Using pyttsx3 with CoInitialize")
            return speak_pyttsx3
        except Exception as e:
            logger.warning(f"[TTS] pyttsx3 failed: {e}")

        # Method 3: print only
        def speak_print(text):
            print(f"[TTS-PRINT] {text}")

        print("[TTS] No audio — print only mode")
        return speak_print
