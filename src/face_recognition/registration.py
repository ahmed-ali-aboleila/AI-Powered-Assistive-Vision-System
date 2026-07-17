"""
registration.py â€” v7
Ø§Ù„ØªØ¹Ø¯ÙŠÙ„Ø§Øª:
  1. Beep ØµÙˆØª "ØªÙ†" ÙƒÙ„ 3 Ø«ÙˆØ§Ù†ÙŠ Ø£Ø«Ù†Ø§Ø¡ ØªØ³Ø¬ÙŠÙ„ Ø§Ù„Ø´Ø®Øµ
  2. Ø¥Ø±Ø´Ø§Ø¯Ø§Øª Ù„Ù„Ø´Ø®Øµ Ø£Ø«Ù†Ø§Ø¡ Ø§Ù„ØªØ³Ø¬ÙŠÙ„ (Ø§Ù†Ø¸Ø± ÙŠÙ…ÙŠÙ†ØŒ Ø´Ù…Ø§Ù„ØŒ ÙÙˆÙ‚ØŒ ØºÙŠØ± ØªØ¹Ø¨ÙŠØ± ÙˆØ¬Ù‡...)
  3. ÙƒÙ„ Ø§Ù„Ø¬Ù…Ù„ Ù…ØªØ±Ø¬Ù…Ø© Ø¹Ø±Ø¨ÙŠ/Ø¥Ù†Ø¬Ù„ÙŠØ²ÙŠ Ø­Ø³Ø¨ config.LANGUAGE
"""

import time, queue, threading, logging, json, os, re
import numpy as np
import config

try:
    import winsound
    _BEEP_OK = True
except ImportError:
    _BEEP_OK = False

logger   = logging.getLogger(__name__)
SAMPLES  = 120   # Ø²Ø¯Ù†Ø§ Ù…Ù† 80 Ù„â†’ 120 ØµÙˆØ±Ø© â€” ØªØºØ·ÙŠØ© Ø£Ø®Ø³Ù† Ù„ØªØ¹Ø§Ø¨ÙŠØ± Ù…Ø®ØªÙ„ÙØ©
TIMEOUT  = 90.0  # Ø²Ø¯Ù†Ø§ Ù…Ù† 60 Ù„â†’ 90 Ø«Ø§Ù†ÙŠØ© Ø¹Ø´Ø§Ù† Ù†ÙƒØ¯Ø± Ù†Ù„ØªÙ‚Ø· Ø§Ù„ØµÙˆØ± Ø§Ù„ÙƒØ§ÙÙŠØ©

BLOCK_FILE = "blocked.json"

# â”€â”€ Ù†ØµÙˆØµ Ø§Ù„Ù„ØºØªÙŠÙ† â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_STR = {
    "en": {
        "say_name":         "Please say the name of this person.",
        "didnt_hear":       "I did not hear you. Please try again.",
        "heard":            "I heard {name}. Is that correct? Say yes or no.",
        "try_again":        "Let us try again.",
        "no_name":          "Could not get a name. Registration cancelled.",
        "registering":      "Registering {name}. Please stand still and face the camera.",
        "vary_expr_hint":   "Tip: slightly vary your expression during capture for better accuracy.",
        "not_enough":       "Not enough photos captured. Please try again.",
        "success":          "{name} has been registered successfully.",
        "no_to_delete":     "No registered persons to delete.",
        "say_delete":       "Registered persons: {names}. Say the name to delete.",
        "no_name_heard":    "No name heard. Cancelled.",
        "not_found":        "Could not find {name}. Cancelled.",
        "confirm_delete":   "Delete {name}? Say yes or no.",
        "cancelled":        "Cancelled.",
        "deleted":          "{name} has been deleted.",
        "keep_person":      "Please keep the person in front of the camera.",
        "no_frame":         "No image received. Cancelling.",
        "no_face":          "No face detected. Please stand in front of the camera.",
        "already_reg":      "This person is already registered as {name}. Cannot block a registered person.",
        "say_label":        "Say a label for this person.",
        "no_label":         "No label heard. Cancelling.",
        "blocking":         "Blocking {name}. Please stay still.",
        "blocked":          "{name} has been blocked.",
        "no_blocked":       "No blocked persons.",
        "say_unblock":      "Blocked persons: {names}. Say the name to unblock.",
        "not_blocked":      "Could not find {name} in the blocked list.",
        "confirm_unblock":  "Unblock {name}? Say yes or no.",
        "unblocked":        "{name} has been unblocked.",
        "look_straight":    "Please look straight at the camera.",
        "look_left":        "Please turn your head slightly to the left.",
        "look_right":       "Please turn your head slightly to the right.",
        "vary_expression":  "Now, smile or change your expression.",
    },
    "ar": {
        "say_name":         "Ù…Ù† ÙØ¶Ù„Ùƒ Ù‚Ù„ Ø§Ø³Ù… Ù‡Ø°Ø§ Ø§Ù„Ø´Ø®Øµ.",
        "didnt_hear":       "Ù„Ù… Ø£Ø³Ù…Ø¹Ùƒ. Ù…Ù† ÙØ¶Ù„Ùƒ Ø­Ø§ÙˆÙ„ Ù…Ø±Ø© Ø£Ø®Ø±Ù‰.",
        "heard":            "Ø³Ù…Ø¹Øª {name}. Ù‡Ù„ Ù‡Ø°Ø§ ØµØ­ÙŠØ­ØŸ Ù‚Ù„ Ù†Ø¹Ù… Ø£Ùˆ Ù„Ø§.",
        "try_again":        "Ù„Ù†Ø­Ø§ÙˆÙ„ Ù…Ø±Ø© Ø£Ø®Ø±Ù‰.",
        "no_name":          "Ù„Ù… Ø£ØªÙ…ÙƒÙ† Ù…Ù† Ø§Ù„Ø­ØµÙˆÙ„ Ø¹Ù„Ù‰ Ø§Ø³Ù…. ØªÙ… Ø¥Ù„ØºØ§Ø¡ Ø§Ù„ØªØ³Ø¬ÙŠÙ„.",
        "registering":      "Ø¬Ø§Ø±ÙŠ ØªØ³Ø¬ÙŠÙ„ {name}. Ù…Ù† ÙØ¶Ù„Ùƒ Ù‚Ù Ø£Ù…Ø§Ù… Ø§Ù„ÙƒØ§Ù…ÙŠØ±Ø§ Ø¨Ø«Ø¨Ø§Øª.",
        "vary_expr_hint":   "Ù†ØµÙŠØ­Ø©: ØºÙŠÙ‘Ø± ØªØ¹Ø¨ÙŠØ±Ùƒ Ù‚Ù„ÙŠÙ„Ø§Ù‹ Ø£Ø«Ù†Ø§Ø¡ Ø§Ù„ØªØ³Ø¬ÙŠÙ„ Ù„Ø¯Ù‚Ø© Ø£Ø¹Ù„Ù‰.",
        "not_enough":       "Ù„Ù… ÙŠØªÙ… Ø§Ù„ØªÙ‚Ø§Ø· ØµÙˆØ± ÙƒØ§ÙÙŠØ©. Ù…Ù† ÙØ¶Ù„Ùƒ Ø­Ø§ÙˆÙ„ Ù…Ø±Ø© Ø£Ø®Ø±Ù‰.",
        "success":          "ØªÙ… ØªØ³Ø¬ÙŠÙ„ {name} Ø¨Ù†Ø¬Ø§Ø­.",
        "no_to_delete":     "Ù„Ø§ ÙŠÙˆØ¬Ø¯ Ø£Ø´Ø®Ø§Øµ Ù…Ø³Ø¬Ù„ÙˆÙ† Ù„Ù„Ø­Ø°Ù.",
        "say_delete":       "Ø§Ù„Ø£Ø´Ø®Ø§Øµ Ø§Ù„Ù…Ø³Ø¬Ù„ÙˆÙ†: {names}. Ù‚Ù„ Ø§Ù„Ø§Ø³Ù… Ø§Ù„Ø°ÙŠ ØªØ±ÙŠØ¯ Ø­Ø°ÙÙ‡.",
        "no_name_heard":    "Ù„Ù… Ø£Ø³Ù…Ø¹ Ø§Ø³Ù…Ø§Ù‹. ØªÙ… Ø§Ù„Ø¥Ù„ØºØ§Ø¡.",
        "not_found":        "Ù„Ù… Ø£Ø¬Ø¯ {name}. ØªÙ… Ø§Ù„Ø¥Ù„ØºØ§Ø¡.",
        "confirm_delete":   "Ù‡Ù„ ØªØ±ÙŠØ¯ Ø­Ø°Ù {name}ØŸ Ù‚Ù„ Ù†Ø¹Ù… Ø£Ùˆ Ù„Ø§.",
        "cancelled":        "ØªÙ… Ø§Ù„Ø¥Ù„ØºØ§Ø¡.",
        "deleted":          "ØªÙ… Ø­Ø°Ù {name}.",
        "keep_person":      "Ù…Ù† ÙØ¶Ù„Ùƒ Ø§Ø¨Ù‚ Ø§Ù„Ø´Ø®Øµ Ø£Ù…Ø§Ù… Ø§Ù„ÙƒØ§Ù…ÙŠØ±Ø§.",
        "no_frame":         "Ù„Ù… ÙŠØµÙ„ Ø£ÙŠ Ø¥Ø·Ø§Ø±. Ø¬Ø§Ø±ÙŠ Ø§Ù„Ø¥Ù„ØºØ§Ø¡.",
        "no_face":          "Ù„Ù… ÙŠØªÙ… Ø§ÙƒØªØ´Ø§Ù ÙˆØ¬Ù‡. Ù…Ù† ÙØ¶Ù„Ùƒ Ù‚Ù Ø£Ù…Ø§Ù… Ø§Ù„ÙƒØ§Ù…ÙŠØ±Ø§.",
        "already_reg":      "Ù‡Ø°Ø§ Ø§Ù„Ø´Ø®Øµ Ù…Ø³Ø¬Ù„ Ø¨Ø§Ù„ÙØ¹Ù„ Ø¨Ø§Ø³Ù… {name}. Ù„Ø§ ÙŠÙ…ÙƒÙ† Ø­Ø¸Ø± Ø´Ø®Øµ Ù…Ø³Ø¬Ù„.",
        "say_label":        "Ù‚Ù„ ØªØ³Ù…ÙŠØ© Ù„Ù‡Ø°Ø§ Ø§Ù„Ø´Ø®Øµ.",
        "no_label":         "Ù„Ù… Ø£Ø³Ù…Ø¹ ØªØ³Ù…ÙŠØ©. Ø¬Ø§Ø±ÙŠ Ø§Ù„Ø¥Ù„ØºØ§Ø¡.",
        "blocking":         "Ø¬Ø§Ø±ÙŠ Ø­Ø¸Ø± {name}. Ø§Ø¨Ù‚ Ø«Ø§Ø¨ØªØ§Ù‹ Ù…Ù† ÙØ¶Ù„Ùƒ.",
        "blocked":          "ØªÙ… Ø­Ø¸Ø± {name}.",
        "no_blocked":       "Ù„Ø§ ÙŠÙˆØ¬Ø¯ Ø£Ø´Ø®Ø§Øµ Ù…Ø­Ø¸ÙˆØ±ÙˆÙ†.",
        "say_unblock":      "Ø§Ù„Ø£Ø´Ø®Ø§Øµ Ø§Ù„Ù…Ø­Ø¸ÙˆØ±ÙˆÙ†: {names}. Ù‚Ù„ Ø§Ù„Ø§Ø³Ù… Ø§Ù„Ø°ÙŠ ØªØ±ÙŠØ¯ Ø±ÙØ¹ Ø­Ø¸Ø±Ù‡.",
        "not_blocked":      "Ù„Ù… Ø£Ø¬Ø¯ {name} ÙÙŠ Ù‚Ø§Ø¦Ù…Ø© Ø§Ù„Ø­Ø¸Ø±.",
        "confirm_unblock":  "Ù‡Ù„ ØªØ±ÙŠØ¯ Ø±ÙØ¹ Ø­Ø¸Ø± {name}ØŸ Ù‚Ù„ Ù†Ø¹Ù… Ø£Ùˆ Ù„Ø§.",
        "unblocked":        "ØªÙ… Ø±ÙØ¹ Ø­Ø¸Ø± {name}.",
        "look_straight":    "Ù…Ù† ÙØ¶Ù„Ùƒ Ø§Ù†Ø¸Ø± Ù…Ø¨Ø§Ø´Ø±Ø© Ø¥Ù„Ù‰ Ø§Ù„ÙƒØ§Ù…ÙŠØ±Ø§.",
        "look_left":        "Ù…Ù† ÙØ¶Ù„Ùƒ Ø§Ù„ØªÙØª Ø¨Ø±Ø£Ø³Ùƒ Ù‚Ù„ÙŠÙ„Ø§Ù‹ Ø¥Ù„Ù‰ Ø§Ù„ÙŠØ³Ø§Ø±.",
        "look_right":       "Ù…Ù† ÙØ¶Ù„Ùƒ Ø§Ù„ØªÙØª Ø¨Ø±Ø£Ø³Ùƒ Ù‚Ù„ÙŠÙ„Ø§Ù‹ Ø¥Ù„Ù‰ Ø§Ù„ÙŠÙ…ÙŠÙ†.",
        "vary_expression":  "Ø§Ù„Ø¢Ù†ØŒ Ø§Ø¨ØªØ³Ù… Ø£Ùˆ ØºÙŠØ± ØªØ¹Ø¨ÙŠØ± ÙˆØ¬Ù‡Ùƒ.",
    },
}

_STR["en"].update({
    "improve_who": "Which registered person do you want to improve?",
    "confirm_improve": "Improve {name}? Say yes or no.",
    "improving": "Improving {name}. Please face the camera and follow the guidance.",
    "improved": "{name} has been improved successfully.",
    "no_registered": "No registered persons.",
})
_STR["ar"].update({
    "improve_who": "\u0645\u0646 \u0627\u0644\u0634\u062e\u0635 \u0627\u0644\u0645\u0633\u062c\u0644 \u0627\u0644\u0630\u064a \u062a\u0631\u064a\u062f \u062a\u062d\u0633\u064a\u0646\u0647\u061f",
    "confirm_improve": "\u0647\u0644 \u062a\u0631\u064a\u062f \u062a\u062d\u0633\u064a\u0646 \u062a\u0633\u062c\u064a\u0644 {name}\u061f \u0642\u0644 \u0646\u0639\u0645 \u0623\u0648 \u0644\u0627.",
    "improving": "\u062c\u0627\u0631\u064a \u062a\u062d\u0633\u064a\u0646 \u062a\u0633\u062c\u064a\u0644 {name}. \u0645\u0646 \u0641\u0636\u0644\u0643 \u0648\u0627\u062c\u0647 \u0627\u0644\u0643\u0627\u0645\u064a\u0631\u0627 \u0648\u0627\u062a\u0628\u0639 \u0627\u0644\u0625\u0631\u0634\u0627\u062f\u0627\u062a.",
    "improved": "\u062a\u0645 \u062a\u062d\u0633\u064a\u0646 \u062a\u0633\u062c\u064a\u0644 {name} \u0628\u0646\u062c\u0627\u062d.",
    "no_registered": "\u0644\u0627 \u064a\u0648\u062c\u062f \u0623\u0634\u062e\u0627\u0635 \u0645\u0633\u062c\u0644\u0648\u0646.",
})


def _t(key: str, **kwargs) -> str:
    lang = getattr(config, "LANGUAGE", "en")
    text = _STR.get(lang, _STR["en"]).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


import sys as _sys
import subprocess as _subprocess


def _beep():
    """ØµÙˆØª ØªÙ† Ù‚ØµÙŠØ± ÙŠØ¹Ù„Ù… Ø§Ù„Ø´Ø®Øµ Ø¨Ø§Ù„ØªÙ‚Ø§Ø· ØµÙˆØ±Ø©."""
    if _BEEP_OK:
        try:
            winsound.Beep(1000, 70)
            return
        except Exception:
            pass
    # Linux / Raspberry Pi fallback
    if _sys.platform != 'win32':
        try:
            # Generate a short beep tone using aplay (available on most RPi setups)
            _subprocess.Popen(
                ['python3', '-c',
                 'import struct,wave,os,tempfile;'
                 'f=tempfile.NamedTemporaryFile(suffix=".wav",delete=False);'
                 'w=wave.open(f.name,"w");w.setnchannels(1);w.setsampwidth(2);'
                 'w.setframerate(16000);'
                 'd=b"".join(struct.pack("<h",int(20000*__import__("math").sin(2*3.14159*1000*i/16000))) for i in range(1920));'
                 'w.writeframes(d);w.close();'
                 'os.system("aplay -q "+f.name);os.unlink(f.name)'],
                stdout=_subprocess.DEVNULL,
                stderr=_subprocess.DEVNULL,
            )
            return
        except Exception:
            pass
    print("\a", end="", flush=True)


def _beep_beep():
    """ØµÙˆØª ØªÙ† ØªÙ† Ù‚ØµÙŠØ± (Ù…Ø²Ø¯ÙˆØ¬) ÙŠØ¹Ù„Ù… Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù… Ø£Ù† Ø§Ù„Ù†Ø¸Ø§Ù… ÙŠØ¹Ù…Ù„ Ø¨Ù†Ø´Ø§Ø·."""
    if _BEEP_OK:
        def _play():
            try:
                winsound.Beep(1200, 80)
                time.sleep(0.1)
                winsound.Beep(1200, 80)
            except Exception:
                pass
        threading.Thread(target=_play, daemon=True).start()
        return
    # Linux / Raspberry Pi fallback â€” two short beeps
    if _sys.platform != 'win32':
        def _play_linux():
            _beep()
            time.sleep(0.15)
            _beep()
        threading.Thread(target=_play_linux, daemon=True).start()
        return
    # fallback
    print("\a\a", end="", flush=True)


def load_blocked() -> set:
    if os.path.exists(BLOCK_FILE):
        try:
            with open(BLOCK_FILE) as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


def save_blocked(blocked: set):
    with open(BLOCK_FILE, "w") as f:
        json.dump(list(blocked), f)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

try:
    from voice.tts import TTS
    from voice.stt import STT
    from face_recognition.face_db import FaceDB
    from face_recognition.face_processor import FaceProcessor
except ImportError:
    from tts import TTS
    from stt import STT
    from face_db import FaceDB
    from face_processor import FaceProcessor


def _parse_number(text: str) -> int | None:
    t = _normalize_command_text(text)
    if t.isdigit():
        return int(t)
    
    eng_map = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    ar_map = {
        "ÙˆØ§Ø­Ø¯": 1, "ÙˆØ§Ø­Ø¯Ø©": 1, "Ø§ØªÙ†ÙŠÙ†": 2, "Ø§Ø«Ù†ÙŠÙ†": 2, "ØªÙ„Ø§ØªØ©": 3, "Ø«Ù„Ø§Ø«Ø©": 3, "ØªÙ„Ø§ØªÙ‡": 3, "Ø«Ù„Ø§Ø«Ù‡": 3,
        "Ø§Ø±Ø¨Ø¹Ø©": 4, "Ø£Ø±Ø¨Ø¹Ø©": 4, "Ø§Ø±Ø¨Ø¹": 4, "Ø®Ù…Ø³Ø©": 5, "Ø®Ù…Ø³Ù‡": 5, "Ø®Ù…Ø³": 5, "Ø³ØªØ©": 6, "Ø³ØªÙ‡": 6, "Ø³Øª": 6,
        "Ø³Ø¨Ø¹Ø©": 7, "Ø³Ø¨Ø¹Ù‡": 7, "Ø³Ø¨Ø¹": 7, "Ø«Ù…Ø§Ù†ÙŠØ©": 8, "ØªÙ…Ø§Ù†ÙŠØ©": 8, "ØªÙ…Ø§Ù†ÙŠÙ‡": 8, "ØªØ³Ø¹Ø©": 9, "ØªØ³Ø¹Ù‡": 9, "Ø¹Ø´Ø±Ø©": 10, "Ø¹Ø´Ø±Ù‡": 10
    }
    
    number_prefixes = (
        "number", "number.", "no", "no.", "num", "num.",
        "Ø±Ù‚Ù…", "Ù†Ù…Ø¨Ø±", "Ù†Ù…Ø±Ø©", "Ø±Ù‚Ù… Ø§Ù„Ø´Ø®Øµ", "Ø§Ù„Ø´Ø®Øµ Ø±Ù‚Ù…",
    )
    for prefix in number_prefixes:
        if t.startswith(prefix + " "):
            t = t[len(prefix):].strip()
            break

    digit_match = re.search(r"\d+", t)
    if digit_match:
        return int(digit_match.group(0))

    if t in eng_map:
        return eng_map[t]
    if t in ar_map:
        return ar_map[t]
        
    for word, val in eng_map.items():
        if word in t:
            return val
    for word, val in ar_map.items():
        if word in t:
            return val
    return None


def _normalize_command_text(text: str) -> str:
    t = str(text or "").strip().lower()
    arabic_digits = str.maketrans("Ù Ù¡Ù¢Ù£Ù¤Ù¥Ù¦Ù§Ù¨Ù©", "0123456789")
    eastern_digits = str.maketrans("Û°Û±Û²Û³Û´ÛµÛ¶Û·Û¸Û¹", "0123456789")
    t = t.translate(arabic_digits).translate(eastern_digits)
    t = re.sub(r"[^\w\s\u0600-\u06ff]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _is_delete_all_command(text: str) -> bool:
    t = _normalize_command_text(text)
    if not t:
        return False

    exact = {
        "all", "all names", "delete all", "delete everyone", "everyone",
        "everybody", "whole list", "clear all", "wipe all", "remove all",
        "all people", "all persons",
        "Ø§Ù„ÙƒÙ„", "ÙƒÙ„", "ÙƒÙ„Ù‡", "ÙƒÙ„Ù‡Ù…", "Ø§Ù…Ø³Ø­ Ø§Ù„ÙƒÙ„", "Ø§Ø­Ø°Ù Ø§Ù„ÙƒÙ„",
        "Ø­Ø°Ù Ø§Ù„ÙƒÙ„", "Ù…Ø³Ø­ Ø§Ù„ÙƒÙ„", "ÙƒÙ„ Ø§Ù„Ø§Ø³Ù…Ø§Ø¡", "ÙƒÙ„ Ø§Ù„Ø£Ø³Ù…Ø§Ø¡",
        "Ø¬Ù…ÙŠØ¹ Ø§Ù„Ø§Ø³Ù…Ø§Ø¡", "Ø¬Ù…ÙŠØ¹ Ø§Ù„Ø£Ø³Ù…Ø§Ø¡", "ÙƒÙ„ Ø§Ù„Ù†Ø§Ø³", "Ø§Ù„Ø¬Ù…ÙŠØ¹",
    }
    if t in exact:
        return True

    # Common STT near-misses for "all"; keep these scoped to delete flow only.
    near_misses = {"old", "ole", "owl", "call"}
    if t in near_misses:
        return True

    return (
        ("all" in t and any(w in t for w in ("delete", "clear", "wipe", "remove", "names", "people")))
        or ("ÙƒÙ„" in t and any(w in t for w in ("Ø§Ù…Ø³Ø­", "Ø§Ø­Ø°Ù", "Ø­Ø°Ù", "Ù…Ø³Ø­", "Ø§Ø³Ù…", "Ø§Ù„Ø§Ø³Ù…Ø§Ø¡", "Ø§Ù„Ø£Ø³Ù…Ø§Ø¡")))
    )


class RegFlow:
    def __init__(self, tts: TTS, stt: STT, db: FaceDB, proc: FaceProcessor):
        self.tts     = tts
        self.stt     = stt
        self.db      = db
        self.proc    = proc
        self.blocked = load_blocked()

        self._fq     = queue.Queue(maxsize=3)
        self._rq     = queue.Queue(maxsize=1)
        self._active = False
        self._mode   = "register"
        self._target_name = None
        self.current_instruction = ""

    @property
    def active(self): return self._active

    def start_register(self): self._go("register")
    def start_improve(self, name: str | None = None):
        self._target_name = name
        self._go("improve")
    def start_delete(self):   self._go("delete")
    def start_block(self):    self._go("block")
    def start_unblock(self):  self._go("unblock")

    def _go(self, mode: str):
        deadline = time.time() + 60.0
        while self._active and time.time() < deadline:
            time.sleep(0.2)
        if self._active:
            return
        self._mode   = mode
        self._active = True
        while not self._fq.empty():
            try: self._fq.get_nowait()
            except: pass
        threading.Thread(target=self._run, daemon=True).start()

    def feed(self, frame: np.ndarray):
        if not self._active: return
        if self._fq.full():
            try: self._fq.get_nowait()
            except: pass
        try: self._fq.put_nowait(frame.copy())
        except: pass

    def result(self):
        try:
            r = self._rq.get_nowait()
            self._active = False
            return r
        except queue.Empty:
            return "PENDING"

    def _run(self):
        r = None
        try:
            if   self._mode == "register": r = self._register()
            elif self._mode == "improve":  r = self._improve()
            elif self._mode == "delete":   r = self._delete()
            elif self._mode == "block":    r = self._block()
            elif self._mode == "unblock":  r = self._unblock()
        except Exception as e:
            logger.error(f"RegFlow: {e}", exc_info=True)
        finally:
            self._rq.put(r)
            self._active = False
            self.current_instruction = ""

    # â”€â”€ Register â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _register(self):
        name = None
        for attempt in range(1, 4):
            self._say(_t("say_name"))
            heard = self.stt.get_name(tries=2, timeout=10.0, tts=self.tts)
            if heard:
                h_cleaned = heard.lower().strip()
                if h_cleaned in ["cancel", "exit", "stop", "close", "Ø§Ù„ØºÙŠ", "Ø§Ù„Øº", "Ø§Ù„ØºØ§Ø¡", "Ø¥Ù„ØºØ§Ø¡", "Ø¨Ù„Ø§Ø´", "Ø®Ø±ÙˆØ¬", "Ø§Ø®Ø±Ø¬"]:
                    self._say(_t("cancelled"))
                    return None
            if not heard:
                if attempt < 3:
                    self._say(_t("didnt_hear"))
                continue
            self._say(_t("heard", name=heard))
            ok = self.stt.yes_no(tries=3, timeout=8.0, tts=self.tts)
            if ok is True:
                name = heard
                break
            self._say(_t("try_again"))

        if not name:
            self._say(_t("no_name"))
            return None

        self._say(_t("registering", name=name))
        self._say(_t("vary_expr_hint"))   # Ù†ØµÙŠØ­Ø© ÙˆØ§Ø­Ø¯Ø© ÙÙ‚Ø· Ø¹Ù† ØªÙ†ÙˆÙŠØ¹ Ø§Ù„ØªØ¹Ø§Ø¨ÙŠØ±
        embs = self._capture_with_guidance()

        if len(embs) < 15:
            self._say(_t("not_enough"))
            return None

        self.db.add(name, embs)
        self._say(_t("success", name=name))
        return f"registered:{name}"

    def _match_registered_name(self, target: str) -> str | None:
        ns = [n for n in self.db.names() if not n.startswith("__blocked__")]
        if not target:
            return None
        target_l = target.lower().strip()
        return next(
            (n for n in ns if n.lower() == target_l or target_l in n.lower()),
            None
        )

    def _improve(self):
        ns = [n for n in self.db.names() if not n.startswith("__blocked__")]
        if not ns:
            self._say(_t("no_registered"))
            return None

        name = self._match_registered_name(self._target_name or "")
        if not name:
            self._say(_t("improve_who"))
            for attempt in range(1, 4):
                heard = self.stt.get_name(tries=2, timeout=10.0, tts=self.tts)
                if not heard:
                    if attempt < 3:
                        self._say(_t("try_again"))
                    continue
                name = self._match_registered_name(heard)
                if name:
                    break
                self._say(_t("not_found", name=heard))
                if attempt < 3:
                    self._say(_t("try_again"))

        if not name:
            self._say(_t("cancelled"))
            return None

        self._say(_t("confirm_improve", name=name))
        if self.stt.yes_no(tries=4, timeout=8.0, tts=self.tts) is not True:
            self._say(_t("cancelled"))
            return None

        self._say(_t("improving", name=name))
        self._say(_t("vary_expr_hint"))
        embs = self._capture_with_guidance()
        if len(embs) < 10:
            self._say(_t("not_enough"))
            return None

        self.db.add(name, embs)
        self._say(_t("improved", name=name))
        return f"improved:{name}"

    # â”€â”€ Capture with guidance + beeps â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _capture_with_guidance(self) -> list:
        """
        ÙŠÙ„ØªÙ‚Ø· Ø§Ù„ØµÙˆØ± Ù…Ù† Ø²ÙˆØ§ÙŠØ§ ÙˆØªØ¹Ø¨ÙŠØ±Ø§Øª Ù…Ø®ØªÙ„ÙØ© Ø¹Ù† Ø·Ø±ÙŠÙ‚ ØªÙˆØ¬ÙŠÙ‡ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù… ØµÙˆØªÙŠØ§Ù‹.
        """
        embs = []
        phase_samples = SAMPLES // 4  # 30 ØµÙˆØ±Ø© Ù„ÙƒÙ„ Ù…Ø±Ø­Ù„Ø©
        
        phases = [
            ("straight", _t("look_straight")),
            ("left", _t("look_left")),
            ("right", _t("look_right")),
            ("expression", _t("vary_expression"))
        ]

        for phase_name, instruction in phases:
            self._say(instruction)
            time.sleep(0.25)  # Ù…Ù‡Ù„Ø© Ù‚ØµÙŠØ±Ø© Ù„ÙŠØ³ØªØ¹Ø¯ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…
            
            phase_captured = 0
            # Ù…Ù‡Ù„Ø© Ø£Ù‚ØµØ§Ù‡Ø§ 20 Ø«Ø§Ù†ÙŠØ© Ù„Ù‡Ø°Ù‡ Ø§Ù„Ù…Ø±Ø­Ù„Ø©
            deadline = time.time() + 20.0
            last_beep_time = time.time()
            last_no_face_prompt = 0.0
            
            while phase_captured < phase_samples and time.time() < deadline:
                now = time.time()
                if now - last_beep_time >= 3.0:
                    _beep()
                    last_beep_time = now

                try:
                    frame = self._fq.get(timeout=0.5)
                except queue.Empty:
                    continue

                faces = self.proc.detect(frame)
                if not faces:
                    now = time.time()
                    if now - last_no_face_prompt >= 6.0:
                        self._say(_t("no_face"))
                        last_no_face_prompt = now
                    continue

                # Ù†Ù‚ÙˆÙ… Ø¨ØªØ±ØªÙŠØ¨ Ø§Ù„ÙˆØ¬ÙˆÙ‡ ÙˆØ£Ø®Ø° Ø§Ù„Ø£ÙƒØ¨Ø± Ù…Ø³Ø§Ø­Ø© (Ø§Ù„Ø£Ù‚Ø±Ø¨ Ù„Ù„ÙƒØ§Ù…ÙŠØ±Ø§) Ù„Ø¶Ù…Ø§Ù† Ø§Ù„Ø¯Ù‚Ø©
                faces_sorted = sorted(faces, key=lambda b: b[2] * b[3], reverse=True)
                
                e = self.proc.embed(frame, faces_sorted[0])
                if e is not None:
                    embs.append(e)
                    phase_captured += 1
            
            # beep Ù…Ø²Ø¯ÙˆØ¬ ÙÙŠ Ù†Ù‡Ø§ÙŠØ© Ø§Ù„Ù…Ø±Ø­Ù„Ø© Ù„Ù„ØªÙ‚Ø¯Ù…
            _beep_beep()
            time.sleep(0.1)

        logger.info(f"Captured {len(embs)} embeddings total.")
        return embs

    # â”€â”€ Delete â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _delete(self):
        ns = [n for n in self.db.names() if not n.startswith("__blocked__")]
        if not ns:
            self._say(_t("no_to_delete"))
            return None
        
        # Ù‚Ø±Ø§Ø¡Ø© Ø§Ù„Ù‚Ø§Ø¦Ù…Ø© Ø¨Ø§Ù„Ø£Ø±Ù‚Ø§Ù… Ø§Ù„Ù…ØªØ±ØªØ¨Ø© Ù…Ø¹ Ø®ÙŠØ§Ø± Ø§Ù„ÙƒÙ„
        numbered_list = [f"{i+1} {name}" for i, name in enumerate(ns)]
        is_ar = getattr(config, "LANGUAGE", "en") == "ar"
        if is_ar:
            names_str = "ØŒ ".join(numbered_list) + "ØŒ Ø£Ùˆ Ù‚Ù„ Ø§Ù„ÙƒÙ„ Ù„Ù„Ù…Ø³Ø­ Ø§Ù„ÙƒØ§Ù…Ù„"
        else:
            names_str = ", ".join(numbered_list) + ", or say all to delete everyone"
            
        self._say(_t("say_delete", names=names_str))
        
        matched = None
        for attempt in range(1, 4):
            target = self.stt.get_name(tries=2, timeout=10.0, tts=self.tts)
            if target:
                t_cleaned = target.lower().strip()
                if t_cleaned in ["cancel", "exit", "stop", "close", "Ø§Ù„ØºÙŠ", "Ø§Ù„Øº", "Ø§Ù„ØºØ§Ø¡", "Ø¥Ù„ØºØ§Ø¡", "Ø¨Ù„Ø§Ø´", "Ø®Ø±ÙˆØ¬", "Ø§Ø®Ø±Ø¬"]:
                    self._say(_t("cancelled"))
                    return None
            if not target:
                if attempt < 3:
                    self._say(_t("try_again"))
                    continue
                else:
                    self._say(_t("no_name_heard"))
                    return None
            
            t_cleaned = _normalize_command_text(target)
            if _is_delete_all_command(target):
                if is_ar:
                    self._say("Ù‡Ù„ Ø£Ù†Øª Ù…ØªØ£ÙƒØ¯ ØªÙ…Ø§Ù…Ø§Ù‹ Ù…Ù† Ø±ØºØ¨ØªÙƒ ÙÙŠ Ø­Ø°Ù Ø¬Ù…ÙŠØ¹ Ø§Ù„Ø£Ø³Ù…Ø§Ø¡ Ø§Ù„Ù…Ø³Ø¬Ù„Ø©ØŸ Ù‚Ù„ Ù†Ø¹Ù… Ù„Ù„ØªØ£ÙƒÙŠØ¯.")
                else:
                    self._say("Are you absolutely sure you want to delete all registered names? Say yes to confirm.")
                
                if self.stt.yes_no(tries=4, tts=self.tts) is not True:
                    self._say(_t("cancelled"))
                    return None
                    
                for name in ns:
                    self.db.delete(name)
                    
                if is_ar:
                    self._say("ØªÙ… Ø­Ø°Ù Ø¬Ù…ÙŠØ¹ Ø§Ù„Ø£Ø³Ù…Ø§Ø¡ Ø¨Ù†Ø¬Ø§Ø­.")
                else:
                    self._say("All registered names have been successfully deleted.")
                return "deleted:__all__"
                
            num = _parse_number(target)
            if num is not None and 1 <= num <= len(ns):
                matched = ns[num - 1]
                break
            else:
                matched = next((n for n in ns if n.lower() == target.lower()
                                or target.lower() in n.lower()), None)
                if matched:
                    break
            
            self._say(_t("not_found", name=target))
            if attempt < 3:
                self._say(_t("try_again"))
                
        if not matched:
            return None
            
        self._say(_t("confirm_delete", name=matched))
        if self.stt.yes_no(tries=4, tts=self.tts) is not True:
            self._say(_t("cancelled"))
            return None
            
        self.db.delete(matched)
        self._say(_t("deleted", name=matched))
        return f"deleted:{matched}"

    # â”€â”€ Block â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _block(self):
        return self._do_block()

    def _do_block(self):
        self._say(_t("keep_person"))

        frame = None
        deadline = time.time() + 10.0
        while time.time() < deadline:
            try:
                frame = self._fq.get(timeout=1.0)
                break
            except queue.Empty:
                continue

        if frame is None:
            self._say(_t("no_frame"))
            return None

        faces = self.proc.detect(frame)
        if not faces:
            self._say(_t("no_face"))
            return None

        emb_check = self.proc.embed(frame, faces[0])
        if emb_check is not None:
            db = self.db.all()
            for name, rec in db.items():
                if name.startswith("__blocked__"): continue
                if not rec.embeddings: continue
                stored = np.array(rec.embeddings)
                dists  = 1.0 - (stored @ emb_check)
                top3   = sorted(dists)[:min(3, len(dists))]
                if float(np.mean(top3)) <= 0.45:
                    self._say(_t("already_reg", name=name))
                    return None

        self._say(_t("say_label"))
        label = self.stt.get_name(tries=3, timeout=10.0, tts=self.tts)
        if not label:
            self._say(_t("no_label"))
            return None

        self._say(_t("blocking", name=label))
        embs = self._capture_with_guidance()
        if len(embs) < 10:
            self._say(_t("not_enough"))
            return None

        block_id = f"__blocked__{label}"
        self.db.add(block_id, embs)
        self.blocked.add(block_id)
        save_blocked(self.blocked)
        self._say(_t("blocked", name=label))
        return f"blocked:{label}"

    # â”€â”€ Unblock â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _unblock(self):
        blocked_names = [b.replace("__blocked__", "") for b in self.blocked]
        if not blocked_names:
            self._say(_t("no_blocked"))
            return None
        self._say(_t("say_unblock", names=", ".join(blocked_names)))
        
        matched_id = None
        for attempt in range(1, 4):
            target = self.stt.get_name(tries=2, timeout=10.0, tts=self.tts)
            if target:
                t_cleaned = target.lower().strip()
                if t_cleaned in ["cancel", "exit", "stop", "close", "Ø§Ù„ØºÙŠ", "Ø§Ù„Øº", "Ø§Ù„ØºØ§Ø¡", "Ø¥Ù„ØºØ§Ø¡", "Ø¨Ù„Ø§Ø´", "Ø®Ø±ÙˆØ¬", "Ø§Ø®Ø±Ø¬"]:
                    self._say(_t("cancelled"))
                    return None
            if not target:
                if attempt < 3:
                    self._say(_t("try_again"))
                    continue
                else:
                    self._say(_t("no_name_heard"))
                    return None
            
            matched_id = next(
                (b for b in self.blocked if target.lower() in b.lower()), None)
            if matched_id:
                break
                
            self._say(_t("not_blocked", name=target))
            if attempt < 3:
                self._say(_t("try_again"))
                
        if not matched_id:
            return None
            
        target_name = matched_id.replace("__blocked__", "")
        self._say(_t("confirm_unblock", name=target_name))
        if self.stt.yes_no(tries=4, tts=self.tts) is not True:
            self._say(_t("cancelled"))
            return None
        self.blocked.discard(matched_id)
        self.db.delete(matched_id)
        save_blocked(self.blocked)
        self._say(_t("unblocked", name=target_name))
        return f"unblocked:{target_name}"

    # â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _say(self, text: str):
        self.current_instruction = text
        self.tts.say_wait(text, pause=0.05)

