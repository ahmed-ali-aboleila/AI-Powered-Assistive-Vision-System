from pathlib import Path

import numpy as np


class TFLiteEmotionModel:
    """Small predict-compatible wrapper around a TFLite emotion model."""

    def __init__(self, model_path: str):
        try:
            from ai_edge_litert.interpreter import Interpreter
            interpreter_cls = Interpreter
        except ImportError:
            try:
                import tflite_runtime.interpreter as tflite
                interpreter_cls = tflite.Interpreter
            except ImportError:
                try:
                    import tensorflow as tf
                    interpreter_cls = tf.lite.Interpreter
                except ImportError as exc:
                    raise RuntimeError(
                        "TFLite runtime is not installed. Install ai-edge-litert, "
                        "tflite-runtime, or tensorflow, or disable USE_TFLITE_EMOTION."
                    ) from exc

        try:
            self._interpreter = interpreter_cls(model_path=model_path)
        except TypeError:
            try:
                self._interpreter = interpreter_cls(model_content=Path(model_path).read_bytes())
            except TypeError as exc:
                raise RuntimeError(
                    "This TensorFlow Lite interpreter is incompatible with the current "
                    "Python/TensorFlow build. On Raspberry Pi install tflite-runtime "
                    "or ai-edge-litert, or set VISION_USE_TFLITE=0 to use the .h5 model."
                ) from exc
        self._interpreter.allocate_tensors()
        self._input = self._interpreter.get_input_details()[0]
        self._output = self._interpreter.get_output_details()[0]

    def predict(self, batch, verbose: int = 0):
        x = np.asarray(batch)
        input_dtype = self._input["dtype"]
        output_dtype = self._output["dtype"]
        input_scale, input_zero = self._input.get("quantization", (0.0, 0))
        output_scale, output_zero = self._output.get("quantization", (0.0, 0))
        outputs = []

        for sample in x:
            sample = np.expand_dims(sample, axis=0)
            if input_dtype != sample.dtype:
                if np.issubdtype(input_dtype, np.integer) and input_scale:
                    sample = sample / input_scale + input_zero
                    sample = np.clip(
                        np.rint(sample),
                        np.iinfo(input_dtype).min,
                        np.iinfo(input_dtype).max,
                    )
                sample = sample.astype(input_dtype)

            self._interpreter.set_tensor(self._input["index"], sample)
            self._interpreter.invoke()
            pred = self._interpreter.get_tensor(self._output["index"])[0]
            if np.issubdtype(output_dtype, np.integer) and output_scale:
                pred = (pred.astype("float32") - output_zero) * output_scale
            outputs.append(pred.astype("float32"))

        return np.stack(outputs, axis=0)
