"""
MAITRI 2.0 — Psych Support Router
GET  /api/psych/logs      — dialogue history
POST /api/psych/chat      — submit query to Phi-3 LLM
POST /api/psych/grounding — trigger 4-7-8 protocol
GET  /api/psych/presets   — context-adaptive preset chips
POST /api/psych/init      — initialize the support engine
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from backend.state import get_state
import backend.services.psych_service as psych_service

logger = logging.getLogger("maitri.api.psych")
router = APIRouter(prefix="/api/psych", tags=["psych"])


class ChatRequest(BaseModel):
    query: str
    channel: str = "text"


class GroundingRequest(BaseModel):
    crew: str = "Astronaut"
    stress: float = 0.0


class InitRequest(BaseModel):
    config: Optional[dict] = None


@router.post("/init")
async def initialize_engine(req: InitRequest):
    """Load Phi-3 Mini + Whisper + Piper TTS models on demand."""
    success, message = await asyncio.to_thread(psych_service.initialize_engine, req.config)
    return {"success": success, "message": message, "is_loaded": psych_service.is_loaded()}


@router.get("/status")
async def engine_status():
    """Return current Phase 2 engine status."""
    return {
        "is_loaded": psych_service.is_loaded(),
        "error": psych_service.get_load_error(),
    }


@router.get("/logs")
async def get_psych_logs(limit: int = 50):
    """Return psychological dialogue history."""
    try:
        from modules.database_module import get_psych_logs
        df = get_psych_logs(limit=limit)
        return {"records": df.to_dict(orient="records"), "count": len(df)}
    except Exception as exc:
        logger.error("get_psych_logs error: %s", exc)
        return {"records": [], "count": 0, "error": str(exc)}


@router.post("/chat")
async def chat(req: ChatRequest):
    """Submit astronaut query to Phi-3 LLM + Piper TTS."""
    state = get_state()
    result = await psych_service.chat(req.query, req.channel, state)
    return result


@router.post("/grounding")
async def grounding(req: GroundingRequest):
    """Trigger immediate 4-7-8 guided grounding protocol."""
    result = await psych_service.grounding(req.crew, req.stress)
    return result


@router.get("/presets")
async def get_presets():
    """Return context-adaptive preset chips (2 permanent + 4 adaptive)."""
    state = get_state()
    stress_pct = getattr(state.fusion, "last_stress", 0.0)
    emotion = getattr(state.fusion, "last_emotion", "neutral")
    presets = psych_service.get_evolved_presets(stress_pct, emotion)
    return {"presets": presets}
