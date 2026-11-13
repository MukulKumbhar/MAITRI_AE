"""
MAITRI 2.0 — Comprehensive Clinical Core Automated Test Suite
Phase 2 Step 1 Verification:
1. Cardio-Respiratory calculation & HRV metrics (rMSSD, SDNN, Baevsky Stress Index, respiratory rate)
   with bilateral resting thresholds and clinical citations (ESC/NASPE 1996; Baevsky et al.).
2. Personal baseline calibration (Z-Score & Page's CUSUM drift detection) for cephalic
   fluid shift ("puffy-face") bias mitigation and explainable fusion breakdowns.
3. IEC 60601-1-8 tiered alarm management (HIGH, MEDIUM, LOW, INFO) with deduplication,
   acknowledgment tracking, 120-second clinical audio pause/mute, and 3-minute auto-escalation.
4. SQLite schema migration, alarm events ledger, and SHA-256 cryptographic hash chaining verification.
"""

import math
import os
import sqlite3
import tempfile
import time
from typing import Dict, List

import pytest

# Modules under test
from modules.vitals_module import (
    CARDIO_THRESHOLDS,
    CITATIONS,
    VitalsResult,
    calculate_hrv_metrics,
    calculate_respiratory_rate,
    compute_hrv_strain,
    compute_vitals_strain,
    generate_synthetic_rr,
)
from modules.fusion_module import (
    FusionState,
    PersonalBaseline,
    fuse,
)
from backend.state import (
    AlarmEvent,
    AlarmManager,
    AlarmPriority,
    AuditHashChain,
    HardwareSensorAdapter,
)
import modules.database_module as db_mod


# ─────────────────────────────────────────────────────────────────────────────
# 1. Cardio-Respiratory & HRV Metrics (ESC/NASPE 1996 & Baevsky et al.)
# ─────────────────────────────────────────────────────────────────────────────

class TestCardioRespiratoryAndHRV:
    def test_hrv_rmssd_exact_calculation(self):
        """Verify rMSSD calculation matches standard time-domain formula sqrt(mean(diff^2))."""
        # Known RR intervals (ms)
        rr = [800.0, 820.0, 790.0, 810.0, 805.0]
        # diffs = [20, -30, 20, -5]
        # diffs^2 = [400, 900, 400, 25] = 1725
        # mean(diff^2) = 1725 / 4 = 431.25
        # rMSSD = sqrt(431.25) = 20.7665...
        expected_rmssd = math.sqrt(1725.0 / 4.0)
        metrics = calculate_hrv_metrics(rr)
        assert metrics["rmssd"] == pytest.approx(expected_rmssd, abs=0.05)

    def test_hrv_sdnn_exact_calculation(self):
        """Verify SDNN calculation matches sample standard deviation (N-1 divisor)."""
        rr = [800.0, 820.0, 790.0, 810.0, 805.0]
        mean_rr = sum(rr) / len(rr)  # 805.0
        # deviations: [-5, 15, -15, 5, 0]
        # dev^2: [25, 225, 225, 25, 0] = 500
        # s^2 = 500 / 4 = 125
        expected_sdnn = math.sqrt(125.0)
        metrics = calculate_hrv_metrics(rr)
        assert metrics["sdnn"] == pytest.approx(expected_sdnn, abs=0.05)

    def test_baevsky_stress_index_calculation(self):
        """
        Verify Baevsky Stress Index calculation SI = AMo / (2 * Mo * MxDMn).
        Source: Baevsky et al. (1984, 2001) Space Medicine & Human Physiology.
        """
        # Synthesize intervals around 800 ms with small variation (sympathetic stress)
        # All intervals between 750 and 850 ms -> range = 0.10s
        # modal bin around 800 ms (0.80s)
        rr = [800.0] * 15 + [780.0] * 5 + [820.0] * 5  # N = 25
        metrics = calculate_hrv_metrics(rr)

        assert metrics["mode_rr"] > 0.0
        assert metrics["amo"] > 0.0
        assert metrics["mx_dmn"] > 0.0
        expected_si = metrics["amo"] / (2.0 * metrics["mode_rr"] * metrics["mx_dmn"])
        assert metrics["baevsky_index"] == pytest.approx(expected_si, abs=1.0)
        assert metrics["baevsky_index"] > 50.0  # Significant stress index

    def test_synthetic_rr_generation_with_rsa(self):
        """Verify physiological synthetic RR generator simulates respiratory sinus arrhythmia."""
        rr_resting = generate_synthetic_rr(heart_rate=70.0, count=40, stress_factor=0.0, respiratory_rate=14.0)
        assert len(rr_resting) == 40
        mean_resting = sum(rr_resting) / len(rr_resting)
        assert mean_resting == pytest.approx(60000.0 / 70.0, abs=15.0)

        # High stress reduces HRV variability (vagolysis)
        rr_stressed = generate_synthetic_rr(heart_rate=110.0, count=40, stress_factor=0.9, respiratory_rate=22.0)
        metrics_rest = calculate_hrv_metrics(rr_resting)
        metrics_stressed = calculate_hrv_metrics(rr_stressed)
        # Resting rMSSD should be higher than stressed rMSSD
        assert metrics_rest["rmssd"] > metrics_stressed["rmssd"]

    def test_respiratory_rate_calculation(self):
        """Verify respiratory rate calculation from direct input, RSA, or physiological coupling."""
        # Direct override
        assert calculate_respiratory_rate(base_rr=16.5) == 16.5
        # Clamped limits
        assert calculate_respiratory_rate(base_rr=5.0) == 6.0
        assert calculate_respiratory_rate(base_rr=45.0) == 40.0
        # Physiological coupling at rest (HR 70 -> ~12.6 breaths/min)
        resp_rest = calculate_respiratory_rate(heart_rate=70.0)
        assert 12.0 <= resp_rest <= 14.0
        # Exertion coupling (HR 120 -> elevated respiration)
        resp_exert = calculate_respiratory_rate(heart_rate=120.0)
        assert resp_exert > resp_rest

    def test_cardio_thresholds_and_citations(self):
        """Verify clinical threshold structure and cited standards."""
        assert "heart_rate" in CARDIO_THRESHOLDS
        assert "rmssd" in CARDIO_THRESHOLDS
        assert "sdnn" in CARDIO_THRESHOLDS
        assert "baevsky_index" in CARDIO_THRESHOLDS
        assert "respiratory_rate" in CARDIO_THRESHOLDS
        assert "spo2" in CARDIO_THRESHOLDS

        # Verify bilateral bounds exist
        hr_th = CARDIO_THRESHOLDS["heart_rate"]
        assert hr_th["low_critical"] < hr_th["low_warning"] < hr_th["nominal_min"] < hr_th["nominal_max"] < hr_th["high_warning"] < hr_th["high_critical"]
        assert "ESC/NASPE" in hr_th["citation"]

        rmssd_th = CARDIO_THRESHOLDS["rmssd"]
        assert rmssd_th["low_critical"] == 15.0
        assert rmssd_th["nominal_min"] == 25.0
        assert "ESC/NASPE" in rmssd_th["citation"]

        baevsky_th = CARDIO_THRESHOLDS["baevsky_index"]
        assert baevsky_th["nominal_min"] == 50.0
        assert baevsky_th["nominal_max"] == 150.0
        assert "Baevsky" in baevsky_th["citation"]

    def test_compute_vitals_strain_composite_and_status(self):
        """Verify composite vitals strain with normal, elevated, and critical scenarios."""
        # 1. Nominal resting
        res_norm = compute_vitals_strain(heart_rate=70.0, temperature=36.6, spo2=98.0)
        assert res_norm.vitals_strain < 0.40
        assert res_norm.status == "Normal"
        assert res_norm.rmssd > 25.0

        # 2. Elevated strain (moderate tachycardia, mild fever)
        res_elev = compute_vitals_strain(heart_rate=105.0, temperature=37.8, spo2=96.0)
        assert 0.40 <= res_elev.vitals_strain < 0.70
        assert res_elev.status == "Elevated"

        # 3. Critical strain (severe hypoxia, hyperthermia, extreme tachycardia)
        res_crit = compute_vitals_strain(heart_rate=135.0, temperature=39.2, spo2=86.0)
        assert res_crit.vitals_strain >= 0.70
        assert res_crit.status == "Critical"

    def test_hrv_edge_cases(self):
        """Verify robustness against empty inputs, single intervals, and outliers."""
        empty_res = calculate_hrv_metrics([])
        assert empty_res["rmssd"] > 0.0
        assert empty_res["baevsky_index"] > 0.0

        single_res = calculate_hrv_metrics([800.0])
        assert single_res["rmssd"] > 0.0

        # Intervals with non-physiological values are filtered
        outlier_res = calculate_hrv_metrics([50.0, 800.0, 820.0, 5000.0])
        assert outlier_res["mean_rr"] == pytest.approx(810.0, abs=5.0)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Personal Baseline Calibration & CUSUM Drift Detection
# ─────────────────────────────────────────────────────────────────────────────

class TestPersonalBaselineAndCUSUM:
    def test_calibration_accumulation_and_setpoint(self):
        """Verify calibration accumulates resting mean and marks baseline calibrated after target."""
        pb = PersonalBaseline(calibration_target=10)
        assert not pb.is_calibrated

        dummy_probs = {"neutral": 0.8, "happy": 0.1, "disgust": 0.05, "sad": 0.05, "angry": 0.0, "fear": 0.0, "surprise": 0.0}
        for _ in range(10):
            pb.calibrate_step(face_probs=dummy_probs, vitals_strain=0.15, ear=0.29, fatigue_strain=0.10)

        assert pb.sample_count == 10
        assert pb.is_calibrated
        assert pb.mu_ear == pytest.approx(0.29, abs=0.01)
        assert pb.mu_vitals_strain == pytest.approx(0.15, abs=0.01)

    def test_z_score_calculation(self):
        """Verify standard normal deviation Z = (x - mu) / sigma."""
        pb = PersonalBaseline()
        pb.mu_vitals_strain = 0.20
        pb.sigma_vitals_strain = 0.05

        # Exactly at mean -> Z = 0
        assert pb.compute_z_score("vitals_strain", 0.20) == pytest.approx(0.0, abs=0.01)
        # 1 sigma above mean -> Z = 1.0
        assert pb.compute_z_score("vitals_strain", 0.25) == pytest.approx(1.0, abs=0.01)
        # 2 sigma below mean -> Z = -2.0
        assert pb.compute_z_score("vitals_strain", 0.10) == pytest.approx(-2.0, abs=0.01)

    def test_cephalic_fluid_shift_bias_mitigation(self):
        """
        Verify that microgravity cephalic fluid shift ("puffy-face" syndrome)
        baseline offsets are compensated so resting edema does not trigger false distress.
        """
        pb = PersonalBaseline(calibration_target=5)
        # Simulate puffy-face resting affect: Earth model assigns 0.18 disgust and 0.15 sadness due to facial swelling
        puffy_face_resting = {
            "disgust": 0.18, "sad": 0.15, "angry": 0.05,
            "neutral": 0.55, "happy": 0.07, "fear": 0.0, "surprise": 0.0
        }
        for _ in range(5):
            pb.calibrate_step(face_probs=puffy_face_resting, vitals_strain=0.10)

        assert pb.is_calibrated

        # When evaluated with the same resting puffy-face, adjusted probabilities should suppress false disgust
        adjusted = pb.adjust_for_cephalic_fluid_shift(puffy_face_resting)
        assert adjusted["disgust"] < puffy_face_resting["disgust"]
        assert adjusted["sad"] < puffy_face_resting["sad"]
        assert adjusted["neutral"] > puffy_face_resting["neutral"]

    def test_cusum_drift_detection_sustained_shift(self):
        """
        Verify Page's CUSUM control chart flags sustained physiological drift
        when values shift by >= 1.5 sigma over consecutive readings.
        """
        pb = PersonalBaseline()
        pb.mu_vitals_strain = 0.10
        pb.sigma_vitals_strain = 0.05
        pb.cusum_k = 0.5
        pb.cusum_h = 4.0

        # Feed 10 steps of elevated strain (0.25 = 3.0 sigma above mean)
        drift_flagged = False
        for _ in range(10):
            sh, sl, drift = pb.update_cusum("vitals_strain", 0.25)
            if drift:
                drift_flagged = True
                break

        assert drift_flagged, "CUSUM should flag sustained upward drift"
        assert pb.cusum_drift["vitals_strain"] is True

    def test_cusum_no_false_alarm_on_nominal_noise(self):
        """Verify CUSUM does not drift on nominal zero-mean fluctuations."""
        pb = PersonalBaseline()
        pb.mu_vitals_strain = 0.10
        pb.sigma_vitals_strain = 0.05
        pb.cusum_k = 0.5
        pb.cusum_h = 4.0

        for val in [0.11, 0.09, 0.10, 0.12, 0.08, 0.10, 0.11]:
            _, _, drift = pb.update_cusum("vitals_strain", val)
            assert not drift

        assert pb.cusum_drift["vitals_strain"] is False

    def test_explainable_fusion_breakdown_structure(self):
        """Verify fuse outputs explainable breakdown with percentage weights and clinical rationales."""
        state = FusionState()
        face_probs = {"neutral": 0.9, "happy": 0.1}
        res = fuse(
            state=state,
            face_probs=face_probs,
            face_quality=0.95,
            vitals_strain=0.20,
            fatigue_strain=0.05,
            eye_quality=1.0,
            voice_probs=None,
            is_speaking=False,
        )

        assert hasattr(res, "explainable_breakdown")
        bd = res.explainable_breakdown
        assert "weights_pct" in bd
        assert "modality_contributions_pct" in bd
        assert "baseline" in bd
        assert "clinical_rationales" in bd

        # Check weights sum to ~100%
        w_sum = sum(bd["weights_pct"].values())
        assert w_sum == pytest.approx(100.0, abs=1.0)
        # Check voice is gated to 0 in silence
        assert bd["weights_pct"]["voice"] == 0.0
        # Rationales contain clinical explanations
        assert any("Voice gated to 0.0%" in r for r in bd["clinical_rationales"])


# ─────────────────────────────────────────────────────────────────────────────
# 3. IEC 60601-1-8 Tiered Alarm Structure & Deduplication
# ─────────────────────────────────────────────────────────────────────────────

class TestIEC60601Alarms:
    def test_alarm_priorities_high_medium_low_info(self):
        """Verify IEC 60601-1-8 tiered priorities can be raised and counted."""
        mgr = AlarmManager()
        a_high = mgr.raise_alarm("HR_HIGH_CRIT", "HIGH", "Heart rate critical 140 BPM")
        a_med = mgr.raise_alarm("SPO2_WARN", "MEDIUM", "SpO2 warning 92%")
        a_low = mgr.raise_alarm("TEMP_LOW", "LOW", "Skin temp slightly cool")
        a_info = mgr.raise_alarm("SYS_READY", "INFO", "Hardware sensor ready")

        assert a_high.priority == "HIGH"
        assert a_med.priority == "MEDIUM"
        assert a_low.priority == "LOW"
        assert a_info.priority == "INFO"

        summary = mgr.get_summary()
        assert summary["total_active"] == 4
        assert summary["high_count"] == 1
        assert summary["medium_count"] == 1
        assert summary["low_count"] == 1
        assert summary["info_count"] == 1

    def test_alarm_deduplication(self):
        """Verify repeated alarms with same code update occurrence count without duplicate records."""
        mgr = AlarmManager()
        a1 = mgr.raise_alarm("TACHYCARDIA_01", "HIGH", "Heart rate 132 BPM")
        time.sleep(0.01)
        a2 = mgr.raise_alarm("TACHYCARDIA_01", "HIGH", "Heart rate 135 BPM")

        assert a1.alarm_id == a2.alarm_id
        assert a2.occurrence_count == 2
        assert len(mgr.active_alarms) == 1
        assert a2.message == "Heart rate 135 BPM"

    def test_alarm_acknowledgment_and_resolution(self):
        """Verify alarm acknowledgment tracking and resolution."""
        mgr = AlarmManager()
        alarm = mgr.raise_alarm("HYPOXIA_01", "HIGH", "SpO2 at 87%")
        assert not alarm.acknowledged

        # Acknowledge
        acked = mgr.acknowledge_alarm("HYPOXIA_01", ack_by="Cdr. Sharma")
        assert acked is not None
        assert acked.acknowledged is True
        assert acked.ack_by == "Cdr. Sharma"
        assert acked.ack_timestamp is not None

        # Resolve
        resolved = mgr.resolve_alarm("HYPOXIA_01")
        assert resolved is not None
        assert resolved.active is False
        assert "HYPOXIA_01" not in mgr.active_alarms

    def test_120s_clinical_audio_pause(self):
        """Verify 120-second clinical audio pause/mute pursuant to IEC 60601-1-8 clause 6.8.4."""
        mgr = AlarmManager()
        assert not mgr.is_audio_paused()

        # Pause audio for 120s
        pause_until = mgr.pause_audio(duration_sec=120.0)
        assert mgr.is_audio_paused()
        rem = mgr.remaining_audio_pause_sec()
        assert 118.0 <= rem <= 120.0

        # Simulate expired pause
        mgr.audio_pause_until = time.time() - 1.0
        assert not mgr.is_audio_paused()
        assert mgr.remaining_audio_pause_sec() == 0.0

    def test_3min_auto_escalation_of_unacknowledged_alarms(self):
        """
        Verify unacknowledged alarms auto-escalate after 180 seconds (3 minutes):
        LOW -> MEDIUM, MEDIUM -> HIGH.
        """
        mgr = AlarmManager()
        t0 = 1000.0
        alarm_low = mgr.raise_alarm("CO2_WARN", "LOW", "CO2 rising slightly")
        alarm_low.created_at = t0

        alarm_med = mgr.raise_alarm("HYPOXIA_WARN", "MEDIUM", "SpO2 at 92%")
        alarm_med.created_at = t0

        # Case 1: Check before 180s (at t = 1100s, age = 100s) -> No escalation
        escalated_none = mgr.check_escalation(now=t0 + 100.0)
        assert len(escalated_none) == 0
        assert alarm_low.priority == "LOW"
        assert alarm_med.priority == "MEDIUM"

        # Case 2: Check after 180s (at t = 1185s, age = 185s) -> Escalation triggers
        escalated = mgr.check_escalation(now=t0 + 185.0)
        assert len(escalated) == 2
        assert alarm_low.priority == "MEDIUM"
        assert alarm_low.escalated is True
        assert alarm_low.original_priority == "LOW"

        assert alarm_med.priority == "HIGH"
        assert alarm_med.escalated is True
        assert alarm_med.original_priority == "MEDIUM"

    def test_acknowledged_alarms_do_not_escalate(self):
        """Verify that an acknowledged alarm does NOT escalate even after 180 seconds."""
        mgr = AlarmManager()
        t0 = 1000.0
        alarm = mgr.raise_alarm("HR_HIGH", "MEDIUM", "Tachycardia 108 BPM")
        alarm.created_at = t0
        mgr.acknowledge_alarm("HR_HIGH")

        escalated = mgr.check_escalation(now=t0 + 200.0)
        assert len(escalated) == 0
        assert alarm.priority == "MEDIUM"
        assert alarm.escalated is False


# ─────────────────────────────────────────────────────────────────────────────
# 4. SQLite Schema Migration & SHA-256 Cryptographic Hash Chaining
# ─────────────────────────────────────────────────────────────────────────────

class TestDatabaseAndAuditHashChain:
    @pytest.fixture
    def test_db(self, tmp_path):
        db_file = str(tmp_path / "test_maitri_clinical.db")
        db_mod.init_db(db_file)
        yield db_file
        if os.path.exists(db_file):
            os.remove(db_file)

    def test_schema_creates_all_columns_and_alarm_table(self, test_db):
        """Verify SQLite tables have all required HRV, environmental, and cryptographic columns."""
        conn = sqlite3.connect(test_db)
        c = conn.cursor()

        # Check stress_logs columns
        c.execute("PRAGMA table_info(stress_logs)")
        cols = {row[1] for row in c.fetchall()}
        required_cols = {
            "rmssd", "sdnn", "baevsky_index", "respiratory_rate",
            "co2_mmhg", "o2_percent", "pressure_kpa", "ambient_temp_c", "noise_dba",
            "prev_hash", "record_hash"
        }
        for col in required_cols:
            assert col in cols, f"Missing column in stress_logs: {col}"

        # Check alarm_events table
        c.execute("PRAGMA table_info(alarm_events)")
        alarm_cols = {row[1] for row in c.fetchall()}
        assert "alarm_id" in alarm_cols
        assert "priority" in alarm_cols
        assert "code" in alarm_cols
        assert "prev_hash" in alarm_cols
        assert "record_hash" in alarm_cols
        conn.close()

    def test_schema_migration_preserves_existing_data(self, tmp_path):
        """Verify migration can run on an existing legacy table without losing data."""
        legacy_db = str(tmp_path / "legacy_test.db")
        conn = sqlite3.connect(legacy_db)
        c = conn.cursor()
        # Create minimal old table
        c.execute("""
            CREATE TABLE stress_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                face_emotion TEXT,
                heart_rate REAL,
                stress_score REAL
            )
        """)
        c.execute("INSERT INTO stress_logs (timestamp, face_emotion, heart_rate, stress_score) VALUES ('2026-11-13 12:00:00', 'neutral', 72.0, 15.0)")
        conn.commit()
        conn.close()

        # Run init_db migration
        db_mod.init_db(legacy_db)

        conn = sqlite3.connect(legacy_db)
        c = conn.cursor()
        c.execute("SELECT heart_rate, rmssd, co2_mmhg FROM stress_logs WHERE id=1")
        row = c.fetchone()
        conn.close()

        assert row[0] == 72.0  # Preserved
        assert row[1] == 42.0  # Migrated default
        assert row[2] == 3.0   # Migrated default

    def test_telemetry_cryptographic_hash_chain_integrity(self, test_db):
        """Verify that consecutive telemetry records form an unbroken SHA-256 hash chain."""
        prev1, hash1 = db_mod.log_event(
            face_emotion="neutral", fused_emotion="neutral", voice_state="silent",
            heart_rate=72.0, temperature=36.6, spo2=98.0, blink_rate=15.0,
            fatigue_label="Normal", stress_score=20.0, stress_level="NOMINAL",
            alert_triggered="", response_msg="", rmssd=45.0, baevsky_index=85.0,
            db_path=test_db
        )
        assert prev1 == db_mod.GENESIS_HASH
        assert len(hash1) == 64

        prev2, hash2 = db_mod.log_event(
            face_emotion="neutral", fused_emotion="neutral", voice_state="silent",
            heart_rate=75.0, temperature=36.6, spo2=98.0, blink_rate=16.0,
            fatigue_label="Normal", stress_score=22.0, stress_level="NOMINAL",
            alert_triggered="", response_msg="", rmssd=43.0, baevsky_index=90.0,
            db_path=test_db
        )
        # Block 2's prev_hash MUST be Block 1's record_hash
        assert prev2 == hash1
        assert len(hash2) == 64

        # Chain verification
        is_valid, fail_idx = db_mod.verify_stress_logs_hash_chain(test_db)
        assert is_valid is True
        assert fail_idx is None

    def test_telemetry_hash_chain_detects_tampering(self, test_db):
        """Verify that modifying a historical telemetry record invalidates the cryptographic chain."""
        db_mod.log_event(
            face_emotion="neutral", fused_emotion="neutral", voice_state="silent",
            heart_rate=70.0, temperature=36.6, spo2=98.0, blink_rate=14.0,
            fatigue_label="Normal", stress_score=15.0, stress_level="NOMINAL",
            alert_triggered="", response_msg="", db_path=test_db
        )
        db_mod.log_event(
            face_emotion="neutral", fused_emotion="neutral", voice_state="silent",
            heart_rate=72.0, temperature=36.6, spo2=98.0, blink_rate=14.0,
            fatigue_label="Normal", stress_score=18.0, stress_level="NOMINAL",
            alert_triggered="", response_msg="", db_path=test_db
        )

        # Confirm valid before tampering
        is_valid, _ = db_mod.verify_stress_logs_hash_chain(test_db)
        assert is_valid is True

        # Maliciously tamper with heart_rate in row 1
        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        c.execute("UPDATE stress_logs SET heart_rate=199.0 WHERE id=1")
        conn.commit()
        conn.close()

        # Verification must detect corruption at record id 1
        is_valid_after, fail_rec_id = db_mod.verify_stress_logs_hash_chain(test_db)
        assert is_valid_after is False
        assert fail_rec_id == 1

    def test_alarm_events_cryptographic_hash_chain(self, test_db):
        """Verify IEC 60601-1-8 alarm events ledger forms a verifiable hash chain."""
        p1, h1 = db_mod.log_alarm_event(
            alarm_id="ALM_001", priority="HIGH", code="HR_HIGH",
            message="Heart rate 135 BPM", db_path=test_db
        )
        p2, h2 = db_mod.log_alarm_event(
            alarm_id="ALM_002", priority="MEDIUM", code="SPO2_LOW",
            message="SpO2 at 92%", db_path=test_db
        )

        assert p1 == db_mod.GENESIS_HASH
        assert p2 == h1

        is_valid, fail_idx = db_mod.verify_alarm_events_hash_chain(test_db)
        assert is_valid is True
        assert fail_idx is None

        # Verify tamper detection on alarm events
        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        c.execute("UPDATE alarm_events SET priority='LOW' WHERE id=1")
        conn.commit()
        conn.close()

        is_valid_tampered, fail_id = db_mod.verify_alarm_events_hash_chain(test_db)
        assert is_valid_tampered is False
        assert fail_id == 1

    def test_verify_empty_db_hash_chain(self, test_db):
        """Verify empty database returns valid hash chain with no errors."""
        valid_stress, err_stress = db_mod.verify_stress_logs_hash_chain(test_db)
        assert valid_stress is True
        assert err_stress is None

        valid_alarm, err_alarm = db_mod.verify_alarm_events_hash_chain(test_db)
        assert valid_alarm is True
        assert err_alarm is None


# ─────────────────────────────────────────────────────────────────────────────
# 5. Hardware Sensor Adapter & Audit Hash Chain Class
# ─────────────────────────────────────────────────────────────────────────────

class TestHardwareSensorAdapterAndAuditChain:
    def test_hardware_adapter_modes_and_scenarios(self):
        """Verify hardware adapter transitions between live, manual, and replay modes."""
        adapter = HardwareSensorAdapter(mode="manual")
        assert adapter.mode == "manual"

        adapter.set_mode("replay")
        assert adapter.mode == "replay"

        adapter.set_mode("invalid_mode")
        assert adapter.mode == "replay"  # Ignored invalid mode

        # Test scenario stepping
        adapter.set_scenario("co2_retention")
        sim_step1 = adapter.step_simulation(dt=1.0)
        assert "heart_rate" in sim_step1
        assert "co2_mmhg" in sim_step1
        assert "rmssd" in sim_step1
        assert "baevsky_index" in sim_step1

        # Advance 20 seconds of CO2 retention
        sim_step20 = adapter.step_simulation(dt=20.0)
        assert sim_step20["co2_mmhg"] > sim_step1["co2_mmhg"]
        assert sim_step20["heart_rate"] >= sim_step1["heart_rate"]

    def test_hardware_adapter_status_dict(self):
        adapter = HardwareSensorAdapter(mode="live")
        status = adapter.get_status()
        assert status["mode"] == "live"
        assert "channels" in status
        assert "optical_face" in status["channels"]
        assert "ecg_lead" in status["channels"]
        assert status["channels"]["ecg_lead"]["connected"] is True

    def test_audit_hash_chain_direct_class(self):
        """Verify standalone AuditHashChain append and verify_chain methods."""
        chain = AuditHashChain()
        rec1 = {"timestamp": "2026-11-13 12:00:00", "hr": 75.0, "status": "NOMINAL"}
        p1, h1 = chain.append(rec1)
        assert p1 == AuditHashChain.GENESIS_HASH

        rec2 = {"timestamp": "2026-11-13 12:00:01", "hr": 76.0, "status": "NOMINAL"}
        p2, h2 = chain.append(rec2)
        assert p2 == h1

        records = [
            {"id": 1, "prev_hash": p1, "record_hash": h1, **rec1},
            {"id": 2, "prev_hash": p2, "record_hash": h2, **rec2},
        ]
        valid, idx = AuditHashChain.verify_chain(records)
        assert valid is True
        assert idx is None

        # Tamper record 2
        records[1]["hr"] = 190.0
        valid_tampered, fail_idx = AuditHashChain.verify_chain(records)
        assert valid_tampered is False
        assert fail_idx == 1

