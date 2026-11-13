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
            vitals = compute_vitals_strain(
                heart_rate=state.heart_rate,
                temperature=state.temperature,
                spo2=state.spo2,
                respiratory_rate=getattr(state, "manual_respiratory_rate", None),
                rmssd=getattr(state, "manual_rmssd", None),
                sdnn=getattr(state, "manual_sdnn", None),
                baevsky_index=getattr(state, "manual_baevsky_index", None),
            )
            face_snap = state.live.snapshot_face()
            alert = get_alert(
                stress_pct=state.fusion.last_stress,
                dominant_emotion=state.fusion.last_emotion,
                fatigue_label=face_snap["fatigue_label"],
            )
            prev_h, rec_h = log_event(
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
                rmssd=vitals.rmssd,
                sdnn=vitals.sdnn,
                baevsky_index=vitals.baevsky_index,
                respiratory_rate=vitals.respiratory_rate,
                co2_mmhg=getattr(state, "cabin_co2", 3.0),
                o2_percent=getattr(state, "cabin_o2", 20.9),
                pressure_kpa=getattr(state, "cabin_pressure", 101.3),
                ambient_temp_c=getattr(state, "cabin_temp", 22.0),
                noise_dba=getattr(state, "cabin_noise", 58.0),
            )
            if hasattr(state, "hash_chain"):
                state.hash_chain.current_hash = rec_h
                state.hash_chain.entry_count += 1
        except Exception as exc:
            logger.warning("Manual log error: %s", exc)

    elif action in ("alarm_ack", "acknowledge_alarm"):
        code_or_id = msg.get("code") or msg.get("alarm_id", "")
        ack_by = msg.get("ack_by", "crew")
        if hasattr(state, "alarm_manager") and code_or_id:
            state.alarm_manager.acknowledge_alarm(code_or_id, ack_by=ack_by)

    elif action in ("alarm_mute", "alarm_pause", "pause_audio"):
        duration = float(msg.get("duration", 120.0))
        if hasattr(state, "alarm_manager"):
            state.alarm_manager.pause_audio(duration_sec=duration)

    elif action in ("alarm_resolve", "resolve_alarm"):
        code_or_id = msg.get("code") or msg.get("alarm_id", "")
        if hasattr(state, "alarm_manager") and code_or_id:
            state.alarm_manager.resolve_alarm(code_or_id)

    elif action == "set_sensor_mode":
        mode = msg.get("mode", "manual")
        if hasattr(state, "sensor_adapter"):
            state.sensor_adapter.set_mode(mode)

    elif action == "set_simulation_scenario":
        scenario = msg.get("scenario", "nominal_flight")
        if hasattr(state, "sensor_adapter"):
            state.sensor_adapter.set_scenario(scenario)

    elif action == "calibrate_baseline":
        face_snap = state.live.snapshot_face()
        if hasattr(state, "fusion") and hasattr(state.fusion, "baseline"):
            state.fusion.baseline.calibrate_step(
                face_probs=face_snap.get("emotion_probs"),
                vitals_strain=0.10,
                ear=face_snap.get("ear", 0.28),
                fatigue_strain=face_snap.get("fatigue_strain", 0.0),
            )

    elif action == "watchdog_ack":
        state.watchdog.acknowledge()

    elif action == "watchdog_simulate":
        state.watchdog.trigger_simulation()

    elif action == "ping":
        pass  # heartbeat from client, no-op

    else:
        logger.debug("Unknown telemetry WS action: %s", action)
