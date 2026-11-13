"""
MAITRI 2.0 — Singleton Shared Application State
Holds all runtime objects that must survive across FastAPI requests and WebSocket connections.
Thread-safe access via asyncio.Lock or threading.Lock depending on context.

Phase 2 Extensions:
- HardwareSensorAdapter: supporting modes ['live', 'manual', 'replay'] with
  realistic simulated drift and physiological events.
- IEC 60601-1-8 Tiered Alarm Structure: HIGH, MEDIUM, LOW, INFO with
  deduplication, acknowledge state, 120-second clinical audio pause/mute,
  and 3-minute auto-escalation.
- Cryptographic Hash Chain Tracking: sha256(prev_hash + entry) for audit integrity.
- Cabin Environmental Metrics: CO2, O2, pressure, temperature, noise.
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

# ── Path Setup ────────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

_PROJECT_ROOT: Path = Path(getattr(sys, "_MEIPASS", str(_HERE)))

# ── Import MAITRI modules ─────────────────────────────────────────────────────
from modules.live_state import LiveState
from modules.fusion_module import FusionState
from modules.mission_core import NativeWatchdog, NativeDTNOutbox


# ─────────────────────────────────────────────────────────────────────────────
# Hardware Sensor Adapter State & Simulation Replay
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SensorChannelStatus:
    channel_id: str
    connected: bool = True
    quality: float = 0.98
    last_update: float = field(default_factory=time.time)
    description: str = ""


class HardwareSensorAdapter:
    """
    Hardware Sensor Adapter supporting modes:
    - 'live': Real camera, microphone, and direct hardware inputs.
    - 'manual': Interactive slider/override adjustments.
    - 'replay': Deterministic physiological simulation and scenario replay.
    """
    VALID_MODES = ("live", "manual", "replay")

    def __init__(self, mode: str = "manual"):
        self.mode: str = mode if mode in self.VALID_MODES else "manual"
        self.scenario: str = "nominal_flight"  # nominal_flight, co2_retention, eva_strain, solar_flare
        self.sim_elapsed: float = 0.0
        self.replay_speed: float = 1.0
        self.channels: Dict[str, SensorChannelStatus] = {
            "optical_face": SensorChannelStatus("optical_face", description="Optical RGB Face Tracker"),
            "audio_mic": SensorChannelStatus("audio_mic", description="Dual Cabin Microphone Array"),
            "ppg_sensor": SensorChannelStatus("ppg_sensor", description="Reflectance Pulse Oximeter"),
            "ecg_lead": SensorChannelStatus("ecg_lead", description="Lead-II Bio-Patch"),
            "cabin_eclss": SensorChannelStatus("cabin_eclss", description="ECLSS Atmospheric Bus"),
        }

    def set_mode(self, mode: str) -> None:
        if mode in self.VALID_MODES:
            self.mode = mode

    def set_scenario(self, scenario: str) -> None:
        self.scenario = scenario
        self.sim_elapsed = 0.0

    def step_simulation(self, dt: float = 0.1) -> Dict[str, Any]:
        """
        Advances the simulation clock and returns realistic drifting vitals
        and cabin environmental metrics based on active scenario.
        """
        self.sim_elapsed += dt * self.replay_speed
        t = self.sim_elapsed

        if self.scenario == "co2_retention":
            # CO2 scrubber saturation: CO2 rises, HR increases, respiratory rate increases
            co2 = min(9.5, 3.0 + 0.05 * t)
            o2 = max(19.2, 20.9 - 0.01 * t)
            hr = min(110.0, 72.0 + 0.25 * t)
            rr = min(26.0, 14.0 + 0.10 * t)
            temp = 36.7 + 0.1 * math.sin(t * 0.05)
            spo2 = max(94.0, 98.0 - 0.03 * t)
            rmssd = max(18.0, 45.0 - 0.2 * t)
            baevsky = min(380.0, 90.0 + 2.5 * t)
        elif self.scenario == "eva_strain":
            # Extravehicular physical exertion: high HR, high core temp, high respiratory rate
            co2 = 3.2 + 0.2 * math.sin(t * 0.1)
            o2 = 20.8
            hr = min(140.0, 75.0 + 0.6 * t)
            rr = min(30.0, 15.0 + 0.18 * t)
            temp = min(38.2, 36.8 + 0.015 * t)
            spo2 = max(95.0, 98.0 - 0.02 * t)
            rmssd = max(14.0, 42.0 - 0.3 * t)
            baevsky = min(520.0, 100.0 + 4.0 * t)
        elif self.scenario == "solar_flare":
            # Radiation alarm and acute stress response: HR spikes, rMSSD drops sharply
            co2 = 3.0
            o2 = 20.9
            hr = 85.0 + 15.0 * math.sin(t * 0.2)
            rr = 18.0 + 3.0 * math.cos(t * 0.2)
            temp = 36.9
            spo2 = 98.0
            rmssd = max(16.0, 35.0 - 0.15 * t)
            baevsky = min(420.0, 120.0 + 3.0 * t)
        else:
            # Nominal flight: slight physiological baseline fluctuations with RSA
            co2 = 3.0 + 0.15 * math.sin(t * 0.05)
            o2 = 20.9
            hr = 72.0 + 2.5 * math.sin(t * 0.1) + 1.2 * math.cos(t * 0.3)
            rr = 14.0 + 0.8 * math.sin(t * 0.15)
            temp = 36.6 + 0.05 * math.sin(t * 0.02)
            spo2 = 98.2 + 0.3 * math.cos(t * 0.08)
            rmssd = 45.0 + 4.0 * math.sin(t * 0.1)
            baevsky = 95.0 + 10.0 * math.sin(t * 0.1)

        return {
            "heart_rate": round(hr, 1),
            "temperature": round(temp, 2),
            "spo2": round(min(100.0, spo2), 1),
            "respiratory_rate": round(rr, 1),
            "rmssd": round(rmssd, 1),
            "baevsky_index": round(baevsky, 1),
            "co2_mmhg": round(co2, 2),
            "o2_percent": round(o2, 2),
            "pressure_kpa": 101.3,
            "ambient_temp_c": 22.0,
            "noise_dba": 58.0,
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "scenario": self.scenario,
            "sim_elapsed": round(self.sim_elapsed, 1),
            "replay_speed": self.replay_speed,
            "channels": {
                k: {"connected": v.connected, "quality": v.quality, "description": v.description}
                for k, v in self.channels.items()
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# IEC 60601-1-8 Tiered Alarm Structure & Deduplication
# ─────────────────────────────────────────────────────────────────────────────

class AlarmPriority(str, Enum):
    HIGH = "HIGH"       # Immediate operator response required (Red)
    MEDIUM = "MEDIUM"   # Prompt operator response required (Yellow)
    LOW = "LOW"         # Awareness required (Cyan / Amber)
    INFO = "INFO"       # Informational notification (Blue / White)


@dataclass
class AlarmEvent:
    alarm_id: str                   # e.g. "ALM_HR_001"
    code: str                       # e.g. "HR_HIGH_CRITICAL"
    priority: str                   # "HIGH", "MEDIUM", "LOW", "INFO"
    message: str
    source: str = "clinical"        # "cardiorespiratory", "cabin_env", "affect", "system"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    acknowledged: bool = False
    ack_timestamp: Optional[float] = None
    ack_by: Optional[str] = None
    escalated: bool = False
    escalated_at: Optional[float] = None
    original_priority: Optional[str] = None
    occurrence_count: int = 1
    active: bool = True


class AlarmManager:
    """
    IEC 60601-1-8 Medical Alarm Management System:
    - Tiered alarms: HIGH, MEDIUM, LOW, INFO
    - Alarm deduplication to prevent alarm flooding
    - Operator acknowledgment tracking
    - 120-second clinical audio pause/mute (clause 6.8.4)
    - 3-minute (180s) auto-escalation of unacknowledged alarms
    """
    def __init__(self, db_path: Optional[str] = None):
        self.active_alarms: Dict[str, AlarmEvent] = {}  # key: code
        self.alarm_history: List[AlarmEvent] = []
        self.audio_pause_until: float = 0.0
        self.counter: int = 0
        self.db_path: Optional[str] = db_path

    def _persist_alarm_event(self, alarm: AlarmEvent, status: str, db_path: Optional[str] = None) -> None:
        try:
            import datetime
            from modules.database_module import log_alarm_event
            target_path = db_path or self.db_path
            ack_str = (
                datetime.datetime.fromtimestamp(alarm.ack_timestamp).strftime("%Y-%m-%d %H:%M:%S")
                if alarm.ack_timestamp else None
            )
            res_str = (
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if status == "RESOLVED" else None
            )
            log_alarm_event(
                alarm_id=alarm.alarm_id,
                priority=alarm.priority,
                code=alarm.code,
                message=alarm.message,
                source=alarm.source,
                status=status,
                acknowledged_at=ack_str,
                resolved_at=res_str,
                escalated_from=alarm.original_priority if alarm.escalated else None,
                occurrence_count=alarm.occurrence_count,
                db_path=target_path,
            )
        except Exception:
            pass

    def pause_audio(self, duration_sec: float = 120.0) -> float:
        """Pause clinical alarm audio for 120 seconds (IEC 60601-1-8 clause 6.8.4)."""
        self.audio_pause_until = time.time() + duration_sec
        return self.audio_pause_until

    def is_audio_paused(self) -> bool:
        return time.time() < self.audio_pause_until

    def remaining_audio_pause_sec(self) -> float:
        return max(0.0, self.audio_pause_until - time.time())

    def raise_alarm(
        self,
        code: str,
        priority: str,
        message: str,
        source: str = "clinical",
    ) -> AlarmEvent:
        """
        Raise or update an alarm with automatic deduplication.
        If an active alarm with the same code exists, updates timestamp and increments count.
        """
        now = time.time()
        priority_clean = priority.upper() if priority.upper() in ("HIGH", "MEDIUM", "LOW", "INFO") else "INFO"

        if code in self.active_alarms and self.active_alarms[code].active:
            # Deduplicate
            existing = self.active_alarms[code]
            existing.occurrence_count += 1
            existing.updated_at = now
            existing.message = message
            return existing

        self.counter += 1
        alarm_id = f"ALM_{code[:6]}_{self.counter:04d}"
        alarm = AlarmEvent(
            alarm_id=alarm_id,
            code=code,
            priority=priority_clean,
            message=message,
            source=source,
            created_at=now,
            updated_at=now,
        )
        self.active_alarms[code] = alarm
        self.alarm_history.insert(0, alarm)
        self._persist_alarm_event(alarm, "ACTIVE")
        return alarm

    def acknowledge_alarm(self, code_or_id: str, ack_by: str = "crew") -> Optional[AlarmEvent]:
        now = time.time()
        target: Optional[AlarmEvent] = None
        if code_or_id in self.active_alarms:
            target = self.active_alarms[code_or_id]
        else:
            for a in self.active_alarms.values():
                if a.alarm_id == code_or_id:
                    target = a
                    break

        if target:
            target.acknowledged = True
            target.ack_timestamp = now
            target.ack_by = ack_by
            self._persist_alarm_event(target, "ACKNOWLEDGED")
            return target
        return None

    def resolve_alarm(self, code_or_id: str) -> Optional[AlarmEvent]:
        target: Optional[AlarmEvent] = None
        code_key = None
        if code_or_id in self.active_alarms:
            code_key = code_or_id
            target = self.active_alarms[code_or_id]
        else:
            for k, a in self.active_alarms.items():
                if a.alarm_id == code_or_id:
                    code_key = k
                    target = a
                    break

        if target and code_key:
            target.active = False
            del self.active_alarms[code_key]
            self._persist_alarm_event(target, "RESOLVED")
            return target
        return None

    def check_escalation(self, now: Optional[float] = None) -> List[AlarmEvent]:
        """
        Check for unacknowledged active alarms older than 180s (3 minutes).
        Escalates LOW -> MEDIUM, MEDIUM -> HIGH.
        """
        current_time = now if now is not None else time.time()
        escalated_list: List[AlarmEvent] = []

        for alarm in self.active_alarms.values():
            if alarm.active and not alarm.acknowledged and not alarm.escalated:
                age = current_time - alarm.created_at
                if age >= 180.0:
                    alarm.escalated = True
                    alarm.escalated_at = current_time
                    alarm.original_priority = alarm.priority

                    # Priority escalation mapping
                    if alarm.priority == "LOW":
                        alarm.priority = "MEDIUM"
                    elif alarm.priority == "MEDIUM":
                        alarm.priority = "HIGH"
                    # HIGH remains HIGH, flagged escalated
                    escalated_list.append(alarm)
                    self._persist_alarm_event(alarm, "ESCALATED")

        return escalated_list

    def get_summary(self) -> Dict[str, Any]:
        self.check_escalation()
        active = list(self.active_alarms.values())
        return {
            "total_active": len(active),
            "unacknowledged_count": sum(1 for a in active if not a.acknowledged),
            "audio_paused": self.is_audio_paused(),
            "audio_pause_remaining_sec": round(self.remaining_audio_pause_sec(), 1),
            "high_count": sum(1 for a in active if a.priority == "HIGH"),
            "medium_count": sum(1 for a in active if a.priority == "MEDIUM"),
            "low_count": sum(1 for a in active if a.priority == "LOW"),
            "info_count": sum(1 for a in active if a.priority == "INFO"),
            "active_alarms": [
                {
                    "alarm_id": a.alarm_id,
                    "code": a.code,
                    "priority": a.priority,
                    "message": a.message,
                    "source": a.source,
                    "acknowledged": a.acknowledged,
                    "escalated": a.escalated,
                    "occurrence_count": a.occurrence_count,
                    "created_at": a.created_at,
                }
                for a in active
            ],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Cryptographic Hash Chain Tracking (SHA-256)
# ─────────────────────────────────────────────────────────────────────────────

class AuditHashChain:
    """
    SHA-256 Cryptographic Hash Chain for air-gapped mission audit logging.
    Each entry is chained:
        h_0 = GENESIS_HASH
        h_i = SHA256(h_{i-1} + "|" + CanonicalPayload)
    Provides verifiable tamper-evidence for medical and life-support records.
    """
    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self, genesis: Optional[str] = None):
        self.current_hash: str = genesis or self.GENESIS_HASH
        self.entry_count: int = 0

    def append(self, entry_payload: Any) -> Tuple[str, str]:
        """
        Computes SHA-256 hash chained to current_hash.
        Returns (prev_hash, record_hash).
        """
        prev_hash = self.current_hash
        if isinstance(entry_payload, dict):
            canonical = json.dumps(entry_payload, sort_keys=True, default=str)
        else:
            canonical = str(entry_payload)

        raw = f"{prev_hash}|{canonical}".encode("utf-8")
        record_hash = hashlib.sha256(raw).hexdigest()
        self.current_hash = record_hash
        self.entry_count += 1
        return prev_hash, record_hash

    @staticmethod
    def verify_chain(records: List[Dict[str, Any]]) -> Tuple[bool, Optional[int]]:
        """
        Verifies that records forms an unbroken cryptographic hash chain.
        Returns (is_valid, failing_index).
        """
        if not records:
            return True, None

        expected_prev = records[0].get("prev_hash", AuditHashChain.GENESIS_HASH)
        for idx, rec in enumerate(records):
            actual_prev = rec.get("prev_hash", "")
            if actual_prev != expected_prev:
                return False, idx

            payload = {k: v for k, v in rec.items() if k not in ("prev_hash", "record_hash", "id")}
            canonical = json.dumps(payload, sort_keys=True, default=str)
            computed_hash = hashlib.sha256(f"{actual_prev}|{canonical}".encode("utf-8")).hexdigest()

            actual_record_hash = rec.get("record_hash", "")
            if actual_record_hash and actual_record_hash != computed_hash:
                return False, idx

            expected_prev = actual_record_hash or computed_hash

        return True, None


# ─────────────────────────────────────────────────────────────────────────────
# Dr. Law (2014) CO2-Headache Hazard Model
# ─────────────────────────────────────────────────────────────────────────────

def calculate_law2014_headache_odds(co2_mmhg: float, baseline_co2: float = 2.0) -> Dict[str, Any]:
    """
    Computes headache odds ratio and probability based on Dr. Law et al. (2014).

    Finding: For each 1-mm Hg increase in ambient cabin PCO2, the odds of a crew
    member reporting a headache doubled (Odds Ratio = 2.0 per mmHg increase).
    Reference:
        Law J, Watkins S, Alexander D. Relationship Between Carbon Dioxide Levels
        and Reported Headaches on the International Space Station.
        J Occup Environ Med. 2014;56(5):477-483.
    """
    delta_co2 = max(0.0, float(co2_mmhg) - baseline_co2)
    # Odds ratio doubles per 1 mmHg above baseline: OR = 2.0^(delta)
    odds_ratio = 2.0 ** delta_co2

    # Baseline headache probability in nominal spaceflight (~5% or 0.05 odds)
    baseline_odds = 0.05
    elevated_odds = baseline_odds * odds_ratio
    prob_headache = elevated_odds / (1.0 + elevated_odds)

    if co2_mmhg < 3.0:
        risk_level = "NOMINAL"
        recommendation = "Atmospheric CO2 within safe operational bounds (<3.0 mmHg)."
    elif co2_mmhg < 5.0:
        risk_level = "ELEVATED"
        recommendation = "Elevated CO2. Increase cabin fan airflow; monitor for mild headache or somnolence."
    elif co2_mmhg < 7.0:
        risk_level = "HIGH"
        recommendation = "High CO2 hazard. Verify CDRA/METOX scrubbers; deploy supplemental CO2 absorption."
    else:
        risk_level = "CRITICAL"
        recommendation = "Critical hypercapnia toxicity threshold. Immediate flight surgeon alert and ECLSS intervention."

    return {
        "co2_mmhg": round(co2_mmhg, 2),
        "baseline_co2_mmhg": baseline_co2,
        "delta_co2_mmhg": round(delta_co2, 2),
        "odds_ratio": round(odds_ratio, 2),
        "headache_probability_pct": round(prob_headache * 100.0, 1),
        "risk_level": risk_level,
        "recommendation": recommendation,
        "citation": "Law J, Watkins S, Alexander D. J Occup Environ Med. 2014;56(5):477-483.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Global singleton state container
# ─────────────────────────────────────────────────────────────────────────────

class AppState:
    """
    Central application state singleton.
    Instantiated once at startup; imported everywhere.
    """

    def __init__(self) -> None:
        # ── Live telemetry state ───────────────────────────────────────────
        self.live: LiveState = LiveState()
        self.fusion: FusionState = FusionState()

        # ── Mission control objects ────────────────────────────────────────
        self.watchdog: NativeWatchdog = NativeWatchdog(timeout_sec=45.0)
        self.dtn: NativeDTNOutbox = NativeDTNOutbox()

        # ── Phase 2 Clinical & Hardware Engines ───────────────────────────
        self.sensor_adapter: HardwareSensorAdapter = HardwareSensorAdapter()
        self.alarm_manager: AlarmManager = AlarmManager()
        self.hash_chain: AuditHashChain = AuditHashChain()

        # ── Current vitals (user-adjustable via WS or REST) ───────────────
        self.heart_rate: float = 75.0
        self.temperature: float = 36.6
        self.spo2: float = 98.0
        self.manual_respiratory_rate: Optional[float] = None
        self.manual_rmssd: Optional[float] = None
        self.manual_sdnn: Optional[float] = None
        self.manual_baevsky_index: Optional[float] = None
        self.respiratory_rate: float = 14.0
        self.rmssd: float = 42.0
        self.sdnn: float = 55.0
        self.baevsky_index: float = 95.0

        # ── Cabin Environmental Metrics (ECLSS telemetry) ─────────────────
        self.cabin_co2: float = 3.0       # mmHg (nominal < 4.0, NASA threshold)
        self.cabin_o2: float = 20.9       # %
        self.cabin_pressure: float = 101.3  # kPa
        self.cabin_temp: float = 22.0     # °C
        self.cabin_noise: float = 58.0    # dBA

        # ── Fusion mode ───────────────────────────────────────────────────
        self.manual_override: bool = False
        self.manual_face_ratio: float = 0.60  # 60% face, 40% voice

        # ── Mission profile ───────────────────────────────────────────────
        self.mission_name: str = "ISRO Gaganyaan (LEO)"
        self.active_crew: str = "Cdr. A. Sharma (Pilot / CMO)"
        self.dossier_md: Optional[str] = None

        # ── Audio / microphone settings ───────────────────────────────────
        self.mic_gain: float = 1.0
        self.silence_threshold: float = 0.03

        # ── WebSocket connection registries ───────────────────────────────
        self.telemetry_connections: Set = set()
        self.telemetry_connections_lock: asyncio.Lock = asyncio.Lock()

        # ── Auto-log flag ─────────────────────────────────────────────────
        self.auto_log_enabled: bool = False

        # ── Voice / ASR ───────────────────────────────────────────────────
        self.vosk_ready: bool = False

        # ── ONNX face model readiness ─────────────────────────────────────
        self.face_model_ready: bool = False

        # ── Mission catalog (latency in seconds) ──────────────────────────
        self.mission_catalog: dict = {
            "ISRO Gaganyaan (LEO)":         0.5,
            "Artemis Gateway (Lunar)":      2.4,
            "Mars Transit (Deep Space)":    420.0,
        }
        self.crew_list: list = [
            "Cdr. A. Sharma (Pilot / CMO)",
            "Lt. Cdr. P. Nair (Flight Engineer)",
            "Dr. V. Rao (Mission Specialist)",
        ]

    def calculate_co2_headache_hazard(self, co2_mmhg: Optional[float] = None) -> Dict[str, Any]:
        """
        Calculate Dr. Law (2014) CO2-headache hazard model odds ratio and risk.
        Reference:
            Law J, Watkins S, Alexander D. Relationship Between Carbon Dioxide
            Levels and Reported Headaches on the International Space Station.
            J Occup Environ Med. 2014;56(5):477-483.
        """
        val = self.cabin_co2 if co2_mmhg is None else co2_mmhg
        return calculate_law2014_headache_odds(val)

    # ── Convenience helpers ────────────────────────────────────────────────────

    def get_project_root(self) -> Path:
        return _PROJECT_ROOT

    def get_db_path(self) -> str:
        """Return absolute path to the SQLite DB file."""
        return str(_PROJECT_ROOT / "maitri_logs.db")

    def sync_hash_chain(self, db_path: Optional[str] = None) -> None:
        """Sync in-memory AuditHashChain with latest hash & count from SQLite."""
        try:
            import sqlite3
            path = db_path or self.get_db_path()
            if os.path.exists(path):
                conn = sqlite3.connect(path)
                c = conn.cursor()
                c.execute("SELECT record_hash FROM stress_logs WHERE record_hash IS NOT NULL AND record_hash != '' ORDER BY id DESC LIMIT 1")
                row = c.fetchone()
                if row and row[0]:
                    self.hash_chain.current_hash = row[0]
                c.execute("SELECT COUNT(*) FROM stress_logs")
                cnt_row = c.fetchone()
                if cnt_row:
                    self.hash_chain.entry_count = cnt_row[0]
                conn.close()
        except Exception:
            pass


# Global singleton — imported by all backend modules
_app_state: Optional[AppState] = None


def get_state() -> AppState:
    """Return the global AppState singleton, creating it if needed."""
    global _app_state
    if _app_state is None:
        _app_state = AppState()
    return _app_state


def reset_state() -> AppState:
    """Reset to a fresh AppState (used in tests only)."""
    global _app_state
    _app_state = AppState()
    return _app_state
