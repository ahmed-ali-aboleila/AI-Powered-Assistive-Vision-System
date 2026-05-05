"""
shared/stt.py - Speech to Text
================================
Dual-mode STT:
  - Online  -> Google Speech API (high accuracy)
  - Offline -> Vosk local model (wake word + basic commands)

Wake word "Vision" always works even without internet.
Full commands use Google when available, Vosk when offline.
"""
import speech_recognition as sr
import logging
import time
import threading
import os

logger = logging.getLogger(__name__)

YES = {"yes","yeah","yep","yup","sure","ok","okay",
       "correct","right","register","add","do","please"}
NO  = {"no","nope","nah","skip","cancel","stop",
       "wrong","negative","ignore","don't","dont"}

OFFLINE_COMMANDS = [
    "vision","register","block","unblock","delete",
    "list","who","quiet","silence","mute",
    "speak","resume","unmute","stop","yes","no",
    "yeah","nope","okay","cancel"
]

VOSK_MODEL_PATH = "models/vosk-model"


class STT:
    def __init__(self):
        self.r = sr.Recognizer()
        self.r.pause_threshold          = 1.5
        self.r.phrase_threshold         = 0.3
        self.r.non_speaking_duration    = 0.8
        self.r.dynamic_energy_threshold = False
        self.r.energy_threshold         = 400
        self._mic = None

        # Internet status
        self._online            = True
        self._last_online_check = 0

        # Vosk
        self._vosk_model      = None
        self._vosk_recognizer = None
        self._vosk_ready      = False
        self._init_vosk()

    def _init_vosk(self):
        def _load():
            try:
                import config
                if not config.VOSK_ENABLED:
                    print("[STT] Vosk disabled in config.")
                    return
                from vosk import Model, KaldiRecognizer, SetLogLevel
                SetLogLevel(-1)
                if not os.path.exists(VOSK_MODEL_PATH):
                    print("[STT] Vosk model not found — offline mode disabled")
                    return
                print("[STT] Loading Vosk model...")
                import json
                model = Model(VOSK_MODEL_PATH)
                grammar = json.dumps(OFFLINE_COMMANDS)
                self._vosk_model      = model
                self._vosk_recognizer = KaldiRecognizer(model, 16000, grammar)
                self._vosk_ready      = True
                print("[STT] Vosk ready — offline commands enabled")
            except Exception as e:
                print(f"[STT] Vosk init failed: {e}")
        threading.Thread(target=_load, daemon=True).start()

    def _check_online(self) -> bool:
        now = time.time()
        if now - self._last_online_check < 10.0:
            return self._online
        self._last_online_check = now
        try:
            import socket
            socket.setdefaulttimeout(2)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            if not self._online:
                print("[STT] Internet restored — using Google Speech")
            self._online = True
        except Exception:
            if self._online:
                print("[STT] No internet — using Vosk offline mode")
            self._online = False
        return self._online

    def calibrate(self, duration: float = 2.0):
        print("[STT] Calibrating mic — please be quiet for 2 seconds...")
        try:
            with sr.Microphone(device_index=self._mic) as src:
                self.r.adjust_for_ambient_noise(src, duration=duration)
            self.r.energy_threshold = max(300, min(1500, self.r.energy_threshold))
            print(f"[STT] Ready. Threshold = {self.r.energy_threshold:.0f}")
        except Exception as e:
            logger.warning(f"Calibrate: {e}")
            self.r.energy_threshold = 400
            print("[STT] Using default threshold = 400")

    def _quick_recal(self):
        try:
            with sr.Microphone(device_index=self._mic) as src:
                self.r.adjust_for_ambient_noise(src, duration=0.5)
            self.r.energy_threshold = max(300, min(1500, self.r.energy_threshold))
        except Exception:
            pass

    def listen(self, timeout: float = 8.0,
               phrase_limit: float = 10.0,
               recal: bool = False) -> str | None:
        if recal:
            self._quick_recal()
        try:
            with sr.Microphone(device_index=self._mic) as src:
                print(f"[STT] Listening... (E={self.r.energy_threshold:.0f})")
                audio = self.r.listen(src, timeout=timeout,
                                      phrase_time_limit=phrase_limit)
        except sr.WaitTimeoutError:
            print("[STT] No speech detected.")
            return None
        except Exception as e:
            logger.warning(f"Mic: {e}")
            return None

        # Try Google first if online
        if self._check_online():
            result = self._recognize_google(audio)
            if result is not None:
                return result
            print("[STT] Google failed — trying Vosk")

        # Fallback to Vosk
        return self._recognize_vosk(audio)

    def _recognize_google(self, audio) -> str | None:
        try:
            text = self.r.recognize_google(audio, language="en-US")
            print(f"[STT] Google: '{text}'")
            return text.lower().strip()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"[STT] Google error: {e}")
            self._online = False
            return None

    def _recognize_vosk(self, audio) -> str | None:
        if not self._vosk_ready:
            print("[STT] Vosk not ready.")
            return None
        try:
            import json
            wav_data = audio.get_wav_data(convert_rate=16000, convert_width=2)
            self._vosk_recognizer.AcceptWaveform(wav_data)
            result = json.loads(self._vosk_recognizer.Result())
            text   = result.get("text", "").strip()
            if text:
                print(f"[STT] Vosk: '{text}'")
                return text.lower()
            return None
        except Exception as e:
            logger.warning(f"Vosk: {e}")
            return None

    def yes_no(self, tries: int = 4, timeout: float = 8.0) -> bool | None:
        for i in range(1, tries + 1):
            text = self.listen(timeout=timeout, phrase_limit=4.0, recal=(i > 1))
            if text is None: continue
            if any(w in text for w in YES):
                print("[STT] YES"); return True
            if any(w in text for w in NO):
                print("[STT] NO");  return False
            print(f"[STT] '{text}' not yes/no — attempt {i}/{tries}")
        return None

    def get_name(self, tries: int = 3, timeout: float = 9.0) -> str | None:
        for i in range(1, tries + 1):
            text = self.listen(timeout=timeout, phrase_limit=10.0, recal=(i > 1))
            if not text: continue
            words = text.strip().split()
            if "is" in words:
                idx = words.index("is")
                if idx + 1 < len(words):
                    words = words[idx + 1:]
            name = " ".join(words[:2]).title()
            if len(name) >= 2:
                print(f"[STT] Name: '{name}'")
                return name
            print(f"[STT] Name too short — attempt {i}/{tries}")
        return None
