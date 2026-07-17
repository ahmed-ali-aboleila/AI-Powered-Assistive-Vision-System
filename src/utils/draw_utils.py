import cv2
import numpy as np
import os
import logging

logger = logging.getLogger(__name__)

# TrueType font paths on Windows and Linux that support Arabic / Unicode
FONT_PATHS = [
    "C:\\Windows\\Fonts\\arial.ttf",
    "C:\\Windows\\Fonts\\tahoma.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
]

def draw_text_unicode(frame: np.ndarray, text: str, position: tuple, font_size: int = 18, color: tuple = (255, 255, 255)) -> np.ndarray:
    """
    Draws text supporting Unicode (including Arabic) on an OpenCV image using Pillow.
    Handles right-to-left layout and character reshaping if arabic_reshaper and python-bidi are present.
    
    frame: cv2 BGR image (numpy array)
    text: text to draw
    position: (x, y) coordinates for bottom-left of the text
    font_size: size of the font
    color: tuple in BGR format (blue, green, red)
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        # Fallback to OpenCV putText if PIL is not installed
        cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, font_size / 24.0, color, 2)
        return frame

    # Reshaping and BiDi processing for Arabic text
    display_text = text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped_text = arabic_reshaper.reshape(text)
        display_text = get_display(reshaped_text)
    except Exception:
        # Fallback if shaping libraries fail or are missing
        pass

    # Find a valid system font
    font_file = None
    for path in FONT_PATHS:
        if os.path.exists(path):
            font_file = path
            break

    try:
        if font_file:
            font = ImageFont.truetype(font_file, font_size)
        else:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # Convert OpenCV BGR to Pillow RGB
    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb_image)
    
    # Prepare Drawing context
    draw = ImageDraw.Draw(pil_image)
    # Convert BGR color to RGB
    rgb_color = (color[2], color[1], color[0])
    
    # Adjust position from OpenCV's baseline to Pillow's top-left
    x, y = position
    y_adjusted = max(0, y - font_size)

    draw.text((x, y_adjusted), display_text, font=font, fill=rgb_color)

    # Convert back to OpenCV BGR
    result_frame = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    # Modifying the original frame content in-place if possible, or returning it
    np.copyto(frame, result_frame)
    return frame
