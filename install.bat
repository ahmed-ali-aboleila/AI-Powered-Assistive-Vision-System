@echo off
echo ============================================
echo   Assistive Vision System — Install
echo ============================================
py -3.12 -m pip install opencv-python numpy pyttsx3 SpeechRecognition pyaudio scikit-image deepface tf-keras tensorflow mtcnn sounddevice librosa pywin32
echo.
echo Done! Copy emotion_fixed.h5 into models/ folder then run: run.bat
pause
