"""
Tests for Phase 2 Step 2: Clinical Services, Models, and APIs.
Verifies:
1. PVT-B Reaction Self-Test calculations (Basner & Dinges 2011, lapses >355ms, false starts <100ms, mean 1/RT)
2. Sleep debt, Cosinor circadian phase angle phi, Rea melatonin suppression, and ISS 90-min orbital cycle
3. Validated clinical screeners (PHQ-9 with Item 9 safety trigger, GAD-7, PSS-4 reverse scoring, Third-Quarter Effect)
4. Dr. Law (2014) CO2-headache hazard model odds ratio calculations
5. Curated local medical KB, emergency checklists, and Phi-3 out-of-scope refusal
6. Built-In Self-Test (BIST) diagnostics runner
7. Database tables (pvt_logs, sleep_records, screener_records) with SHA-256 hash chaining
8. Clinical REST endpoints and voice intent parsing
"""

import os
import tempfile
import time
import pytest
from starlette.testclient import TestClient

from backend.main import app
from backend.state import get_state, reset_state, calculate_law2014_headache_odds
from modules.pvt_module import (
    PVTSession,
    PVTResponse,
    calculate_pvt_metrics,
    PVTB_LAPSE_THRESHOLD_MS,
    PVTB_FALSE_START_THRESHOLD_MS,
)
from modules.circadian_module import (
    calculate_sleep_debt,
    calculate_circadian_phase,
    cosinor_model_predict,
    estimate_melatonin_suppression,
    get_iss_orbital_cycle,
)
from modules.screener_module import (
    score_phq9,
    score_gad7,
    score_pss4,
    calculate_third_quarter_effect,
)
from modules.medical_kb import (
    search_medical_knowledge,
    get_emergency_checklist,
    get_all_emergency_checklists,
    is_query_in_scope,
    get_curated_grounding_context,
    EXPLICIT_REFUSAL_MESSAGE,
    is_medical_inquiry,
)
from modules.database_module import (
    init_db,
    log_pvt_result,
    verify_pvt_logs_hash_chain,
    get_pvt_logs,
    log_sleep_record,
    verify_sleep_records_hash_chain,
    get_sleep_records,
    log_screener_record,
    verify_screener_records_hash_chain,
    get_screener_records,
)
from backend.services.bist_service import (
    check_cameras,
    check_microphones,
    check_models_on_disk,
    check_ram_and_resources,
    check_database_integrity,
    run_bist,
)
from backend.services.intent_parser import parse_intent


# ─────────────────────────────────────────────────────────────────────────────
# 1. PVT-B Reaction Self-Test Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_pvtb_metrics_nominal_profile():
    """Verify PVT-B calculations with optimal reaction times."""
    responses = [
        PVTResponse(trial_index=1, isi_delay_s=3.0, stimulus_time=1.0, response_time=1.22, rt_ms=220.0),
        PVTResponse(trial_index=2, isi_delay_s=4.0, stimulus_time=5.0, response_time=5.24, rt_ms=240.0),
        PVTResponse(trial_index=3, isi_delay_s=2.5, stimulus_time=9.0, response_time=9.21, rt_ms=210.0),
        PVTResponse(trial_index=4, isi_delay_s=6.0, stimulus_time=15.0, response_time=15.25, rt_ms=250.0),
    ]
    metrics = calculate_pvt_metrics(responses, duration_s=180.0)

    assert metrics.total_stimuli == 4
    assert metrics.valid_hits == 4
    assert metrics.lapses == 0
    assert metrics.false_starts == 0
    assert 220.0 <= metrics.mean_rt_ms <= 240.0
    # Mean 1/RT speed: 1000/230 ~ 4.3 s^-1
    assert metrics.mean_speed >= 4.0
    assert metrics.fatigue_risk_score < 25.0
    assert metrics.performance_category == "OPTIMAL"


def test_pvtb_metrics_lapses_and_false_starts():
    """Verify Basner & Dinges (2011) lapse (>355ms) and false start (<100ms) detection."""
    responses = [
        PVTResponse(trial_index=1, isi_delay_s=3.0, stimulus_time=1.0, rt_ms=50.0, is_false_start=True),   # False start
        PVTResponse(trial_index=2, isi_delay_s=4.0, stimulus_time=5.0, rt_ms=380.0, is_lapse=True),         # Lapse (>355ms)
        PVTResponse(trial_index=3, isi_delay_s=5.0, stimulus_time=10.0, rt_ms=450.0, is_lapse=True),        # Lapse (>355ms)
        PVTResponse(trial_index=4, isi_delay_s=2.0, stimulus_time=16.0, rt_ms=260.0),                       # Valid hit
    ]
    metrics = calculate_pvt_metrics(responses, duration_s=180.0)

    assert metrics.total_stimuli == 4
    assert metrics.valid_hits == 1
    assert metrics.lapses == 2
    assert metrics.false_starts == 1
    # 2 lapses (20 pts) + 1 false start (5 pts) + speed penalty
    assert metrics.fatigue_risk_score >= 25.0
    assert metrics.performance_category in ("MILD_FATIGUE", "MODERATE_FATIGUE", "SEVERE_IMPAIRMENT")


def test_pvtb_session_lifecycle():
    """Verify PVTSession state machine transitions and response recording."""
    session = PVTSession(crew_member="Cdr. Sharma", duration_s=180.0)
    assert session.status == "READY"

    # Start session
    st = session.start()
    assert session.status == "AWAITING_STIMULUS"
    assert session.next_stimulus_due > session.start_time

    # False start before stimulus activates
    fs_res = session.record_press()
    assert fs_res["outcome"] == "FALSE_START"
    assert session.responses[-1].is_false_start is True

    # Force stimulus active
    session.status = "STIMULUS_ACTIVE"
    session.active_stimulus_start = time.time() - 0.250  # 250ms ago
    hit_res = session.record_press()
    assert hit_res["outcome"] == "VALID_HIT"
    assert 200.0 <= hit_res["rt_ms"] <= 300.0

    # Force lapse response (>355ms)
    session.status = "STIMULUS_ACTIVE"
    session.active_stimulus_start = time.time() - 0.400  # 400ms ago
    lapse_res = session.record_press()
    assert lapse_res["outcome"] == "LAPSE"
    assert lapse_res["rt_ms"] >= PVTB_LAPSE_THRESHOLD_MS

    # Abort
    abort_res = session.abort()
    assert abort_res["status"] == "ABORTED"


def test_pvtb_database_hash_chain():
    """Verify cryptographic SHA-256 hash chaining on pvt_logs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = os.path.join(tmpdir, "pvt_test.db")
        init_db(db)

        # Log 3 consecutive PVT sessions
        p1, r1 = log_pvt_result("S1", "Astronaut", 180.0, 10, 8, 1, 1, 260.0, 250.0, 200.0, 380.0, 3.8, 25.0, "MILD_FATIGUE", [250.0, 260.0], db_path=db)
        p2, r2 = log_pvt_result("S2", "Astronaut", 180.0, 12, 11, 0, 1, 230.0, 225.0, 195.0, 310.0, 4.3, 10.0, "OPTIMAL", [220.0, 230.0], db_path=db)
        p3, r3 = log_pvt_result("S3", "Astronaut", 180.0, 11, 9, 2, 0, 310.0, 290.0, 210.0, 420.0, 3.2, 35.0, "MODERATE_FATIGUE", [290.0, 310.0], db_path=db)

        assert p2 == r1
        assert p3 == r2

        valid, fail_id = verify_pvt_logs_hash_chain(db)
        assert valid is True
        assert fail_id is None

        # Verify DataFrame retrieval
        df = get_pvt_logs(limit=10, db_path=db)
        assert len(df) == 3

        # Tamper with middle record
        import sqlite3
        conn = sqlite3.connect(db)
        c = conn.cursor()
        c.execute("UPDATE pvt_logs SET mean_rt_ms = 999.0 WHERE session_id = 'S2'")
        conn.commit()
        conn.close()

        valid_tampered, fail_id = verify_pvt_logs_hash_chain(db)
        assert valid_tampered is False
        assert fail_id == 2


# ─────────────────────────────────────────────────────────────────────────────
# 2. Sleep & Circadian Rhythm Module Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_sleep_debt_van_dongen_model():
    """Verify sleep restriction debt accumulation and recovery efficiency."""
    # Day 1: 5h sleep on 8h target -> 3h acute debt
    d1 = calculate_sleep_debt(actual_sleep_hours=5.0, target_sleep_hours=8.0, prior_cumulative_debt_hours=0.0)
    assert d1["daily_delta_hours"] == 3.0
    assert d1["cumulative_debt_hours"] == 3.0
    assert d1["clinical_status"] == "MILD_DEFICIT"

    # Day 2: 4h sleep -> 4h deficit added to 3h -> 7h cumulative debt
    d2 = calculate_sleep_debt(actual_sleep_hours=4.0, target_sleep_hours=8.0, prior_cumulative_debt_hours=d1["cumulative_debt_hours"])
    assert d2["cumulative_debt_hours"] == 7.0
    assert d2["clinical_status"] == "MODERATE_DEBT"

    # Day 3: Recovery sleep 10h (2h excess pays down debt with 85% efficiency -> pays down 1.7h)
    d3 = calculate_sleep_debt(actual_sleep_hours=10.0, target_sleep_hours=8.0, prior_cumulative_debt_hours=d2["cumulative_debt_hours"])
    assert d3["cumulative_debt_hours"] < d2["cumulative_debt_hours"]
    assert round(d3["cumulative_debt_hours"], 2) == 5.3


def test_cosinor_circadian_phase_and_alertness():
    """Verify single-harmonic Cosinor and phase angle calculations."""
    # Peak alertness around acrophase (14:00)
    peak = calculate_circadian_phase(current_hour_decimal=14.0, acrophase_hour=14.0)
    assert peak["circadian_alertness"] >= 0.85
    assert peak["phase_state"] == "PEAK_ALERTNESS"

    # Nadir zone around 02:00 (12h opposite to 14:00)
    nadir = calculate_circadian_phase(current_hour_decimal=2.0, acrophase_hour=14.0)
    assert nadir["circadian_alertness"] <= 0.15
    assert nadir["phase_state"] == "NADIR_ZONE"

    # Cosinor model continuity
    val_12 = cosinor_model_predict(12.0, mesor=36.8, amplitude=0.45, acrophase_rad=2.88)
    assert 36.0 <= val_12 <= 37.5


def test_melatonin_suppression_rea_model():
    """Verify Rea et al. phototransduction nocturnal melatonin suppression."""
    # Pitch black (<1 lux): zero suppression
    dark = estimate_melatonin_suppression(light_lux=0.5)
    assert dark["melatonin_suppression_pct"] == 0.0
    assert dark["risk_level"] == "LOW"

    # Dim pre-sleep cabin light (30 lux): mild suppression
    dim = estimate_melatonin_suppression(light_lux=30.0)
    assert dim["melatonin_suppression_pct"] < 30.0

    # Bright daylight exposure (500 lux): high suppression
    bright = estimate_melatonin_suppression(light_lux=500.0)
    assert bright["melatonin_suppression_pct"] >= 60.0
    assert bright["risk_level"] == "HIGH"

    # Blue-enriched boost increases suppression
    boosted = estimate_melatonin_suppression(light_lux=100.0, blue_spectrum_boost=1.4)
    standard = estimate_melatonin_suppression(light_lux=100.0, blue_spectrum_boost=1.0)
    assert boosted["melatonin_suppression_pct"] > standard["melatonin_suppression_pct"]


def test_iss_orbital_cycle():
    """Verify ISS 92.68-min orbital period and daylight/night phase calculations."""
    cycle = get_iss_orbital_cycle()
    assert cycle["orbit_period_minutes"] == 92.68
    assert cycle["current_phase"] in ("DAYLIGHT", "ORBITAL_NIGHT")
    assert 0.0 <= cycle["orbital_fraction"] <= 1.0
    assert cycle["seconds_to_next_transition"] > 0
    assert cycle["next_event"] in ("SUNSET", "SUNRISE")
    assert cycle["sunrises_per_24h"] >= 15.0


def test_sleep_database_hash_chain():
    """Verify cryptographic SHA-256 hash chaining on sleep_records."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = os.path.join(tmpdir, "sleep_test.db")
        init_db(db)

        p1, r1 = log_sleep_record("2026-11-01", 7.5, 8.0, 0.5, 0.5, 10.0, 0.0, 15.0, 100.0, "NOMINAL", "Restful", "Astronaut", db_path=db)
        p2, r2 = log_sleep_record("2026-11-02", 6.0, 8.0, 2.0, 2.5, 25.0, 0.0, 25.0, 120.0, "MILD_DEFICIT", "Noisy pump", "Astronaut", db_path=db)

        assert p2 == r1
        valid, fail_id = verify_sleep_records_hash_chain(db)
        assert valid is True
        assert fail_id is None

        # Check retrieval
        df = get_sleep_records(db_path=db)
        assert len(df) == 2

        # Tamper
        import sqlite3
        conn = sqlite3.connect(db)
        conn.execute("UPDATE sleep_records SET sleep_duration_hours = 12.0 WHERE id = 1")
        conn.commit()
        conn.close()

        valid_tampered, fail_id = verify_sleep_records_hash_chain(db)
        assert valid_tampered is False
        assert fail_id == 1


# ─────────────────────────────────────────────────────────────────────────────
# 3. Clinical Screener Module Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_phq9_scoring_and_severity():
    """Verify PHQ-9 depression psychometric scoring."""
    # Zero score
    res_zero = score_phq9([0] * 9)
    assert res_zero.total_score == 0
    assert res_zero.severity == "MINIMAL"
    assert res_zero.safety_alert is False

    # Moderate depression (12)
    res_mod = score_phq9([1, 2, 2, 1, 1, 1, 2, 2, 0])
    assert res_mod.total_score == 12
    assert res_mod.severity == "MODERATE"
    assert res_mod.safety_alert is False


def test_phq9_item9_safety_gate_trigger():
    """Verify critical safety gate on Item 9 suicide/self-harm trigger."""
    # Mild overall score (5), but Item 9 is positive (1)
    res = score_phq9([1, 1, 1, 1, 0, 0, 0, 0, 1])
    assert res.total_score == 5
    assert res.safety_alert is True
    assert "SAFETY GATE TRIGGERED" in res.safety_message
    assert "Item 9" in res.safety_message
    assert "IMMEDIATE EMERGENCY SAFETY PROTOCOL" in res.action_recommendation


def test_gad7_scoring_and_severity():
    """Verify GAD-7 anxiety psychometric scoring."""
    res_mild = score_gad7([1, 1, 1, 1, 1, 1, 1])
    assert res_mild.total_score == 7
    assert res_mild.severity == "MILD"

    res_sev = score_gad7([3, 3, 3, 2, 2, 3, 2])
    assert res_sev.total_score == 18
    assert res_sev.severity == "SEVERE"


def test_pss4_reverse_scoring():
    """Verify PSS-4 perceived stress scoring with reverse scoring on Items 2 & 3."""
    # If raw responses are [0, 4, 4, 0]:
    # Item 1: 0
    # Item 2 (rev): 4 - 4 = 0
    # Item 3 (rev): 4 - 4 = 0
    # Item 4: 0
    # Total = 0
    res_min = score_pss4([0, 4, 4, 0])
    assert res_min.total_score == 0
    assert res_min.severity == "LOW_STRESS"

    # If raw responses are [0, 0, 0, 0]:
    # Item 1: 0
    # Item 2 (rev): 4 - 0 = 4
    # Item 3 (rev): 4 - 0 = 4
    # Item 4: 0
    # Total = 8
    res_rev = score_pss4([0, 0, 0, 0])
    assert res_rev.total_score == 8
    assert res_rev.severity == "MODERATE_STRESS"

    # Maximum stress [4, 0, 0, 4] -> 4 + 4 + 4 + 4 = 16
    res_max = score_pss4([4, 0, 0, 4])
    assert res_max.total_score == 16
    assert res_max.severity == "HIGH_STRESS"


def test_third_quarter_effect_bechtel():
    """Verify Third-Quarter Effect longitudinal tracking (Bechtel & Berning 1991)."""
    # 20% into mission -> Q1
    q1 = calculate_third_quarter_effect(mission_elapsed_days=36.0, mission_total_days=180.0)
    assert q1["quarter"] == 1
    assert q1["is_third_quarter"] is False
    assert q1["risk_level"] == "LOW"

    # 60% into mission -> Q3 (Third-Quarter Zone)
    q3 = calculate_third_quarter_effect(mission_elapsed_days=108.0, mission_total_days=180.0)
    assert q3["quarter"] == 3
    assert q3["is_third_quarter"] is True
    assert q3["vulnerability_index"] >= 50.0
    assert "Third-Quarter" in q3["countermeasure_guidance"]


def test_screener_database_hash_chain():
    """Verify cryptographic SHA-256 hash chaining on screener_records."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = os.path.join(tmpdir, "screener_test.db")
        init_db(db)

        p1, r1 = log_screener_record("PHQ-9", 3, 27, "MINIMAL", [0]*9, False, "", 20.0, "Nominal", "Continue", "Astronaut", db_path=db)
        p2, r2 = log_screener_record("GAD-7", 5, 21, "MILD", [1,1,1,0,0,1,1], False, "", 25.0, "Mild anxiety", "Relaxation", "Astronaut", db_path=db)

        assert p2 == r1
        valid, fail_id = verify_screener_records_hash_chain(db)
        assert valid is True
        assert fail_id is None

        # Check retrieval
        df = get_screener_records(db_path=db)
        assert len(df) == 2

        # Tamper
        import sqlite3
        conn = sqlite3.connect(db)
        conn.execute("UPDATE screener_records SET total_score = 99 WHERE id = 1")
        conn.commit()
        conn.close()

        valid_tampered, fail_id = verify_screener_records_hash_chain(db)
        assert valid_tampered is False
        assert fail_id == 1


# ─────────────────────────────────────────────────────────────────────────────
# 4. Dr. Law (2014) CO2-Headache Hazard Model Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_law2014_co2_hazard_odds_ratio():
    """Verify Dr. Law (2014) CO2-headache hazard odds doubling per 1 mmHg."""
    # Baseline nominal: 2.0 mmHg -> OR = 1.0
    h2 = calculate_law2014_headache_odds(co2_mmhg=2.0, baseline_co2=2.0)
    assert h2["odds_ratio"] == 1.0
    assert h2["risk_level"] == "NOMINAL"

    # 3.0 mmHg: 1 mmHg above baseline -> OR = 2.0^1 = 2.0 (doubles)
    h3 = calculate_law2014_headache_odds(co2_mmhg=3.0, baseline_co2=2.0)
    assert h3["odds_ratio"] == 2.0
    assert h3["risk_level"] == "ELEVATED"

    # 4.0 mmHg: 2 mmHg above baseline -> OR = 2.0^2 = 4.0 (quadruples)
    h4 = calculate_law2014_headache_odds(co2_mmhg=4.0, baseline_co2=2.0)
    assert h4["odds_ratio"] == 4.0

    # 7.0 mmHg: 5 mmHg above baseline -> OR = 2.0^5 = 32.0 (critical toxicity threshold)
    h7 = calculate_law2014_headache_odds(co2_mmhg=7.0, baseline_co2=2.0)
    assert h7["odds_ratio"] == 32.0
    assert h7["risk_level"] == "CRITICAL"
    assert "Law J, Watkins S, Alexander D" in h7["citation"]


# ─────────────────────────────────────────────────────────────────────────────
# 5. Medical KB & Emergency Checklists Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_medical_kb_search_and_retrieval():
    """Verify curated local medical reference search."""
    res_co2 = search_medical_knowledge("carbon dioxide headache scrubber")
    assert len(res_co2) > 0
    assert res_co2[0]["id"] == "KB_CO2_HYPERCAPNIA"
    assert any("Law J" in c for c in res_co2[0]["citations"])

    res_sans = search_medical_knowledge("optic disc edema vision sans")
    assert len(res_sans) > 0
    assert res_sans[0]["id"] == "KB_SANS"
    assert any("Mader TH" in c for c in res_sans[0]["citations"])


def test_emergency_checklists_retrieval():
    """Verify ammonia, trauma, and ocular debris emergency checklists."""
    ammonia_cl = get_emergency_checklist("checklist_ammonia")
    assert ammonia_cl is not None
    assert ammonia_cl["priority"] == "CRITICAL"
    assert len(ammonia_cl["steps"]) >= 5
    assert "DON EMERGENCY OXYGEN MASK" in ammonia_cl["steps"][0]["action"]

    trauma_cl = get_emergency_checklist("checklist_trauma")
    assert trauma_cl is not None
    assert "APPLY DIRECT PRESSURE" in trauma_cl["steps"][0]["action"]

    ocular_cl = get_emergency_checklist("checklist_ocular_debris")
    assert ocular_cl is not None
    assert "DO NOT RUB EYE" in ocular_cl["steps"][0]["action"]

    all_cls = get_all_emergency_checklists()
    assert len(all_cls) >= 3


def test_medical_kb_grounding_and_out_of_scope_refusal():
    """Verify Phi-3 knowledge base grounding and refusal on out-of-scope inquiries."""
    # In-scope: Space Motion Sickness
    in_scope, matched = is_query_in_scope("I am having acute space motion sickness and vomiting")
    assert in_scope is True
    assert matched is not None
    context, ok = get_curated_grounding_context("I am having acute space motion sickness and vomiting")
    assert ok is True
    assert "Science" in context or "Oman CM" in context or "Promethazine" in context

    # Out-of-scope: Chemotherapy for colon cancer
    in_scope_out, _ = is_query_in_scope("What chemotherapy regimen should I use for Stage 4 colon cancer?")
    assert in_scope_out is False
    refusal, ok = get_curated_grounding_context("What chemotherapy regimen should I use for Stage 4 colon cancer?")
    assert ok is False
    assert refusal == EXPLICIT_REFUSAL_MESSAGE


# ─────────────────────────────────────────────────────────────────────────────
# 6. Built-In Self-Test (BIST) Diagnostic Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_bist_subsystem_checks():
    """Verify camera, mic, models, ram, and database diagnostic checks."""
    cam = check_cameras()
    assert cam["status"] in ("PASSED", "DEGRADED")

    mic = check_microphones()
    assert mic["status"] in ("PASSED", "DEGRADED")

    models = check_models_on_disk()
    assert models["status"] in ("PASSED", "DEGRADED")
    assert "models" in models

    ram = check_ram_and_resources()
    assert ram["status"] in ("PASSED", "DEGRADED", "FAILED")
    assert ram["available_mb"] > 0

    with tempfile.TemporaryDirectory() as tmpdir:
        db = os.path.join(tmpdir, "bist_test.db")
        init_db(db)
        db_res = check_database_integrity(db_path=db)
        assert db_res["status"] == "PASSED"
        assert db_res["all_chains_valid"] is True


def test_bist_full_run():
    """Verify end-to-end BIST diagnostic execution and report generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = os.path.join(tmpdir, "bist_full.db")
        init_db(db)
        report = run_bist(db_path=db)

        assert report["overall_status"] in ("PASSED", "DEGRADED")
        assert report["duration_ms"] > 0
        assert "subsystems" in report
        assert "database_cryptography" in report["subsystems"]
        assert report["subsystems"]["database_cryptography"]["status"] == "PASSED"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Clinical REST Endpoints & Voice Command Intent Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_clinical_rest_endpoints():
    """Verify FastAPI clinical endpoints."""
    client = TestClient(app)

    # 1. Environment & Hazard model
    r_env = client.get("/api/clinical/environment")
    assert r_env.status_code == 200
    env_data = r_env.json()
    assert "cabin_co2_mmhg" in env_data
    assert "co2_headache_hazard" in env_data

    r_haz = client.get("/api/clinical/environment/hazard-model?co2_mmhg=4.0")
    assert r_haz.status_code == 200
    assert r_haz.json()["odds_ratio"] == 4.0

    # 2. Sleep & Orbital cycle
    r_sleep = client.get("/api/clinical/sleep")
    assert r_sleep.status_code == 200
    sleep_data = r_sleep.json()
    assert "sleep_debt" in sleep_data
    assert "circadian_phase" in sleep_data
    assert "orbital_cycle" in sleep_data

    r_orb = client.get("/api/clinical/sleep/orbital-cycle")
    assert r_orb.status_code == 200
    assert "orbit_period_minutes" in r_orb.json()

    # 3. Screener submission
    r_phq = client.post("/api/clinical/screener/submit", json={
        "screener_type": "PHQ-9",
        "item_responses": [1, 1, 0, 1, 0, 0, 0, 0, 0],
        "crew_member": "Cdr. Sharma",
    })
    assert r_phq.status_code == 200
    phq_data = r_phq.json()
    assert phq_data["status"] == "scored_and_logged"
    assert phq_data["result"]["total_score"] == 3
    assert phq_data["result"]["safety_alert"] is False

    # 4. Emergency Checklists
    r_cls = client.get("/api/clinical/checklists")
    assert r_cls.status_code == 200
    assert len(r_cls.json()["checklists"]) >= 3

    r_amm = client.get("/api/clinical/checklists/checklist_ammonia")
    assert r_amm.status_code == 200
    assert r_amm.json()["id"] == "checklist_ammonia"

    # 5. References
    r_refs = client.get("/api/clinical/references?query=sans")
    assert r_refs.status_code == 200
    assert len(r_refs.json()["references"]) >= 1

    # 6. BIST Endpoint
    r_bist = client.post("/api/clinical/bist/run")
    assert r_bist.status_code == 200
    assert r_bist.json()["overall_status"] in ("PASSED", "DEGRADED")


def test_clinical_voice_intents():
    """Verify voice intent recognition for new clinical commands."""
    # PVT commands
    p_start_pvt = parse_intent("start pvt test")
    assert p_start_pvt["intent"] == "start_pvt"

    p_stop_pvt = parse_intent("stop pvt")
    assert p_stop_pvt["intent"] == "stop_pvt"

    # Screener commands
    p_dep = parse_intent("start depression check")
    assert p_dep["intent"] == "screener_depression"

    p_anx = parse_intent("start anxiety check")
    assert p_anx["intent"] == "screener_anxiety"

    # Emergency checklists
    p_amm = parse_intent("checklist ammonia")
    assert p_amm["intent"] == "checklist_ammonia"

    p_trauma = parse_intent("checklist trauma")
    assert p_trauma["intent"] == "checklist_trauma"

    # Navigation
    p_nav_clin = parse_intent("open clinical")
    assert p_nav_clin["intent"] == "navigate_clinical"

    p_nav_sleep = parse_intent("open sleep")
    assert p_nav_sleep["intent"] == "navigate_sleep"
