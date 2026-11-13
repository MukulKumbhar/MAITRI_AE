"""
MAITRI 2.0 — Vision Service Tests
Tests the face crop inference pipeline.
"""

import sys
import os
import io
from pathlib import Path

import numpy as np
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


class TestVisionService:
    def test_error_result_on_empty_bytes(self):
        """Empty bytes should return a neutral error result."""
        from backend.services.vision_service import process_face_crop
        result = process_face_crop(b"not_a_jpeg")
        # Should not raise, should return a neutral fallback
        assert result is not None
        assert "emotion" in result
        assert "probs" in result
        assert set(result["probs"].keys()) == {
            "angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"
        }

    def test_process_synthetic_jpeg(self):
        """Create a valid synthetic JPEG and verify inference runs without crash."""
        from PIL import Image
        import io
        from backend.services.vision_service import process_face_crop

        # Create a 224x224 black JPEG (edge case: no face)
        img = Image.fromarray(np.zeros((224, 224, 3), dtype=np.uint8))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        jpeg_bytes = buf.getvalue()

        result = process_face_crop(jpeg_bytes)
        assert result is not None
        assert "emotion" in result
        assert "probs" in result
        probs = result["probs"]
        # Probs should sum to approximately 1.0
        total = sum(probs.values())
        assert 0.9 <= total <= 1.1, f"Probs should sum to ~1, got {total}"

    def test_facs_action_units_fusion(self):
        """Verify FACS blendshapes modulate dominant emotion and probabilities correctly."""
        from PIL import Image
        import io
        from backend.services.vision_service import process_face_crop

        img = Image.fromarray(np.zeros((224, 224, 3), dtype=np.uint8))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        jpeg_bytes = buf.getvalue()

        # 1. Smile -> happy
        res_smile = process_face_crop(jpeg_bytes, blendshapes={"mouthSmileLeft": 0.85, "mouthSmileRight": 0.82})
        assert res_smile["emotion"] == "happy"
        assert res_smile["probs"]["happy"] > 0.60

        # 2. Surprise -> jaw open + brow inner up
        res_surp = process_face_crop(jpeg_bytes, blendshapes={"jawOpen": 0.88, "browInnerUp": 0.75})
        assert res_surp["emotion"] == "surprise"
        assert res_surp["probs"]["surprise"] > 0.50

        # 3. Anger -> corrugator brow down
        res_ang = process_face_crop(jpeg_bytes, blendshapes={"browDownLeft": 0.85, "browDownRight": 0.82})
        assert res_ang["emotion"] == "angry"
        assert res_ang["probs"]["angry"] >= 0.45

        # 4. Sadness -> mouth frown + brow inner up
        res_sad = process_face_crop(jpeg_bytes, blendshapes={"mouthFrownLeft": 0.80, "mouthFrownRight": 0.78, "browInnerUp": 0.50})
        assert res_sad["emotion"] == "sad"
        assert res_sad["probs"]["sad"] >= 0.45

    def test_model_status_structure(self):
        """get_model_status returns expected keys."""
        from backend.services.vision_service import get_model_status
        status = get_model_status()
        assert "onnx" in status
        assert "deepface" in status
        assert isinstance(status["onnx"], bool)

    def test_error_result_format(self):
        """_error_result returns correctly shaped dict."""
        from backend.services.vision_service import _error_result
        r = _error_result("test error")
        assert r["emotion"] == "neutral"
        assert r["confidence"] == 0.0
        assert r["quality"] == 0.0
        assert r["model"] == "error"
        assert "error" in r
        probs = r["probs"]
        assert abs(sum(probs.values()) - 1.0) < 0.01


class TestVoiceService:
    def test_initial_state(self):
        """VoiceService initializes in non-speaking state."""
        from backend.services.voice_service import VoiceService
        svc = VoiceService()
        assert svc._speaking is False
        assert svc._vosk_ready is False

    def test_rms_computation(self):
        """_compute_rms_int16 produces correct RMS for known signal."""
        from backend.services.voice_service import _compute_rms_int16
        # Constant amplitude signal: RMS should equal amplitude
        samples = tuple([1000] * 100)
        rms = _compute_rms_int16(samples)
        assert abs(rms - 1000.0) < 1.0

    def test_rms_zero_signal(self):
        """Zero signal produces zero RMS."""
        from backend.services.voice_service import _compute_rms_int16
        samples = tuple([0] * 100)
        rms = _compute_rms_int16(samples)
        assert rms == 0.0

    def test_rms_empty(self):
        """Empty samples returns 0."""
        from backend.services.voice_service import _compute_rms_int16
        assert _compute_rms_int16(()) == 0.0
