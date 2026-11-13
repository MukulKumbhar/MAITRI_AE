"""
MAITRI 2.0 — Telemetry WebSocket Handler
/ws/telemetry

Bidirectional channel:
  Server → Client: 10 Hz JSON telemetry payload (registered to broadcast loop)
  Client → Server: vitals updates, settings toggles
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.state import get_state

logger = logging.getLogger("maitri.ws.telemetry")
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/telemetry")
async def telemetry_ws(websocket: WebSocket):
    """
    WebSocket endpoint for bidirectional telemetry streaming.
    Registers the connection in the broadcast pool; the telemetry_service
    loop pushes JSON at 10 Hz.  Incoming messages update vitals/settings.
    """
    await websocket.accept()
    state = get_state()

    async with state.telemetry_connections_lock:
        state.telemetry_connections.add(websocket)
    logger.info("Telemetry WS connected. Total: %d", len(state.telemetry_connections))

    try:
        while True:
            # Wait for client messages (vitals updates, toggles, etc.)
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                await _handle_client_message(msg, state)
            except json.JSONDecodeError:
                logger.debug("Invalid JSON from telemetry WS client")
            except Exception as exc:
                logger.warning("Telemetry WS message error: %s", exc)

    except WebSocketDisconnect:
        logger.info("Telemetry WS disconnected")
    except Exception as exc:
        logger.warning("Telemetry WS error: %s", exc)
    finally:
        async with state.telemetry_connections_lock:
            state.telemetry_connections.discard(websocket)
        logger.info("Telemetry WS removed. Total: %d", len(state.telemetry_connections))


async def _handle_client_message(msg: dict, state) -> None:
    """Route incoming client messages to the appropriate state update."""
    action = msg.get("action", "")

    if action == "update_vitals":
        # Client sends slider changes
        if "heart_rate" in msg:
            state.heart_rate = float(msg["heart_rate"])
        if "temperature" in msg:
            state.temperature = float(msg["temperature"])
        if "spo2" in msg:
            state.spo2 = float(msg["spo2"])

    elif action == "update_settings":
        if "manual_override" in msg:
            state.manual_override = bool(msg["manual_override"])
        if "manual_face_ratio" in msg:
            state.manual_face_ratio = float(msg["manual_face_ratio"])
        if "auto_log_enabled" in msg:
            state.auto_log_enabled = bool(msg["auto_log_enabled"])
        if "mic_gain" in msg:
            state.mic_gain = float(msg["mic_gain"])
        if "silence_threshold" in msg:
            state.silence_threshold = float(msg["silence_threshold"])

    elif action == "log_snapshot":
        # Manual log button from frontend
        try:
            from modules.database_module import log_event
            from modules.vitals_module import compute_vitals_strain
            from modules.alert_module import get_alert
            vitals = compute_vitals_strain(state.heart_rate, state.temperature, state.spo2)
            face_snap = state.live.snapshot_face()
            alert = get_alert(
                stress_pct=state.fusion.last_stress,
                dominant_emotion=state.fusion.last_emotion,
                fatigue_label=face_snap["fatigue_label"],
            )
            log_event(
                face_emotion=face_snap["face_emotion"],
                fused_emotion=state.fusion.last_emotion,
                voice_state="speaking" if state.live.is_speaking else "silent",
                heart_rate=state.heart_rate,
                temperature=state.temperature,
                spo2=state.spo2,
                blink_rate=face_snap["blink_rate"],
                fatigue_label=face_snap["fatigue_label"],
                stress_score=state.fusion.last_stress,
                stress_level=alert.stress_level,
                alert_triggered=alert.header,
                response_msg=alert.body,
                emotion_probs=dict(state.fusion.ema_probs),
            )
        except Exception as exc:
            logger.warning("Manual log error: %s", exc)

    elif action == "watchdog_ack":
        state.watchdog.acknowledge()

    elif action == "watchdog_simulate":
        state.watchdog.trigger_simulation()

    elif action == "ping":
        pass  # heartbeat from client, no-op

    else:
        logger.debug("Unknown telemetry WS action: %s", action)
