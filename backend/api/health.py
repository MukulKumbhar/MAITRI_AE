"""
MAITRI 2.0 — Health Check Router
GET /api/health
"""

import os
import sys
from pathlib import Path

from fastapi import APIRouter

from backend.state import get_state
from backend.services.vision_service import get_model_status

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check():
    """
    System health and model availability status.
    Returns status of all ONNX models and backend services.
    """
    state = get_state()
    model_status = get_model_status()

    # Check model files on disk
    project_root = state.get_project_root()
    model_files = {
        "enet_b2_7": (project_root / "models" / "enet_b2_7.onnx").exists(),
        "enet_b0_fallback": (project_root / "models" / "enet_b0_8_best_vgaf.onnx").exists(),
        "face_landmarker": (
            (project_root / "models" / "face_landmarker.task").exists() or
            (project_root / "face_landmarker.task").exists()
        ),
        "wav2vec2_ser": (project_root / "models" / "wav2vec2_ser_q4.onnx").exists(),
        "piper_tts": (project_root / "models" / "piper_voice" / "en_US-lessac-medium.onnx").exists(),
        "phi3_llm": (project_root / "models" / "phi3_mini_q4.gguf").exists(),
        "vosk": (project_root / "models" / "vosk").exists(),
        "whisper": (project_root / "models" / "whisper_tiny_en").exists(),
    }

    from backend.services import psych_service
    return {
        "status": "ok",
        "version": "2.0.0",
        "models_loaded": {
            "face_onnx": model_status.get("onnx", False),
            "psych_engine": psych_service.is_loaded(),
            "vosk_asr": state.vosk_ready,
        },
        "models_on_disk": model_files,
        "mission": state.mission_name,
        "crew": state.active_crew,
    }
