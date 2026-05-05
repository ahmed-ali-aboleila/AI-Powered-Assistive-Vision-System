"""
logic_controller.py - Brain of the Assistive Vision System
===========================================================
Multi-face support:
  - Detects ALL faces in frame
  - Announces them one by one, closest first (largest box)
  - Waits for TTS to finish before announcing next person
  - Only announces when emotion changes
"""

import time
import threading
import logging

import config

logger = logging.getLogger(__name__)


class LogicController:

    def __init__(self, tts, stt, reg_flow, face_processor, face_db):
        self.tts  = tts
        self.stt  = stt
        self.reg  = reg_flow
        self.proc = face_processor
        self.db   = face_db

        # Per-person tracking
        self._last_announced  = {}  # {name: last_time}
        self._last_seen       = {}  # {name: last_time}
        self._last_emotion    = {}  # {name: emotion}

        # Current closest person (for voice commands)
        self._current_name    = None
        self._current_emotion = None

        # Announcement queue — one at a time
        self._announce_queue  = []
        self._announcing      = False

        # Low light warning once per session
        self._low_light_warned = False

        # Wake word listener flag
        self._processing_command = False

        threading.Timer(5.0, self._start_command_listener).start()
        print("      Logic Controller ready.")

    # ── Announcement Queue ────────────────────────────────────────────────────

    def _queue_announcement(self, msg: str):
        """Add message to queue — plays after current speech finishes"""
        self._announce_queue.append(msg)
        if not self._announcing:
            threading.Thread(target=self._flush_queue, daemon=True).start()

    def _flush_queue(self):
        """Process announcement queue one by one"""
        self._announcing = True
        while self._announce_queue:
            if self.tts.busy():
                time.sleep(0.2)
                continue
            msg = self._announce_queue.pop(0)
            self.tts.say(msg)
            # Wait for this message to finish before next
            time.sleep(0.3)
            self.tts.wait(timeout=10.0)
        self._announcing = False

    # ── Wake Word Command Listener ────────────────────────────────────────────

    def _start_command_listener(self):
        def _loop():
            while True:
                try:
                    if self.reg.active or self.tts.busy() or self._processing_command:
                        time.sleep(0.3)
                        continue

                    text = self.stt.listen(timeout=4.0, phrase_limit=3.0)
                    if not text:
                        continue

                    if "vision" not in text.lower():
                        continue

                    self._processing_command = True
                    # Clear queue before responding to command
                    self._announce_queue.clear()
                    self.tts.say_wait("Yes?", pause=0.5)

                    command = self.stt.listen(timeout=6.0, phrase_limit=5.0)
                    if not command:
                        self.tts.say_wait("I did not hear a command.")
                    else:
                        self._handle_command(command.lower())

                except Exception as e:
                    logger.debug(f"Command listener: {e}")
                    time.sleep(0.5)
                finally:
                    self._processing_command = False

        threading.Thread(target=_loop, daemon=True).start()

    # ── Command Handler ───────────────────────────────────────────────────────

    def _handle_command(self, text: str):

        if "register" in text or "save" in text or "add" in text:
            if self._current_name is None:
                self.tts.say_wait("No person detected.")
            elif self._current_name != "Unknown":
                self.tts.say_wait(f"{self._current_name} is already registered.")
            else:
                self.reg.start_register()
            return

        if "unblock" in text:
            self.reg.start_unblock()
            return

        if "block" in text or "ban" in text:
            if self._current_name is None:
                self.tts.say_wait("No person detected.")
            elif self._current_name != "Unknown":
                self.tts.say_wait("Cannot block a registered person. Use delete instead.")
            else:
                self.reg.start_block()
            return

        if "who" in text:
            if self._current_name is None or self._current_name == "Unknown":
                emotion = self._current_emotion or "unknown emotion"
                self.tts.say_wait(f"Unknown person, they look {emotion}.")
            else:
                emotion = self._current_emotion or "unknown emotion"
                self.tts.say_wait(f"{self._current_name} looks {emotion}.")
            return

        if "delete" in text or "remove" in text:
            self.reg.start_delete()
            return

        if "list" in text:
            names = [n for n in self.db.names()
                     if not n.startswith("__blocked__")]
            if names:
                self.tts.say_wait(f"Registered persons: {', '.join(names)}.")
            else:
                self.tts.say_wait("No registered persons.")
            return

        if "quiet" in text or "silence" in text or "mute" in text:
            self._announce_queue.clear()
            self.tts.set_quiet(True)
            self.tts.say_wait("Quiet mode on.")
            return

        if "speak" in text or "resume" in text or "unmute" in text:
            self.tts.set_quiet(False)
            self.tts.say_wait("Resuming.")
            return

        if "stop" in text:
            self._announce_queue.clear()
            self.tts.stop()
            return

        self.tts.say_wait("Command not recognized. Please try again.")

    # ── Main Process (called per face per frame) ──────────────────────────────

    def process_faces(self, faces_data: list, brightness: float, frame=None) -> str:
        """
        Process multiple faces at once.
        faces_data: list of (face_id, name, rec_score, emotion, emo_conf, box_area)
                    already sorted by box_area descending (closest first)
        """
        now = time.time()

        if frame is not None and self.reg.active:
            self.reg.feed(frame)

        # Low light warning once
        if brightness < config.BRIGHTNESS_THRESHOLD and not self._low_light_warned:
            self._low_light_warned = True
            self._queue_announcement("Low light detected. Relying on audio analysis.")

        if not faces_data:
            self._current_name    = None
            self._current_emotion = None
            return "no_face"

        # Update current = closest person (index 0)
        self._current_name    = faces_data[0][1]
        self._current_emotion = faces_data[0][3]

        # Process each face
        for face_id, name, rec_score, emotion, emo_conf, box_area in faces_data:
            if name.startswith("__blocked__"):
                continue
            if name != "Unknown":
                self._process_known(name, rec_score, emotion, now)
            else:
                self._process_unknown(face_id, emotion, now)

        return "processed"

    # ── Single face process (kept for backward compatibility) ─────────────────

    def process(self, face_id: str, name: str, recognition_score: float,
                emotion: str, emotion_confidence: float,
                brightness: float, frame=None) -> str:
        """Single face wrapper — calls process_faces internally"""
        faces_data = [(face_id, name, recognition_score,
                       emotion, emotion_confidence, 1)]
        return self.process_faces(faces_data, brightness, frame)

    # ── Known Person ──────────────────────────────────────────────────────────

    def _process_known(self, name: str, score: float,
                       emotion: str, now: float):

        last_seen     = self._last_seen.get(name, 0)
        just_returned = (now - last_seen) > config.UNKNOWN_REASK_TIMEOUT
        self._last_seen[name] = now

        last_announced  = self._last_announced.get(name, 0)
        last_emotion    = self._last_emotion.get(name, "")
        cooldown_passed = (now - last_announced) >= config.TTS_COOLDOWN_SEC
        emotion_changed = (emotion != last_emotion)

        if just_returned or (emotion_changed and cooldown_passed):
            self._last_announced[name] = now
            self._last_emotion[name]   = emotion

            if score >= 0.75:
                msg = f"{name} looks {emotion}"
            else:
                msg = f"I think this is {name}, they look {emotion}"

            self._queue_announcement(msg)

    # ── Unknown Person ────────────────────────────────────────────────────────

    def _process_unknown(self, face_id: str, emotion: str, now: float):

        key             = f"unknown_{face_id}"
        last_announced  = self._last_announced.get(key, 0)
        last_emotion    = self._last_emotion.get(key, "")
        cooldown_passed = (now - last_announced) >= config.TTS_COOLDOWN_SEC
        emotion_changed = (emotion != last_emotion)

        if emotion_changed and cooldown_passed:
            self._last_announced[key] = now
            self._last_emotion[key]   = emotion
            self._queue_announcement(f"Unknown person, they look {emotion}")

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def on_person_left(self, name: str):
        self._last_announced.pop(name, None)
        self._last_emotion.pop(name, None)

    def on_registered(self, name: str):
        emotion = self._current_emotion or "Neutral"
        self._announce_queue.clear()
        self._queue_announcement(f"{name} looks {emotion}")
        self._last_announced[name] = time.time()
        self._last_seen[name]      = time.time()
        self._last_emotion[name]   = emotion
