"""
convert_model.py - Convert old Keras model to new format
Run this once to fix compatibility issues.
"""
import tensorflow as tf
import os

OLD_MODEL = "models/emotion_cnn.keras"
NEW_MODEL = "models/emotion_model_fixed.keras"

print("Loading old model...")
# Try to load with safe mode
model = tf.keras.models.load_model(OLD_MODEL, compile=False, safe_mode=False)

print("Model loaded successfully!")
print(model.summary())

# Save in new format
print(f"\nSaving as: {NEW_MODEL}")
model.save(NEW_MODEL)

print("\nDone! Now update config.py:")
print(f'  MODEL_PATH = "{NEW_MODEL}"')
