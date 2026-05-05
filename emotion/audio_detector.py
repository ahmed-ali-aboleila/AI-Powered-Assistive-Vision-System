"""
src/audio_detector.py - Audio emotion detection (fallback)
Used only when face confidence is below 45%
"""
import threading
import numpy as np

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

try:
    import sounddevice as sd
    import librosa
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


class AudioEmotionDetector:
    """
    Records a short audio clip and classifies emotion using:
    - Energy (volume level)
    - Pitch (voice tone)
    - ZCR (Zero Crossing Rate)
    - MFCCs (Mel-frequency cepstral coefficients)
    """

    def __init__(self):
        self.available   = AUDIO_AVAILABLE and config.AUDIO_ENABLED
        self._is_running = False

        if not self.available:
            print("WARNING: Audio not available — running on camera only")

    def analyze_async(self, callback):
        """Record and analyze audio in a background thread (non-blocking)"""
        if not self.available or self._is_running:
            return
        self._is_running = True
        t = threading.Thread(target=self._analyze, args=(callback,), daemon=True)
        t.start()

    def _analyze(self, callback):
        try:
            # Record audio
            audio = sd.rec(
                int(config.AUDIO_RECORD_SEC * config.AUDIO_SAMPLE_RATE),
                samplerate=config.AUDIO_SAMPLE_RATE,
                channels=1,
                dtype='float32',
                device=config.AUDIO_DEVICE_INDEX,
            )
            sd.wait()
            audio = audio.flatten()

            # Classify emotion from audio features
            emotion, confidence = self._classify(audio)
            callback(emotion, confidence)

        except Exception as e:
            print(f"WARNING: Audio error: {e}")
        finally:
            self._is_running = False

    def _classify(self, audio):
        """
        Rule-based emotion classification from audio features
        """
        sr = config.AUDIO_SAMPLE_RATE

        # Energy (RMS)
        energy = float(np.sqrt(np.mean(audio ** 2)))

        # Pitch
        try:
            pitches, mags = librosa.piptrack(y=audio, sr=sr)
            pitch = float(np.mean(pitches[mags > np.median(mags)]))
        except Exception:
            pitch = 0.0

        # Zero Crossing Rate
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(audio)))

        # Classification rules based on audio features
        if energy < 0.01:
            return "Neutral", 0.60

        if energy > 0.15 and pitch > 200:
            return "Happy", 0.65

        if energy > 0.15 and pitch < 150:
            return "Angry", 0.65

        if zcr > 0.1 and energy > 0.05:
            return "Fear", 0.60

        if energy < 0.05 and pitch < 120:
            return "Sad", 0.60

        return "Neutral", 0.55
