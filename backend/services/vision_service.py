"""
MAITRI 2.0 — Vision Service
Wraps EfficientNet ONNX face emotion inference.
Called from /ws/video-crop WebSocket handler on each received face crop.
"""

import io
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger("maitri.vision")

# ── Path setup ────────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent.parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# ── Lazy imports ──────────────────────────────────────────────────────────────
_face_module = None


def _get_face_module():
    global _face_module
    if _face_module is None:
        try:
            import modules.face_module as fm
            _face_module = fm
            logger.info("Face module loaded OK")
        except Exception as exc:
            logger.error("Failed to load face_module: %s", exc)
    return _face_module


def process_face_crop(
    jpeg_bytes: bytes,
    is_smiling: bool = False,
    smile_score: float = 0.0,
    blendshapes: Optional[Dict[str, float]] = None,
) -> Optional[Dict]:
    """
    Accept a JPEG-encoded face crop (128x128 or 224x224) from the browser,
    run EfficientNet ONNX inference, fuse geometric FACS blendshapes, and return:
      - emotion: str (dominant emotion)
      - probs: Dict[str, float] (7-class normalized probabilities [0, 1])
      - confidence: float (dominant class probability)
      - quality: float (face quality score for fusion gating)
      - model: str ("onnx_efficientnet" | "deepface" | "error")
    """
    fm = _get_face_module()
    if fm is None:
        return _error_result("face_module unavailable")

    try:
        import cv2
        from PIL import Image
        img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
        frame_rgb = np.array(img)
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

        # 1. Initialize & retrieve ONNX session (primary AffectNet model)
        sess = fm._get_onnx_session() if hasattr(fm, "_get_onnx_session") else getattr(fm, "_onnx_session", None)
        if sess is not None and hasattr(fm, "_predict_onnx"):
            dominant, probs_dict, conf = fm._predict_onnx(frame_bgr)

            # Apply FACS Geometric Action Unit Fusion
            bs = blendshapes or {}
            bs_smile = max(
                smile_score,
                bs.get("mouthSmileLeft", 0.0),
                bs.get("mouthSmileRight", 0.0),
            )
            bs_cheek = max(
                bs.get("cheekSquintLeft", 0.0),
                bs.get("cheekSquintRight", 0.0),
            )
            active_smile = is_smiling or (bs_smile >= 0.32) or (bs_smile >= 0.22 and bs_cheek >= 0.18)

            if active_smile and hasattr(fm, "fuse_facs_with_deep_emotion"):
                effective_smile = max(0.65, bs_smile)
                dominant, probs_dict, conf, _ = fm.fuse_facs_with_deep_emotion(
                    dominant, probs_dict, conf, True, effective_smile, effective_smile * 0.8
                )
            elif bs:
                # Surprise: jawOpen (AU26/27) + browInnerUp (AU1) + eyeWide (AU5)
                jaw_open = bs.get("jawOpen", 0.0)
                brow_up = bs.get("browInnerUp", 0.0)
                eye_wide = max(bs.get("eyeWideLeft", 0.0), bs.get("eyeWideRight", 0.0))
                if jaw_open >= 0.32 or (jaw_open >= 0.20 and (brow_up >= 0.25 or eye_wide >= 0.25)):
                    surp_val = max(jaw_open * 110.0, brow_up * 90.0, eye_wide * 90.0)
                    probs_dict["surprise"] = max(probs_dict.get("surprise", 0.0), surp_val)
                    if probs_dict["surprise"] > probs_dict.get(dominant, 0.0):
                        dominant = "surprise"
                        conf = min(0.95, probs_dict["surprise"] / 100.0)

                # Anger: Corrugator browDown (AU4)
                brow_down = max(bs.get("browDownLeft", 0.0), bs.get("browDownRight", 0.0))
                if brow_down >= 0.28:
                    anger_val = min(98.0, max(85.0, brow_down * 125.0))
                    probs_dict["angry"] = max(probs_dict.get("angry", 0.0), anger_val)
                    if probs_dict["angry"] > probs_dict.get(dominant, 0.0):
                        dominant = "angry"
                        conf = min(0.95, probs_dict["angry"] / 100.0)

                # Sadness: mouthFrown (AU15) + browInnerUp (AU1)
                mouth_frown = max(bs.get("mouthFrownLeft", 0.0), bs.get("mouthFrownRight", 0.0))
                if mouth_frown >= 0.25 or (mouth_frown >= 0.16 and brow_up >= 0.22):
                    sad_val = min(92.0, max(mouth_frown * 115.0, brow_up * 85.0))
                    probs_dict["sad"] = max(probs_dict.get("sad", 0.0), sad_val)
                    if probs_dict["sad"] > probs_dict.get(dominant, 0.0):
                        dominant = "sad"
                        conf = min(0.95, probs_dict["sad"] / 100.0)

                # Disgust: noseSneer (AU9)
                nose_sneer = max(bs.get("noseSneerLeft", 0.0), bs.get("noseSneerRight", 0.0))
                if nose_sneer >= 0.28:
                    disgust_val = min(92.0, nose_sneer * 115.0)
                    probs_dict["disgust"] = max(probs_dict.get("disgust", 0.0), disgust_val)
                    if probs_dict["disgust"] > probs_dict.get(dominant, 0.0):
                        dominant = "disgust"
                        conf = min(0.95, probs_dict["disgust"] / 100.0)

                # Fear: eyeWide (AU5) + browInnerUp (AU1)
                if eye_wide >= 0.32 and brow_up >= 0.28 and jaw_open < 0.25:
                    fear_val = min(90.0, eye_wide * 110.0)
                    probs_dict["fear"] = max(probs_dict.get("fear", 0.0), fear_val)
                    if probs_dict["fear"] > probs_dict.get(dominant, 0.0):
                        dominant = "fear"
                        conf = min(0.95, probs_dict["fear"] / 100.0)

            # Normalize probs from 0–100 scale to 0.0–1.0 scale
            probs_norm = {k: round(float(v) / 100.0, 4) for k, v in probs_dict.items()}
            # Ensure probabilities sum to 1.0
            tot = sum(probs_norm.values())
            if tot > 0:
                probs_norm = {k: round(v / tot, 4) for k, v in probs_norm.items()}

            quality = min(1.0, max(0.50, float(conf) * 1.30))
            return {
                "emotion": str(dominant).lower(),
                "probs": probs_norm,
                "confidence": round(float(conf), 4),
                "quality": round(float(quality), 4),
                "model": "onnx_efficientnet",
            }

        # Fallback: DeepFace (if ONNX not found)
        if hasattr(fm, "_predict_deepface"):
            result = fm._predict_deepface(frame_bgr)
            if result:
                dominant = result.get("dominant_emotion", "neutral")
                probs = result.get("emotion_probs", {})
                confidence = float(probs.get(dominant, 0.5))
                return {
                    "emotion": str(dominant).lower(),
                    "probs": {k: round(float(v) / (100.0 if max(probs.values(), default=1) > 1 else 1.0), 4) for k, v in probs.items()},
                    "confidence": round(confidence, 4),
                    "quality": round(min(1.0, confidence * 1.1), 4),
                    "model": "deepface",
                }

        return _error_result("no inference backend available")

    except Exception as exc:
        logger.warning("Vision inference error: %s", exc)
        return _error_result(str(exc))


def _error_result(msg: str) -> Dict:
    """Return a neutral-state result when inference fails."""
    return {
        "emotion": "neutral",
        "probs": {
            "angry": 0.0, "disgust": 0.0, "fear": 0.0,
            "happy": 0.0, "neutral": 1.0, "sad": 0.0, "surprise": 0.0,
        },
        "confidence": 0.0,
        "quality": 0.0,
        "model": "error",
        "error": msg,
    }


def get_model_status() -> Dict:
    """Return current face model availability status."""
    fm = _get_face_module()
    if fm is None:
        return {"onnx": False, "deepface": False}

    sess = fm._get_onnx_session() if hasattr(fm, "_get_onnx_session") else getattr(fm, "_onnx_session", None)
    onnx_ok = sess is not None
    deepface_ok = True  # DeepFace availability is checked at runtime

    return {
        "onnx": onnx_ok,
        "deepface": deepface_ok,
        "model_path": str(getattr(fm, "ONNX_MODEL_PATH", "unknown")),
    }
