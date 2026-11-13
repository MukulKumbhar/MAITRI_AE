"""
MAITRI 2.0 — Settings Router
GET  /api/settings — return current audio + fusion configuration
POST /api/settings — update mic gain, VAD thresholds, fusion mode
"""

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from backend.state import get_state

logger = logging.getLogger("maitri.api.settings")
router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsRequest(BaseModel):
    mic_gain: Optional[float] = None
    silence_threshold: Optional[float] = None
    manual_override: Optional[bool] = None
    manual_face_ratio: Optional[float] = None
    auto_log_enabled: Optional[bool] = None


@router.get("")
async def get_settings():
    """Return current audio and fusion configuration."""
    state = get_state()
    return {
        "mic_gain": state.mic_gain,
        "silence_threshold": state.silence_threshold,
        "manual_override": state.manual_override,
        "manual_face_ratio": state.manual_face_ratio,
        "auto_log_enabled": state.auto_log_enabled,
    }


@router.post("")
async def update_settings(req: SettingsRequest):
    """Update audio and fusion configuration settings."""
    state = get_state()
    updated = {}

    if req.mic_gain is not None:
        state.mic_gain = max(0.5, min(3.0, req.mic_gain))
        updated["mic_gain"] = state.mic_gain

    if req.silence_threshold is not None:
        state.silence_threshold = max(0.005, min(0.080, req.silence_threshold))
        updated["silence_threshold"] = state.silence_threshold

    if req.manual_override is not None:
        state.manual_override = req.manual_override
        updated["manual_override"] = state.manual_override

    if req.manual_face_ratio is not None:
        state.manual_face_ratio = max(0.0, min(1.0, req.manual_face_ratio))
        updated["manual_face_ratio"] = state.manual_face_ratio

    if req.auto_log_enabled is not None:
        state.auto_log_enabled = req.auto_log_enabled
        updated["auto_log_enabled"] = state.auto_log_enabled

    return {"status": "saved", "updated": updated}
