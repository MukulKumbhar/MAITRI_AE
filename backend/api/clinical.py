"""
MAITRI 2.0 — Clinical API Router
IEC 60601-1-8 Alarms, Hardware Sensor Adapter Control, Personal Baseline Calibration.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from backend.state import get_state

logger = logging.getLogger("maitri.api.clinical")
router = APIRouter(prefix="/api/clinical", tags=["clinical"])


# ── Request Models ────────────────────────────────────────────────────────────

class AlarmAckRequest(BaseModel):
    code_or_id: str
    ack_by: str = "crew"


class AlarmPauseRequest(BaseModel):
    duration_sec: float = 120.0


class AlarmResolveRequest(BaseModel):
    code_or_id: str


class SensorModeRequest(BaseModel):
    mode: str  # "live", "manual", "replay"


class SensorScenarioRequest(BaseModel):
    scenario: str  # "nominal_flight", "co2_retention", "eva_strain", "solar_flare"
    replay_speed: Optional[float] = None


class BaselineCalibrateRequest(BaseModel):
    face_probs: Optional[Dict[str, float]] = None
    vitals_strain: float = 0.10
    ear: float = 0.28
    fatigue_strain: float = 0.0


# ── Alarm Endpoints (IEC 60601-1-8) ──────────────────────────────────────────

@router.get("/alarms")
async def get_alarms():
    """Return active IEC 60601-1-8 alarms and summary."""
    state = get_state()
    if not hasattr(state, "alarm_manager"):
        return {"summary": {}, "active": []}

    summary = state.alarm_manager.get_summary()
    active_list = [
        {
            "alarm_id": a.alarm_id,
            "code": a.code,
            "priority": a.priority,
            "message": a.message,
            "source": a.source,
            "created_at": a.created_at,
            "acknowledged": a.acknowledged,
            "ack_by": a.ack_by,
            "escalated": a.escalated,
            "occurrence_count": a.occurrence_count,
        }
        for a in state.alarm_manager.active_alarms.values()
    ]
    return {
        "summary": summary,
        "active": active_list,
        "is_audio_paused": state.alarm_manager.is_audio_paused(),
        "remaining_pause_sec": round(state.alarm_manager.remaining_audio_pause_sec(), 1),
    }


@router.post("/alarms/ack")
async def acknowledge_alarm(req: AlarmAckRequest):
    """Acknowledge an active IEC 60601-1-8 alarm."""
    state = get_state()
    if not hasattr(state, "alarm_manager"):
        return {"status": "error", "message": "Alarm manager not initialized"}

    alarm = state.alarm_manager.acknowledge_alarm(req.code_or_id, ack_by=req.ack_by)
    if alarm:
        return {
            "status": "acknowledged",
            "alarm_id": alarm.alarm_id,
            "code": alarm.code,
            "ack_by": alarm.ack_by,
        }
    return {"status": "not_found", "message": f"Alarm {req.code_or_id} not found"}


@router.post("/alarms/pause")
async def pause_alarm_audio(req: AlarmPauseRequest):
    """Pause alarm audio for 120s (IEC 60601-1-8 clause 6.8.4)."""
    state = get_state()
    if not hasattr(state, "alarm_manager"):
        return {"status": "error"}

    until = state.alarm_manager.pause_audio(duration_sec=req.duration_sec)
    return {
        "status": "paused",
        "duration_sec": req.duration_sec,
        "paused_until": until,
        "remaining_sec": round(state.alarm_manager.remaining_audio_pause_sec(), 1),
    }


@router.post("/alarms/resolve")
async def resolve_alarm(req: AlarmResolveRequest):
    """Resolve and clear an active alarm."""
    state = get_state()
    if not hasattr(state, "alarm_manager"):
        return {"status": "error"}

    alarm = state.alarm_manager.resolve_alarm(req.code_or_id)
    if alarm:
        return {"status": "resolved", "alarm_id": alarm.alarm_id, "code": alarm.code}
    return {"status": "not_found", "message": f"Alarm {req.code_or_id} not found"}


# ── Hardware Sensor Adapter Control ──────────────────────────────────────────

@router.get("/sensors")
async def get_sensors():
    """Return hardware sensor adapter mode, scenario, and channel status."""
    state = get_state()
    if not hasattr(state, "sensor_adapter"):
        return {"mode": "manual", "channels": {}}
    return state.sensor_adapter.get_status()


@router.post("/sensors/mode")
async def set_sensor_mode(req: SensorModeRequest):
    """Set hardware sensor adapter mode: 'live', 'manual', or 'replay'."""
    state = get_state()
    if not hasattr(state, "sensor_adapter"):
        return {"status": "error"}
    state.sensor_adapter.set_mode(req.mode)
    return {"status": "updated", "mode": state.sensor_adapter.mode}


@router.post("/sensors/scenario")
async def set_sensor_scenario(req: SensorScenarioRequest):
    """Set deterministic physiological simulation scenario."""
    state = get_state()
    if not hasattr(state, "sensor_adapter"):
        return {"status": "error"}
    state.sensor_adapter.set_scenario(req.scenario)
    if req.replay_speed is not None:
        state.sensor_adapter.replay_speed = max(0.1, min(10.0, req.replay_speed))
    return {
        "status": "updated",
        "scenario": state.sensor_adapter.scenario,
        "replay_speed": state.sensor_adapter.replay_speed,
    }


# ── Personal Baseline Calibration ────────────────────────────────────────────

@router.get("/baseline/status")
async def get_baseline_status():
    """Return crew personal baseline calibration status and Z-scores."""
    state = get_state()
    baseline = getattr(state.fusion, "baseline", None)
    if not baseline:
        return {"is_calibrated": False, "sample_count": 0}

    return {
        "crew_id": baseline.crew_id,
        "is_calibrated": baseline.is_calibrated,
        "sample_count": baseline.sample_count,
        "calibration_target": baseline.calibration_target,
        "means": {
            "negative_affect": round(baseline.mu_negative_affect, 3),
            "vitals_strain": round(baseline.mu_vitals_strain, 3),
            "ear": round(baseline.mu_ear, 3),
            "face_strain": round(baseline.mu_face_strain, 3),
        },
        "sigmas": {
            "negative_affect": round(baseline.sigma_negative_affect, 3),
            "vitals_strain": round(baseline.sigma_vitals_strain, 3),
            "ear": round(baseline.sigma_ear, 3),
            "face_strain": round(baseline.sigma_face_strain, 3),
        },
        "cusum_drift": dict(baseline.cusum_drift),
        "cusum_sh": dict(baseline.cusum_sh),
    }


@router.post("/baseline/calibrate")
async def calibrate_baseline(req: BaselineCalibrateRequest):
    """Feed a calibration sample into crew personal baseline."""
    state = get_state()
    baseline = getattr(state.fusion, "baseline", None)
    if not baseline:
        from modules.fusion_module import PersonalBaseline
        state.fusion.baseline = PersonalBaseline()
        baseline = state.fusion.baseline

    baseline.calibrate_step(
        face_probs=req.face_probs,
        vitals_strain=req.vitals_strain,
        ear=req.ear,
        fatigue_strain=req.fatigue_strain,
    )
    return {
        "status": "calibrated" if baseline.is_calibrated else "accumulating",
        "sample_count": baseline.sample_count,
        "is_calibrated": baseline.is_calibrated,
    }
