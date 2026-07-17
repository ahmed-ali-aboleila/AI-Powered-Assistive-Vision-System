# GitHub Release Checklist

Use this checklist before pushing the project to a new GitHub repository.

## Required Checks

- Run `python -m py_compile main.py config.py logic_controller.py shared/stt.py shared/tts.py shared/draw_utils.py face/face_db.py face/face_processor.py face/registration.py emotion/audio_detector.py emotion/display.py emotion/face_detector.py test_speech_and_commands.py`
- Run `python test_speech_and_commands.py`
- Confirm Raspberry Pi setup files exist: `install_pi.sh`, `run_pi.sh`, `download_models.sh`, `requirements-pi.txt`, `tools/rpi_preflight.py`.
- Confirm `face_data.pkl` is not staged.
- Confirm `blocked.json` is not staged.
- Confirm `logs/` is not staged.
- Confirm `tts_cache/` is not staged.
- Confirm `models/` is not staged.
- Confirm training folders `cnn_v3/`, `cnn_v6/`, and `ensemble/` are not staged unless you explicitly want to publish training artifacts.

## Recommended Git Commands

For a clean new repository:

```bash
git init
git add .
git status
git commit -m "Initial assistive vision system release"
git branch -M main
git remote add origin <NEW_REPOSITORY_URL>
git push -u origin main
```

If using this existing repository history, remove tracked generated artifacts from the index first:

```bash
git rm --cached -r cnn_v3 cnn_v6 ensemble
git status
```

## Large Files

Share large model files separately through Google Drive or GitHub Releases:

- `models/cnn_v3_final.h5`
- `models/cnn_v3_final.tflite`
- `models/vosk-model/`
- `models/vosk-model-ar-mgb2-0.4/`

Current Google Drive folder:

```text
https://drive.google.com/drive/folders/1XIOsn-erryTL9f5AB7jxJTJ5kEhGC1cL?usp=drive_link
```

Do not publish personal biometric data:

- `face_data.pkl`
- `blocked.json`
