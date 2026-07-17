# Raspberry Pi Final Checklist

Run these commands on the Raspberry Pi before the demo:

```bash
cd "/home/egb/Desktop/EGB/Face emotin+ Face recognition"
source .venv/bin/activate
git pull
chmod +x run_pi.sh
python tools/rpi_preflight.py
python tools/rpi_deep_test.py
```

The preflight should print `READY`.
The deep test should print `DEEP TEST READY`.

Required files:

- `models/cnn_v3_final.tflite`
- `models/cnn_v3_final.h5`
- `models/vosk-model`
- `models/vosk-model-ar-mgb2-0.4/graph/words.txt`
- `face_data.pkl` after registering people

Run the system:

```bash
VISION_CAMERA_INDEX=0 ./run_pi.sh
```

Run with camera window on the Raspberry Pi screen:

```bash
VISION_CAMERA_INDEX=0 VISION_SHOW_WINDOW=1 ./run_pi.sh
```

Backup registered people after the final registration:

```bash
cp face_data.pkl face_data.backup.pkl
```

If the system feels slow, keep the default `run_pi.sh` settings. They are tuned for Raspberry Pi 4.
