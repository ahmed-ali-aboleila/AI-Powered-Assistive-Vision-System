"""
registration.py — v6
"""
import time, queue, threading, logging, json, os
import numpy as np
from shared.tts          import TTS
from shared.stt          import STT
from face.face_db        import FaceDB
from face.face_processor import FaceProcessor

logger   = logging.getLogger(__name__)
SAMPLES  = 80
TIMEOUT  = 50.0

BLOCK_FILE = "blocked.json"

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

    @property
    def active(self): return self._active

    def start_register(self): self._go("register")
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
            elif self._mode == "delete":   r = self._delete()
            elif self._mode == "block":    r = self._block()
            elif self._mode == "unblock":  r = self._unblock()
        except Exception as e:
            logger.error(f"RegFlow: {e}", exc_info=True)
        finally:
            self._rq.put(r); self._active = False

    # ── Register ──────────────────────────────────────────────────────────────

    def _register(self):
        # Go directly to name — no yes/no question needed
        name = None
        for attempt in range(1, 4):
            self._say("Please say the name of this person.")
            heard = self.stt.get_name(tries=1, timeout=10.0)
            if not heard:
                if attempt < 3:
                    self._say("I did not hear. Please try again.")
                continue
            self._say(f"I heard {heard}. Correct? Say yes or no.")
            ok = self.stt.yes_no(tries=3, timeout=8.0)
            if ok is True:
                name = heard
                break
            self._say("Let us try again.")

        if not name:
            self._say("Could not get a name. Cancelled.")
            return None

        self._say(
            f"Registering {name}. "
            "Please slowly turn your head left and right "
            "while looking at the camera."
        )
        embs = self._capture()
        if len(embs) < 15:
            self._say("Not enough photos. Please try again.")
            return None

        self.db.add(name, embs)
        self._say(f"{name} registered successfully.")
        return f"registered:{name}"

    # ── Delete ────────────────────────────────────────────────────────────────

    def _delete(self):
        ns = [n for n in self.db.names() if not n.startswith("__blocked__")]
        if not ns:
            self._say("No registered persons to delete.")
            return None
        self._say(f"Registered persons: {', '.join(ns)}. Say the name to delete.")
        target = self.stt.get_name(tries=3, timeout=10.0)
        if not target:
            self._say("No name heard. Cancelled.")
            return None
        matched = next((n for n in ns if n.lower() == target.lower()
                        or target.lower() in n.lower()), None)
        if not matched:
            self._say(f"Could not find {target}. Cancelled.")
            return None
        self._say(f"Delete {matched}? Say yes or no.")
        if self.stt.yes_no(tries=3) is not True:
            self._say("Cancelled.")
            return None
        self.db.delete(matched)
        self._say(f"{matched} deleted.")
        return f"deleted:{matched}"

    # ── Block ─────────────────────────────────────────────────────────────────

    def _block(self):
        return self._do_block()

    def _do_block(self):
        self._say("Please keep the person in front of the camera.")

        frame = None
        deadline = time.time() + 10.0
        while time.time() < deadline:
            try:
                frame = self._fq.get(timeout=1.0)
                break
            except queue.Empty:
                continue

        if frame is None:
            self._say("No frame received. Cancelling.")
            return None

        faces = self.proc.detect(frame)
        if not faces:
            self._say("No face detected. Please stand in front of the camera.")
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
                    self._say(
                        f"This person is already registered as {name}. "
                        "You cannot block a registered person."
                    )
                    return None

        self._say("Say a label for this person.")
        label = self.stt.get_name(tries=3, timeout=10.0)
        if not label:
            self._say("No label heard. Cancelling.")
            return None

        self._say(f"Blocking {label}. Please stay still.")
        embs = self._capture()
        if len(embs) < 10:
            self._say("Not enough photos. Cancelled.")
            return None

        block_id = f"__blocked__{label}"
        self.db.add(block_id, embs)
        self.blocked.add(block_id)
        save_blocked(self.blocked)
        self._say(f"{label} has been blocked.")
        return f"blocked:{label}"

    # ── Unblock ───────────────────────────────────────────────────────────────

    def _unblock(self):
        blocked_names = [b.replace("__blocked__", "") for b in self.blocked]
        if not blocked_names:
            self._say("No blocked persons.")
            return None
        self._say(f"Blocked persons: {', '.join(blocked_names)}. Say the name to unblock.")
        target = self.stt.get_name(tries=3, timeout=10.0)
        if not target:
            self._say("No name heard. Cancelled.")
            return None
        matched_id = next(
            (b for b in self.blocked if target.lower() in b.lower()), None)
        if not matched_id:
            self._say(f"Could not find {target} in blocked list.")
            return None
        self._say(f"Unblock {target}? Say yes or no.")
        if self.stt.yes_no(tries=3) is not True:
            self._say("Cancelled.")
            return None
        self.blocked.discard(matched_id)
        self.db.delete(matched_id)
        save_blocked(self.blocked)
        self._say(f"{target} has been unblocked.")
        return f"unblocked:{target}"

    # ── Capture ───────────────────────────────────────────────────────────────

    def _capture(self) -> list:
        embs = []
        deadline = time.time() + TIMEOUT
        while len(embs) < SAMPLES:
            if time.time() > deadline: break
            try: frame = self._fq.get(timeout=1.0)
            except queue.Empty: continue
            faces = self.proc.detect(frame)
            if not faces: continue
            e = self.proc.embed(frame, faces[0])
            if e is not None: embs.append(e)
        logger.info(f"Captured {len(embs)} embeddings.")
        return embs

    def _say(self, text: str):
        self.tts.say_wait(text, pause=1.2)
