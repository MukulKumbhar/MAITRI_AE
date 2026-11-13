"""
MAITRI 2.0 — Psychomotor Vigilance Test (PVT-B) Engine
Offline 3-Minute Reaction Self-Test Engine for Astronaut Vigilance Monitoring.

Based on:
Basner M, Dinges DF. Maximizing Sensitivity of the Psychomotor Vigilance Test (PVT)
to Sleep Loss. Sleep. 2011;34(5):581-591. doi:10.1093/sleep/34.5.581
NASA Human Research Program (HRP) Behavioral Health & Performance (BHP) Standards.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
import random
import statistics
import time
from typing import Any, Dict, List, Optional, Tuple


# ── Constants per Basner & Dinges (2011) ──────────────────────────────────────
PVTB_DURATION_SECONDS: float = 180.0       # Standard 3-minute brief PVT
PVTB_MIN_ISI_SECONDS: float = 2.0          # Minimum inter-stimulus interval (2s)
PVTB_MAX_ISI_SECONDS: float = 10.0         # Maximum inter-stimulus interval (10s)
PVTB_FALSE_START_THRESHOLD_MS: float = 100.0  # Anticipation threshold (<100ms)
PVTB_LAPSE_THRESHOLD_MS: float = 355.0     # PVT-B optimal lapse threshold (>=355ms)
PVTB_TIMEOUT_MS: float = 5000.0            # Max wait time for response before auto-timeout


@dataclass
class PVTResponse:
    """A single stimulus-response trial record."""
    trial_index: int
    isi_delay_s: float
    stimulus_time: float
    response_time: Optional[float] = None
    rt_ms: float = 0.0
    is_false_start: bool = False
    is_lapse: bool = False
    is_timeout: bool = False


@dataclass
class PVTMetrics:
    """Summary metrics of a completed or in-progress PVT-B test."""
    total_stimuli: int = 0
    valid_hits: int = 0
    lapses: int = 0
    false_starts: int = 0
    mean_rt_ms: float = 0.0
    median_rt_ms: float = 0.0
    fastest_10pct_rt_ms: float = 0.0
    slowest_10pct_rt_ms: float = 0.0
    mean_speed: float = 0.0           # Mean 1/RT (s^-1)
    fatigue_risk_score: float = 0.0   # 0 to 100
    performance_category: str = "OPTIMAL"
    duration_s: float = PVTB_DURATION_SECONDS
    all_rts: List[float] = field(default_factory=list)


def calculate_pvt_metrics(responses: List[PVTResponse], duration_s: float = PVTB_DURATION_SECONDS) -> PVTMetrics:
    """
    Computes standard Basner & Dinges (2011) PVT-B metrics from trial responses.
    """
    total_stimuli = len(responses)
    if total_stimuli == 0:
        return PVTMetrics(duration_s=duration_s)

    lapses = 0
    false_starts = 0
    valid_rts: List[float] = []
    speeds: List[float] = []

    for trial in responses:
        if trial.is_false_start or trial.rt_ms < PVTB_FALSE_START_THRESHOLD_MS:
            false_starts += 1
            continue

        valid_rts.append(trial.rt_ms)
        speeds.append(1000.0 / trial.rt_ms)  # 1/RT in s^-1

        if trial.is_lapse or trial.rt_ms >= PVTB_LAPSE_THRESHOLD_MS or trial.is_timeout:
            lapses += 1

    valid_hits = len([rt for rt in valid_rts if rt < PVTB_LAPSE_THRESHOLD_MS])

    mean_rt = statistics.mean(valid_rts) if valid_rts else 0.0
    median_rt = statistics.median(valid_rts) if valid_rts else 0.0
    mean_speed = statistics.mean(speeds) if speeds else 0.0

    # 10th percentile (fastest) and 90th percentile (slowest)
    if len(valid_rts) >= 2:
        sorted_rts = sorted(valid_rts)
        k_fast = max(1, int(len(sorted_rts) * 0.10))
        k_slow = max(1, int(len(sorted_rts) * 0.10))
        fastest_10pct = statistics.mean(sorted_rts[:k_fast])
        slowest_10pct = statistics.mean(sorted_rts[-k_slow:])
    elif valid_rts:
        fastest_10pct = valid_rts[0]
        slowest_10pct = valid_rts[0]
    else:
        fastest_10pct = 0.0
        slowest_10pct = 0.0

    # ── Fatigue Risk Score (FRS) [0-100] ──────────────────────────────────────
    # Lapse component (up to 50 pts): each lapse adds 10 pts
    lapse_component = min(50.0, lapses * 10.0)

    # Speed component (up to 35 pts): normal is >= 4.0 s^-1 (~250ms), impaired is <= 2.0 s^-1 (~500ms)
    if mean_speed >= 4.0 or not speeds:
        speed_component = 0.0
    elif mean_speed <= 2.0:
        speed_component = 35.0
    else:
        speed_component = 35.0 * ((4.0 - mean_speed) / 2.0)

    # False start component (up to 15 pts): each false start adds 5 pts
    fs_component = min(15.0, false_starts * 5.0)

    frs = min(100.0, max(0.0, lapse_component + speed_component + fs_component))

    # Performance Category
    if frs < 25.0:
        category = "OPTIMAL"
    elif frs < 50.0:
        category = "MILD_FATIGUE"
    elif frs < 75.0:
        category = "MODERATE_FATIGUE"
    else:
        category = "SEVERE_IMPAIRMENT"

    return PVTMetrics(
        total_stimuli=total_stimuli,
        valid_hits=valid_hits,
        lapses=lapses,
        false_starts=false_starts,
        mean_rt_ms=round(mean_rt, 1),
        median_rt_ms=round(median_rt, 1),
        fastest_10pct_rt_ms=round(fastest_10pct, 1),
        slowest_10pct_rt_ms=round(slowest_10pct, 1),
        mean_speed=round(mean_speed, 3),
        fatigue_risk_score=round(frs, 1),
        performance_category=category,
        duration_s=duration_s,
        all_rts=valid_rts,
    )


class PVTSession:
    """
    Manages a single active or completed PVT-B test session.
    """
    def __init__(self, crew_member: str = "Astronaut", duration_s: float = PVTB_DURATION_SECONDS) -> None:
        self.session_id: str = f"PVT_{int(time.time())}_{random.randint(1000, 9999)}"
        self.crew_member: str = crew_member
        self.duration_s: float = duration_s
        self.start_time: float = time.time()
        self.status: str = "READY"  # READY, AWAITING_STIMULUS, STIMULUS_ACTIVE, COMPLETED, ABORTED
        self.responses: List[PVTResponse] = []
        self.current_trial: Optional[PVTResponse] = None
        self.next_stimulus_due: float = 0.0
        self.active_stimulus_start: float = 0.0

    def start(self) -> Dict[str, Any]:
        """Start the PVT-B test session and schedule the first stimulus."""
        self.start_time = time.time()
        self.status = "AWAITING_STIMULUS"
        delay = random.uniform(PVTB_MIN_ISI_SECONDS, PVTB_MAX_ISI_SECONDS)
        self.next_stimulus_due = self.start_time + delay
        self.current_trial = PVTResponse(
            trial_index=len(self.responses) + 1,
            isi_delay_s=round(delay, 2),
            stimulus_time=self.next_stimulus_due,
        )
        return self.get_status()

    def check_timer(self, now: Optional[float] = None) -> Dict[str, Any]:
        """
        Polls the session timer to check if duration expired, stimulus should activate,
        or stimulus timed out.
        """
        current_time = now or time.time()

        if self.status in ("COMPLETED", "ABORTED"):
            return self.get_status()

        # Check total test duration (180s)
        if current_time - self.start_time >= self.duration_s:
            self.status = "COMPLETED"
            return self.get_status()

        if self.status == "AWAITING_STIMULUS":
            if current_time >= self.next_stimulus_due:
                self.status = "STIMULUS_ACTIVE"
                self.active_stimulus_start = current_time
                if self.current_trial:
                    self.current_trial.stimulus_time = current_time

        elif self.status == "STIMULUS_ACTIVE":
            # Check timeout (5000ms without response)
            elapsed_ms = (current_time - self.active_stimulus_start) * 1000.0
            if elapsed_ms >= PVTB_TIMEOUT_MS:
                if self.current_trial:
                    self.current_trial.rt_ms = PVTB_TIMEOUT_MS
                    self.current_trial.is_lapse = True
                    self.current_trial.is_timeout = True
                    self.current_trial.response_time = current_time
                    self.responses.append(self.current_trial)
                self._schedule_next_stimulus(current_time)

        return self.get_status()

    def record_press(self, now: Optional[float] = None) -> Dict[str, Any]:
        """
        Records an astronaut press / reaction event.
        - If stimulus is active, records valid RT or lapse.
        - If awaiting stimulus, records false start.
        """
        current_time = now or time.time()

        if self.status == "COMPLETED" or self.status == "ABORTED":
            return {"status": self.status, "message": "Test is not active"}

        if self.status == "AWAITING_STIMULUS":
            # Anticipation / False Start (<100ms or before stimulus onset)
            trial = self.current_trial or PVTResponse(
                trial_index=len(self.responses) + 1,
                isi_delay_s=0.0,
                stimulus_time=self.next_stimulus_due,
            )
            trial.is_false_start = True
            trial.rt_ms = 50.0  # nominal false-start penalty representation
            trial.response_time = current_time
            self.responses.append(trial)
            self._schedule_next_stimulus(current_time)
            return {
                "outcome": "FALSE_START",
                "message": "False start! Wait for the visual stimulus.",
                "rt_ms": 0.0,
                **self.get_status(),
            }

        elif self.status == "STIMULUS_ACTIVE":
            rt_ms = (current_time - self.active_stimulus_start) * 1000.0
            trial = self.current_trial or PVTResponse(
                trial_index=len(self.responses) + 1,
                isi_delay_s=0.0,
                stimulus_time=self.active_stimulus_start,
            )
            trial.response_time = current_time
            trial.rt_ms = round(rt_ms, 1)

            if rt_ms < PVTB_FALSE_START_THRESHOLD_MS:
                trial.is_false_start = True
                outcome = "FALSE_START"
            elif rt_ms >= PVTB_LAPSE_THRESHOLD_MS:
                trial.is_lapse = True
                outcome = "LAPSE"
            else:
                outcome = "VALID_HIT"

            self.responses.append(trial)
            self._schedule_next_stimulus(current_time)
            return {
                "outcome": outcome,
                "rt_ms": round(rt_ms, 1),
                **self.get_status(),
            }

        return self.get_status()

    def _schedule_next_stimulus(self, current_time: float) -> None:
        if current_time - self.start_time >= self.duration_s:
            self.status = "COMPLETED"
            self.current_trial = None
            return

        delay = random.uniform(PVTB_MIN_ISI_SECONDS, PVTB_MAX_ISI_SECONDS)
        self.status = "AWAITING_STIMULUS"
        self.next_stimulus_due = current_time + delay
        self.current_trial = PVTResponse(
            trial_index=len(self.responses) + 1,
            isi_delay_s=round(delay, 2),
            stimulus_time=self.next_stimulus_due,
        )

    def abort(self) -> Dict[str, Any]:
        """Abort the active session early."""
        self.status = "ABORTED"
        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        """Return full session status and computed metrics."""
        now = time.time()
        elapsed = min(self.duration_s, max(0.0, now - self.start_time))
        remaining = max(0.0, self.duration_s - elapsed)
        metrics = calculate_pvt_metrics(self.responses, duration_s=self.duration_s)

        return {
            "session_id": self.session_id,
            "crew_member": self.crew_member,
            "status": self.status,
            "elapsed_s": round(elapsed, 1),
            "remaining_s": round(remaining, 1),
            "trial_count": len(self.responses),
            "metrics": {
                "total_stimuli": metrics.total_stimuli,
                "valid_hits": metrics.valid_hits,
                "lapses": metrics.lapses,
                "false_starts": metrics.false_starts,
                "mean_rt_ms": metrics.mean_rt_ms,
                "median_rt_ms": metrics.median_rt_ms,
                "fastest_10pct_rt_ms": metrics.fastest_10pct_rt_ms,
                "slowest_10pct_rt_ms": metrics.slowest_10pct_rt_ms,
                "mean_speed": metrics.mean_speed,
                "fatigue_risk_score": metrics.fatigue_risk_score,
                "performance_category": metrics.performance_category,
            },
            "recent_rts": [r.rt_ms for r in self.responses[-10:]],
            "decision_support_notice": "DECISION SUPPORT ONLY — NOT AN AUTOMATED MEDICAL DEVICE.",
        }
