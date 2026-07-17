"""
src/display.py - Draw results on screen
"""
import cv2
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from shared.draw_utils import draw_text_unicode


def draw_results(frame, emotion, confidence, face_box, source):
    """
    Draw on frame:
    - Rectangle around face
    - Emotion label
    - Confidence percentage
    - Source indicator (CAM or MIC)
    - Confidence bar at bottom
    """
    h, w   = frame.shape[:2]
    color  = config.EMOTION_COLORS.get(emotion, (255, 255, 255))

    # Draw face rectangle
    if face_box is not None:
        x, y, bw, bh = face_box
        cv2.rectangle(frame, (x, y), (x+bw, y+bh), color, 2)

    # Draw info bar at bottom
    bar_h   = 80
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - bar_h), (w, h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Confidence progress bar
    bar_w = int(w * confidence)
    cv2.rectangle(frame, (0, h - 6), (bar_w, h), color, -1)

    # Text labels
    conf_txt = f"{confidence*100:.0f}%"
    src_txt  = "CAM" if source == "face" else "MIC"

    frame = draw_text_unicode(frame, emotion, (10, h - bar_h + 25), 24, color)
    frame = draw_text_unicode(frame, conf_txt, (10, h - bar_h + 55), 18, (200, 200, 200))
    frame = draw_text_unicode(frame, src_txt, (w - 70, h - bar_h + 25), 18, color)

    return frame


def draw_no_face(frame):
    """Draw message when no face is detected"""
    h, w = frame.shape[:2]
    frame = draw_text_unicode(frame, "No face detected",
                              (w//2 - 120, h//2), 22, (100, 100, 255))
    return frame


def draw_fps(frame, fps):
    """Draw FPS counter in top-left corner"""
    cv2.putText(frame, f"FPS: {fps:.0f}",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
    return frame
