"""
MAITRI 2.0 — Audio WebSocket Handler
/ws/audio

Bidirectional channel:
  Client → Server: 16-bit 16kHz mono PCM binary chunks from AudioWorklet
  Server → Client: JSON events (vad_speech_start, vad_speech_end,
                   audio_level, asr_transcript, tts_audio_response)

Phase 1: Energy-based VAD + RMS metering (Vosk added in Phase 3).
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.state import get_state
from backend.services.voice_service import get_voice_service

logger = logging.getLogger("maitri.ws.audio")
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/audio")
async def audio_ws(websocket: WebSocket):
    """
    WebSocket endpoint for audio PCM streaming and ASR events.
    Accepts binary PCM frames from the browser AudioWorklet.
    """
    await websocket.accept()
    state = get_state()
    voice_svc = get_voice_service()
    logger.info("Audio WS connected")

    # Register event callback: voice_service emits events back through this WS
    async def emit_event(event: dict):
        try:
            await websocket.send_text(json.dumps(event))
        except Exception:
            pass  # WS closed

    voice_svc.add_event_callback(emit_event)

    # Send ready acknowledgement
    await websocket.send_text(json.dumps({
        "type": "audio_ws_ready",
        "phase1_vad": True,
        "vosk_ready": state.vosk_ready,
    }))

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message and message["bytes"] is not None:
                # Binary PCM chunk from AudioWorklet
                pcm_bytes = message["bytes"]
                await voice_svc.push_audio_chunk(pcm_bytes, state)

            elif "text" in message and message["text"]:
                # JSON control messages from client
                try:
                    ctrl = json.loads(message["text"])
                    await _handle_audio_control(ctrl, state, websocket)
                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        logger.info("Audio WS disconnected")
    except Exception as exc:
        logger.warning("Audio WS error: %s", exc)
    finally:
        voice_svc.remove_event_callback(emit_event)
        try:
            await voice_svc.flush(state)
        except Exception:
            pass
        voice_svc.reset_session()
        # Reset speaking state on disconnect
        with state.live.voice_lock:
            state.live.is_speaking = False
            state.live.voice_rms = 0.0


async def _handle_audio_control(ctrl: dict, state, ws: WebSocket) -> None:
    """Handle JSON control messages from the audio WebSocket client."""
    msg_type = ctrl.get("type", "")

    if msg_type == "set_gain":
        state.mic_gain = max(0.5, min(3.0, float(ctrl.get("gain", 1.0))))

    elif msg_type == "set_threshold":
        state.silence_threshold = max(0.005, min(0.080, float(ctrl.get("threshold", 0.03))))

    elif msg_type == "ping":
        await ws.send_text(json.dumps({"type": "pong"}))

    elif msg_type == "request_status":
        await ws.send_text(json.dumps({
            "type": "audio_status",
            "vosk_ready": state.vosk_ready,
            "mic_gain": state.mic_gain,
            "silence_threshold": state.silence_threshold,
            "is_speaking": state.live.is_speaking,
        }))
