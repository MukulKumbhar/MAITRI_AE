"""
MAITRI 2.0 — Clinical API Router
IEC 60601-1-8 Alarms, Hardware Sensor Adapter Control, Personal Baseline Calibration.
"""

import logging
from typing import Any, Dict, List, Optional

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


class PVTStartRequest(BaseModel):
    crew_member: str = "Astronaut"
    duration_s: float = 180.0


class PVTResponseRequest(BaseModel):
    rt_ms: Optional[float] = None
    is_false_start: bool = False


class SleepLogRequest(BaseModel):
    sleep_date: str
    sleep_duration_hours: float
    target_sleep_hours: float = 8.0
    light_exposure_lux: float = 120.0
    notes: str = ""
    crew_member: str = "Astronaut"


class ScreenerSubmitRequest(BaseModel):
    screener_type: str  # "PHQ-9", "GAD-7", "PSS-4"
    item_responses: List[int]
    crew_member: str = "Astronaut"
    mission_elapsed_days: float = 90.0
    mission_total_days: float = 180.0


class CabinEnvUpdateRequest(BaseModel):
    cabin_co2: Optional[float] = None
    cabin_o2: Optional[float] = None
    cabin_pressure: Optional[float] = None
    cabin_temp: Optional[float] = None
    cabin_noise: Optional[float] = None


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


# ─────────────────────────────────────────────────────────────────────────────
# PVT-B Reaction Self-Test Endpoints (Basner & Dinges 2011)
# ─────────────────────────────────────────────────────────────────────────────

_active_pvt_session: Optional[Any] = None


@router.post("/pvt/start")
async def start_pvt(req: PVTStartRequest):
    """Start a new 3-minute PVT-B test session."""
    global _active_pvt_session
    from modules.pvt_module import PVTSession
    _active_pvt_session = PVTSession(crew_member=req.crew_member, duration_s=req.duration_s)
    status = _active_pvt_session.start()
    return {"status": "started", "session": status}


@router.post("/pvt/response")
async def record_pvt_response(req: PVTResponseRequest):
    """Record an astronaut's response press during active PVT session."""
    global _active_pvt_session
    if not _active_pvt_session:
        return {"status": "error", "message": "No active PVT session"}

    if req.is_false_start:
        _active_pvt_session.status = "AWAITING_STIMULUS"
        res = _active_pvt_session.record_press()
    elif req.rt_ms is not None:
        # Client reported explicit RT
        import time as _time
        from modules.pvt_module import PVTResponse, PVTB_FALSE_START_THRESHOLD_MS, PVTB_LAPSE_THRESHOLD_MS
        trial = _active_pvt_session.current_trial or PVTResponse(
            trial_index=len(_active_pvt_session.responses) + 1,
            isi_delay_s=0.0,
            stimulus_time=_active_pvt_session.active_stimulus_start,
        )
        trial.rt_ms = float(req.rt_ms)
        trial.response_time = _time.time()
        trial.is_false_start = (trial.rt_ms < PVTB_FALSE_START_THRESHOLD_MS)
        trial.is_lapse = (trial.rt_ms >= PVTB_LAPSE_THRESHOLD_MS)
        _active_pvt_session.responses.append(trial)
        _active_pvt_session._schedule_next_stimulus(_time.time())
        res = {
            "outcome": "FALSE_START" if trial.is_false_start else ("LAPSE" if trial.is_lapse else "VALID_HIT"),
            "rt_ms": trial.rt_ms,
            **_active_pvt_session.get_status(),
        }
    else:
        res = _active_pvt_session.record_press()

    # If completed, persist to database with SHA-256 hash chaining
    if _active_pvt_session.status == "COMPLETED":
        try:
            from modules.database_module import log_pvt_result
            m = _active_pvt_session.get_status()["metrics"]
            log_pvt_result(
                session_id=_active_pvt_session.session_id,
                crew_member=_active_pvt_session.crew_member,
                duration_s=_active_pvt_session.duration_s,
                total_stimuli=m["total_stimuli"],
                valid_hits=m["valid_hits"],
                lapses=m["lapses"],
                false_starts=m["false_starts"],
                mean_rt_ms=m["mean_rt_ms"],
                median_rt_ms=m["median_rt_ms"],
                fastest_10pct_rt_ms=m["fastest_10pct_rt_ms"],
                slowest_10pct_rt_ms=m["slowest_10pct_rt_ms"],
                mean_speed=m["mean_speed"],
                fatigue_risk_score=m["fatigue_risk_score"],
                performance_category=m["performance_category"],
                raw_rts=[r.rt_ms for r in _active_pvt_session.responses],
            )
        except Exception as exc:
            logger.warning("Failed to auto-log completed PVT: %s", exc)

    return res


@router.get("/pvt/status")
async def get_pvt_status():
    """Get active PVT session status and metrics."""
    global _active_pvt_session
    if not _active_pvt_session:
        return {"status": "IDLE", "session": None}
    status = _active_pvt_session.check_timer()
    return {"status": _active_pvt_session.status, "session": status}


@router.post("/pvt/abort")
async def abort_pvt():
    """Abort active PVT session."""
    global _active_pvt_session
    if not _active_pvt_session:
        return {"status": "error", "message": "No active PVT session"}
    res = _active_pvt_session.abort()
    return {"status": "aborted", "session": res}


@router.get("/pvt/history")
async def get_pvt_history(limit: int = 20):
    """Return historical PVT-B test records from SQLite database."""
    from modules.database_module import get_pvt_logs
    df = get_pvt_logs(limit=limit)
    return {"records": df.to_dict(orient="records")}


# ─────────────────────────────────────────────────────────────────────────────
# Sleep & Circadian Rhythm Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/sleep")
async def get_sleep_status(actual_hours: float = 7.0, target_hours: float = 8.0, lux: float = 120.0):
    """
    Get current sleep debt, circadian phase angle, melatonin suppression,
    and ISS 90-minute daylight/night orbital cycle tracker.
    """
    import datetime
    from modules.circadian_module import (
        calculate_sleep_debt,
        calculate_circadian_phase,
        estimate_melatonin_suppression,
        get_iss_orbital_cycle,
    )
    now_dt = datetime.datetime.now()
    cur_hour = now_dt.hour + (now_dt.minute / 60.0)

    debt = calculate_sleep_debt(actual_sleep_hours=actual_hours, target_sleep_hours=target_hours)
    phase = calculate_circadian_phase(current_hour_decimal=cur_hour)
    melatonin = estimate_melatonin_suppression(light_lux=lux)
    orbital = get_iss_orbital_cycle()

    return {
        "sleep_debt": debt,
        "circadian_phase": phase,
        "melatonin_suppression": melatonin,
        "orbital_cycle": orbital,
        "decision_support_notice": "DECISION SUPPORT ONLY — NOT AN AUTOMATED MEDICAL DEVICE.",
    }


@router.post("/sleep/log")
async def log_sleep(req: SleepLogRequest):
    """Log daily sleep hours and calculate cumulative debt with cryptographic chaining."""
    from modules.circadian_module import calculate_sleep_debt, estimate_melatonin_suppression
    from modules.database_module import log_sleep_record, get_sleep_records

    # Check prior records for cumulative debt
    prior_df = get_sleep_records(limit=1)
    prior_debt = float(prior_df.iloc[0]["cumulative_debt_hours"]) if not prior_df.empty else 0.0

    debt_info = calculate_sleep_debt(
        actual_sleep_hours=req.sleep_duration_hours,
        target_sleep_hours=req.target_sleep_hours,
        prior_cumulative_debt_hours=prior_debt,
    )
    melatonin_info = estimate_melatonin_suppression(light_lux=req.light_exposure_lux)

    prev_hash, record_hash = log_sleep_record(
        sleep_date=req.sleep_date,
        sleep_duration_hours=req.sleep_duration_hours,
        target_sleep_hours=req.target_sleep_hours,
        sleep_debt_hours=debt_info["daily_delta_hours"],
        cumulative_debt_hours=debt_info["cumulative_debt_hours"],
        chronic_fatigue_risk=debt_info["chronic_fatigue_risk_index"],
        circadian_phase_rad=0.0,
        melatonin_suppression_pct=melatonin_info["melatonin_suppression_pct"],
        light_exposure_lux=req.light_exposure_lux,
        clinical_status=debt_info["clinical_status"],
        notes=req.notes,
        crew_member=req.crew_member,
    )

    return {
        "status": "logged",
        "record_hash": record_hash,
        "prev_hash": prev_hash,
        "debt_analysis": debt_info,
    }


@router.get("/sleep/history")
async def get_sleep_history(limit: int = 30):
    """Return historical sleep records."""
    from modules.database_module import get_sleep_records
    df = get_sleep_records(limit=limit)
    return {"records": df.to_dict(orient="records")}


@router.get("/sleep/orbital-cycle")
async def get_orbital_cycle():
    """Return real-time ISS 90-minute daylight/night orbital cycle tracker."""
    from modules.circadian_module import get_iss_orbital_cycle
    return get_iss_orbital_cycle()


# ─────────────────────────────────────────────────────────────────────────────
# Clinical Screener Endpoints (PHQ-9, GAD-7, PSS-4 & Third-Quarter Effect)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/screener/submit")
async def submit_screener(req: ScreenerSubmitRequest):
    """
    Score validated clinical psychometric screener (PHQ-9, GAD-7, PSS-4),
    enforce Item 9 safety trigger, calculate Third-Quarter Effect, and log with SHA-256 chain.
    """
    from modules.screener_module import (
        score_phq9,
        score_gad7,
        score_pss4,
        calculate_third_quarter_effect,
    )
    from modules.database_module import log_screener_record, get_screener_records

    st = req.screener_type.upper().strip()
    if st == "PHQ-9" or st == "PHQ9":
        result = score_phq9(req.item_responses)
    elif st == "GAD-7" or st == "GAD7":
        result = score_gad7(req.item_responses)
    elif st == "PSS-4" or st == "PSS4":
        result = score_pss4(req.item_responses)
    else:
        return {"status": "error", "message": f"Unsupported screener type: {req.screener_type}"}

    # Calculate Third-Quarter Effect
    past_df = get_screener_records(limit=10)
    past_records = past_df.to_dict(orient="records") if not past_df.empty else []
    tq_analysis = calculate_third_quarter_effect(
        mission_elapsed_days=req.mission_elapsed_days,
        mission_total_days=req.mission_total_days,
        historical_scores=past_records,
    )

    prev_h, rec_h = log_screener_record(
        screener_type=result.screener_type,
        total_score=result.total_score,
        max_possible_score=result.max_possible_score,
        severity=result.severity,
        item_responses=result.item_responses,
        safety_alert=result.safety_alert,
        safety_message=result.safety_message or "",
        third_quarter_risk_index=tq_analysis["vulnerability_index"],
        clinical_interpretation=result.clinical_interpretation,
        action_recommendation=result.action_recommendation,
        crew_member=req.crew_member,
    )

    # If safety gate triggered, raise high-priority clinical alarm
    state = get_state()
    if result.safety_alert and hasattr(state, "alarm_manager"):
        state.alarm_manager.raise_alarm(
            "PSYCH_ITEM9_SAFETY_TRIGGER",
            "HIGH",
            "CRITICAL: PHQ-9 Item 9 Self-Harm Endorsement. Immediate Ground Behavioral Consultation Required.",
            "affect"
        )

    return {
        "status": "scored_and_logged",
        "result": {
            "screener_type": result.screener_type,
            "total_score": result.total_score,
            "max_possible_score": result.max_possible_score,
            "severity": result.severity,
            "clinical_interpretation": result.clinical_interpretation,
            "safety_alert": result.safety_alert,
            "safety_message": result.safety_message,
            "action_recommendation": result.action_recommendation,
        },
        "third_quarter_effect": tq_analysis,
        "record_hash": rec_h,
        "prev_hash": prev_h,
    }


@router.get("/screener/history")
async def get_screener_history(limit: int = 30):
    """Return historical clinical screener records."""
    from modules.database_module import get_screener_records
    df = get_screener_records(limit=limit)
    return {"records": df.to_dict(orient="records")}


@router.get("/screener/third-quarter")
async def get_third_quarter_analysis(mission_elapsed_days: float = 90.0, mission_total_days: float = 180.0):
    """Return Third-Quarter Effect vulnerability analysis."""
    from modules.screener_module import calculate_third_quarter_effect
    from modules.database_module import get_screener_records
    past_df = get_screener_records(limit=10)
    past_records = past_df.to_dict(orient="records") if not past_df.empty else []
    return calculate_third_quarter_effect(
        mission_elapsed_days=mission_elapsed_days,
        mission_total_days=mission_total_days,
        historical_scores=past_records,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Cabin Environmental Telemetry & Dr. Law (2014) Hazard Model Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/environment")
async def get_cabin_environment():
    """Return current ECLSS atmospheric telemetry and Law (2014) headache hazard model."""
    state = get_state()
    co2 = getattr(state, "cabin_co2", 3.0)
    hazard = state.calculate_co2_headache_hazard(co2) if hasattr(state, "calculate_co2_headache_hazard") else {}

    return {
        "cabin_co2_mmhg": co2,
        "cabin_o2_percent": getattr(state, "cabin_o2", 20.9),
        "cabin_pressure_kpa": getattr(state, "cabin_pressure", 101.3),
        "cabin_temp_c": getattr(state, "cabin_temp", 22.0),
        "cabin_noise_dba": getattr(state, "cabin_noise", 58.0),
        "co2_headache_hazard": hazard,
        "decision_support_notice": "DECISION SUPPORT ONLY — NOT AN AUTOMATED MEDICAL DEVICE.",
    }


@router.post("/environment")
async def set_cabin_environment(req: CabinEnvUpdateRequest):
    """Set manual cabin environment parameters."""
    state = get_state()
    if req.cabin_co2 is not None:
        state.cabin_co2 = max(0.0, min(20.0, float(req.cabin_co2)))
    if req.cabin_o2 is not None:
        state.cabin_o2 = max(10.0, min(30.0, float(req.cabin_o2)))
    if req.cabin_pressure is not None:
        state.cabin_pressure = max(50.0, min(150.0, float(req.cabin_pressure)))
    if req.cabin_temp is not None:
        state.cabin_temp = max(10.0, min(40.0, float(req.cabin_temp)))
    if req.cabin_noise is not None:
        state.cabin_noise = max(30.0, min(100.0, float(req.cabin_noise)))

    return {
        "status": "updated",
        "cabin_co2_mmhg": state.cabin_co2,
        "cabin_o2_percent": state.cabin_o2,
        "cabin_pressure_kpa": state.cabin_pressure,
        "cabin_temp_c": state.cabin_temp,
        "cabin_noise_dba": state.cabin_noise,
    }


@router.get("/environment/hazard-model")
async def get_co2_hazard_model(co2_mmhg: float = 3.0):
    """Compute Dr. Law (2014) CO2-headache hazard odds ratio and probability."""
    from backend.state import calculate_law2014_headache_odds
    return calculate_law2014_headache_odds(co2_mmhg)


# ─────────────────────────────────────────────────────────────────────────────
# Curated Medical Reference Library Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/references")
async def get_medical_references(query: Optional[str] = None):
    """List or search curated aerospace clinical reference library."""
    from modules.medical_kb import MEDICAL_ARTICLES, search_medical_knowledge
    if query:
        results = search_medical_knowledge(query, max_results=10)
    else:
        results = MEDICAL_ARTICLES
    return {"references": results, "total": len(results)}


@router.get("/references/{ref_id}")
async def get_medical_reference_by_id(ref_id: str):
    """Get specific clinical reference article by ID."""
    from modules.medical_kb import MEDICAL_ARTICLES
    for art in MEDICAL_ARTICLES:
        if art["id"].lower() == ref_id.lower():
            return art
    return {"status": "not_found", "message": f"Reference {ref_id} not found"}


# ─────────────────────────────────────────────────────────────────────────────
# Step-by-Step Emergency Checklists Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/checklists")
async def get_emergency_checklists():
    """List all available step-by-step aerospace emergency checklists."""
    from modules.medical_kb import get_all_emergency_checklists
    return {"checklists": get_all_emergency_checklists()}


@router.get("/checklists/{checklist_id}")
async def get_emergency_checklist_by_id(checklist_id: str):
    """Get specific emergency checklist steps (e.g. 'checklist_ammonia', 'checklist_trauma')."""
    from modules.medical_kb import get_emergency_checklist
    cl = get_emergency_checklist(checklist_id)
    if cl:
        return cl
    return {"status": "not_found", "message": f"Checklist {checklist_id} not found"}


# ─────────────────────────────────────────────────────────────────────────────
# Built-In Self-Test (BIST) Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/bist/run")
async def run_bist_endpoint():
    """Execute full Built-In Self-Test (BIST) diagnostic suite across all hardware & software."""
    from backend.services.bist_service import run_bist
    state = get_state()
    res = run_bist(db_path=state.get_db_path())
    return res


@router.get("/bist/status")
async def get_bist_status():
    """Get the latest cached BIST report or run diagnostic if none exists."""
    from backend.services.bist_service import get_last_bist_result, run_bist
    res = get_last_bist_result()
    if res is None:
        state = get_state()
        res = run_bist(db_path=state.get_db_path())
    return res
