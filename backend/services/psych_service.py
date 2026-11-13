"""
MAITRI 2.0 — Psych Service
Wraps Phase2Manager (Phi-3 LLM + Whisper ASR + Piper TTS) with lazy loading.
Keeps the heavyweight models out of the startup path.
"""

import asyncio
import base64
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("maitri.psych")

_HERE = Path(__file__).resolve().parent.parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# ── Lazy Phase2Manager ────────────────────────────────────────────────────────
_phase2_manager = None
_phase2_loaded: bool = False
_phase2_error: Optional[str] = None


def get_phase2_manager():
    return _phase2_manager


def is_loaded() -> bool:
    return _phase2_loaded


def get_load_error() -> Optional[str]:
    return _phase2_error


def initialize_engine(config: Optional[Union[dict, Any]] = None) -> Tuple[bool, str]:
    """
    Load Phi-3 Mini + Whisper + Piper TTS models.
    This is called on demand when the user clicks "Initialize Support Engine".
    Returns (success, message).
    """
    global _phase2_manager, _phase2_loaded, _phase2_error

    if _phase2_loaded:
        return True, "Engine already initialized."

    try:
        from modules.phase2_core import Phase2Manager, Phase2Config
        mgr = Phase2Manager()
        if isinstance(config, Phase2Config):
            cfg = config
        elif isinstance(config, dict):
            import dataclasses
            valid_fields = {f.name for f in dataclasses.fields(Phase2Config)}
            known_args = {k: v for k, v in config.items() if k in valid_fields}
            cfg = Phase2Config(**known_args)
        else:
            cfg = Phase2Config()

        mgr.load_models(cfg)
        _phase2_manager = mgr
        _phase2_loaded = True
        _phase2_error = None
        logger.info("Phase2Manager loaded successfully")
        return True, "🟢 Phi-3 Mini + Whisper + Piper TTS loaded successfully."
    except Exception as exc:
        _phase2_error = str(exc)
        _phase2_loaded = False
        logger.error("Phase2Manager load error: %s", exc)
        return False, f"Failed to initialize: {exc}"


async def chat(query: str, channel: str, state) -> Dict:
    """
    Submit a text query to the LLM and get a text + TTS audio response.
    Returns {"reply": str, "audio_base64": str | None}.
    """
    if not _phase2_loaded or _phase2_manager is None:
        standby_msg = "Clinical intelligence engine not initialized (offline standby). Please click Initialize Support Engine or state your flight command."
        try:
            from backend.services.voice_service import _synthesize_standalone_wav
            audio_bytes = await asyncio.to_thread(_synthesize_standalone_wav, standby_msg)
            audio_b64 = base64.b64encode(audio_bytes).decode() if audio_bytes else None
        except Exception:
            audio_b64 = None
        return {
            "reply": standby_msg,
            "audio_base64": audio_b64,
        }

    try:
        from modules.database_module import log_psych_event

        # Build system context from live telemetry
        stress_pct = getattr(state.fusion, "last_stress", 0.0)
        emotion = getattr(state.fusion, "last_emotion", "neutral")
        crew = getattr(state, "active_crew", "Unknown")
        mission = getattr(state, "mission_name", "Unknown")

        # Generate LLM response off the event loop
        if asyncio.iscoroutinefunction(_phase2_manager.generate_response):
            reply = await _phase2_manager.generate_response(
                user_text=query,
                emotion=emotion,
                stress_pct=stress_pct,
                astronaut_name=crew,
                mission_phase=mission,
            )
        else:
            reply = await asyncio.to_thread(
                _phase2_manager.generate_response,
                user_text=query,
                emotion=emotion,
                stress_pct=stress_pct,
                astronaut_name=crew,
                mission_phase=mission,
            )

        # Synthesize TTS off the event loop
        audio_bytes: Optional[bytes] = None
        try:
            if asyncio.iscoroutinefunction(_phase2_manager.speak):
                audio_bytes = await _phase2_manager.speak(reply)
            else:
                audio_bytes = await asyncio.to_thread(_phase2_manager.speak, reply)
        except Exception as tts_exc:
            logger.warning("TTS synthesis error: %s", tts_exc)

        if not audio_bytes:
            try:
                from backend.services.voice_service import _synthesize_standalone_wav
                audio_bytes = await asyncio.to_thread(_synthesize_standalone_wav, reply)
            except Exception as fb_exc:
                logger.debug("Standalone fallback TTS error: %s", fb_exc)

        audio_b64 = base64.b64encode(audio_bytes).decode() if audio_bytes else None

        # Log to DB
        try:
            log_psych_event(
                crew_member=crew,
                mission_phase=mission,
                input_channel=channel,
                astronaut_query=query,
                detected_emotion=emotion,
                stress_pct=stress_pct,
                ai_response=reply,
                has_audio=audio_bytes is not None,
            )
        except Exception as db_exc:
            logger.debug("Psych log error: %s", db_exc)

        return {"reply": reply, "audio_base64": audio_b64}

    except Exception as exc:
        logger.error("Chat error: %s", exc)
        return {"reply": f"Error: {exc}", "audio_base64": None}


async def grounding(crew: str, stress: float) -> Dict:
    """
    Trigger immediate 4-7-8 guided grounding protocol.
    Returns {"script": str, "audio_base64": str | None}.
    """
    script = (
        f"Initiating 4-7-8 breathing protocol for {crew}. "
        "Please follow along. Inhale through your nose for 4 counts. "
        "Hold your breath for 7 counts. "
        "Exhale completely through your mouth for 8 counts. "
        "Repeat this cycle 4 times. You are doing well."
    )

    audio_bytes: Optional[bytes] = None
    if _phase2_loaded and _phase2_manager is not None:
        try:
            if asyncio.iscoroutinefunction(_phase2_manager.speak):
                audio_bytes = await _phase2_manager.speak(script)
            else:
                audio_bytes = await asyncio.to_thread(_phase2_manager.speak, script)
        except Exception as exc:
            logger.warning("Grounding TTS error: %s", exc)

    if not audio_bytes:
        try:
            from backend.services.voice_service import _synthesize_standalone_wav
            audio_bytes = await asyncio.to_thread(_synthesize_standalone_wav, script)
        except Exception as exc:
            logger.debug("Grounding fallback TTS error: %s", exc)

    return {
        "script": script,
        "audio_base64": base64.b64encode(audio_bytes).decode() if audio_bytes else None,
    }


def get_evolved_presets(stress_pct: float, emotion: str, mission_phase: str = "LEO Operations") -> List[Tuple[str, str]]:
    """
    Returns the 6 contextual preset chips (2 permanent + 4 adaptive) as [label, prompt] pairs,
    matching the Step 0 specification REST contract and app.py logic.
    """
    try:
        from modules.phase2_core import get_evolved_presets as core_presets
        return core_presets(chat_history=None, cur_emotion=emotion, stress_pct=stress_pct, mission_phase=mission_phase)
    except Exception as exc:
        logger.debug("Core presets fallback: %s", exc)
        return [
            ("🧘 4-7-8 Grounding", "Guide me through a 4-7-8 sensory grounding exercise."),
            ("📊 Full Telemetry Check", "Assess my current fatigue and stress telemetry across all sensors."),
            ("🫁 Box Breathing", "Guide me through a four-stage box breathing routine."),
            ("🚀 Docking Stress", "I am feeling high anxiety during this docking phase."),
            ("💤 Sleep Reset", "Provide sleep and circadian rest guidance for spaceflight insomnia."),
            ("🎯 60s Focus Primer", "Guide me through a 60-second operational focus and presence check."),
        ]
