"""
MAITRI 2.0 — Clinical Screener Module
Offline Validated Clinical Psychometrics for Spaceflight Behavioral Health:
- PHQ-9 (Patient Health Questionnaire - 9) with Item 9 Safety Gate Trigger
- GAD-7 (Generalized Anxiety Disorder - 7)
- PSS-4 (Perceived Stress Scale - 4) with reverse scoring on Items 2 & 3
- Longitudinal Third-Quarter Effect Vulnerability Tracker

References:
- Kroenke K, Spitzer RL, Williams JB. The PHQ-9: validity of a brief depression severity measure.
  J Gen Intern Med. 2001;16(9):606-613.
- Spitzer RL, Kroenke K, Williams JB, Löwe B. A brief measure for assessing generalized
  anxiety disorder: the GAD-7. Arch Intern Med. 2006;166(10):1092-1097.
- Cohen S, Kamarck T, Mermelstein R. A global measure of perceived stress.
  J Health Soc Behav. 1983;24(4):385-396.
- Bechtel RB, Berning A. The third-quarter phenomenon: do people experience a decrease
  in morale and performance in the third quarter of an isolated mission?
  Environ Behav. 1991;23(4):460-478.
- Kanas N, Salnitskiy V, Grund EM, et al. Psychological characteristics of crew members
  and ground personnel during ISS missions. Aviat Space Environ Med. 2006;77(10):1083-1090.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
import json
from typing import Any, Dict, List, Optional, Tuple


# ── Questionnaires Text & Descriptions ────────────────────────────────────────

PHQ9_ITEMS = [
    "1. Little interest or pleasure in doing things",
    "2. Feeling down, depressed, or hopeless",
    "3. Trouble falling or staying asleep, or sleeping too much",
    "4. Feeling tired or having little energy",
    "5. Poor appetite or overeating",
    "6. Feeling bad about yourself — or that you are a failure",
    "7. Trouble concentrating on tasks, reading, or mission ops",
    "8. Moving or speaking slowly, or being unusually fidgety/restless",
    "9. Thoughts that you would be better off dead, or of hurting yourself in some way",
]

GAD7_ITEMS = [
    "1. Feeling nervous, anxious, or on edge",
    "2. Not being able to stop or control worrying",
    "3. Worrying too much about different things",
    "4. Trouble relaxing",
    "5. Being so restless that it is hard to sit still",
    "6. Becoming easily annoyed or irritable",
    "7. Feeling afraid as if something awful might happen",
]

PSS4_ITEMS = [
    "1. In the last month, how often have you felt unable to control the important things in your life?",
    "2. In the last month, how often have you felt confident about your ability to handle personal problems? [Reverse Scored]",
    "3. In the last month, how often have you felt that things were going your way? [Reverse Scored]",
    "4. In the last month, how often have you felt difficulties were piling up so high you could not overcome them?",
]


@dataclass
class ScreenerResult:
    """Standardized result of a scored screener."""
    screener_type: str                  # "PHQ-9", "GAD-7", "PSS-4"
    total_score: int
    max_possible_score: int
    severity: str
    clinical_interpretation: str
    item_responses: List[int]
    safety_alert: bool = False
    safety_message: Optional[str] = None
    action_recommendation: str = ""
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


# ── 1. PHQ-9 Scoring & Safety Gate Engine ─────────────────────────────────────

def score_phq9(responses: List[int]) -> ScreenerResult:
    """
    Score the 9 items of the PHQ-9 (each 0–3).
    Includes the critical Item 9 suicide/self-harm safety gate.

    Scoring:
      0-4: Minimal or none
      5-9: Mild depression
      10-14: Moderate depression
      15-19: Moderately severe depression
      20-27: Severe depression
    """
    if len(responses) != 9:
        raise ValueError(f"PHQ-9 requires exactly 9 responses, got {len(responses)}")

    clamped = [max(0, min(3, int(r))) for r in responses]
    total = sum(clamped)

    # Item 9 safety trigger check (index 8)
    item9_score = clamped[8]
    safety_alert = False
    safety_message = None

    if item9_score > 0:
        safety_alert = True
        safety_message = (
            f"SAFETY GATE TRIGGERED: Item 9 positive endorsement ({item9_score}/3). "
            "Self-harm or death ideation reported. Mandatory immediate notification to "
            "Crew Medical Officer (CMO) and Ground Behavioral Health / Flight Surgeon."
        )

    if total <= 4:
        severity = "MINIMAL"
        interpretation = "Minimal or no depressive symptomatology."
        action = "Nominal mission operations. Re-screen per standard flight schedule."
    elif total <= 9:
        severity = "MILD"
        interpretation = "Mild depressive symptoms."
        action = "Supportive counseling, sleep hygiene review, schedule pacing."
    elif total <= 14:
        severity = "MODERATE"
        interpretation = "Moderate depressive symptoms."
        action = "Structured CBT check-in, private ground consultation recommended."
    elif total <= 19:
        severity = "MODERATELY_SEVERE"
        interpretation = "Moderately severe depressive symptoms."
        action = "Immediate Flight Surgeon review. Consider pharmacotherapy / duty restriction."
    else:
        severity = "SEVERE"
        interpretation = "Severe depressive symptoms."
        action = "Urgent clinical intervention. Flight Surgeon emergency consult."

    if safety_alert:
        action = "IMMEDIATE EMERGENCY SAFETY PROTOCOL: " + action

    return ScreenerResult(
        screener_type="PHQ-9",
        total_score=total,
        max_possible_score=27,
        severity=severity,
        clinical_interpretation=interpretation,
        item_responses=clamped,
        safety_alert=safety_alert,
        safety_message=safety_message,
        action_recommendation=action,
    )


# ── 2. GAD-7 Anxiety Scoring Engine ───────────────────────────────────────────

def score_gad7(responses: List[int]) -> ScreenerResult:
    """
    Score the 7 items of the GAD-7 (each 0–3).

    Scoring:
      0-4: Minimal anxiety
      5-9: Mild anxiety
      10-14: Moderate anxiety
      15-21: Severe anxiety
    """
    if len(responses) != 7:
        raise ValueError(f"GAD-7 requires exactly 7 responses, got {len(responses)}")

    clamped = [max(0, min(3, int(r))) for r in responses]
    total = sum(clamped)

    if total <= 4:
        severity = "MINIMAL"
        interpretation = "Minimal anxiety symptoms."
        action = "Nominal baseline. Continue normal mission activities."
    elif total <= 9:
        severity = "MILD"
        interpretation = "Mild anxiety symptoms."
        action = "Recommend 4-7-8 grounding and autonomic down-regulation exercises."
    elif total <= 14:
        severity = "MODERATE"
        interpretation = "Moderate anxiety symptoms."
        action = "Evaluate operational stressors; schedule private psychological conference."
    else:
        severity = "SEVERE"
        interpretation = "Severe anxiety symptoms."
        action = "Flight Surgeon consultation; potential acute anxiolytic protocol."

    return ScreenerResult(
        screener_type="GAD-7",
        total_score=total,
        max_possible_score=21,
        severity=severity,
        clinical_interpretation=interpretation,
        item_responses=clamped,
        safety_alert=False,
        action_recommendation=action,
    )


# ── 3. PSS-4 Perceived Stress Scoring Engine ──────────────────────────────────

def score_pss4(responses: List[int]) -> ScreenerResult:
    """
    Score the 4 items of the PSS-4 (each 0–4).
    IMPORTANT: Items 2 and 3 (1-based) are REVERSE SCORED:
      Reversed Score = 4 - raw_score

    Scoring:
      0-5: Low stress
      6-10: Moderate stress
      11-16: High perceived stress
    """
    if len(responses) != 4:
        raise ValueError(f"PSS-4 requires exactly 4 responses, got {len(responses)}")

    clamped = [max(0, min(4, int(r))) for r in responses]

    # Item 1: raw
    # Item 2: reversed (4 - score)
    # Item 3: reversed (4 - score)
    # Item 4: raw
    scored_items = [
        clamped[0],
        4 - clamped[1],
        4 - clamped[2],
        clamped[3],
    ]
    total = sum(scored_items)

    if total <= 5:
        severity = "LOW_STRESS"
        interpretation = "Low perceived stress. Strong perceived coping resources."
        action = "Maintain current work-rest pacing."
    elif total <= 10:
        severity = "MODERATE_STRESS"
        interpretation = "Moderate perceived stress level."
        action = "Incorporate daily mindfulness / box breathing session and mission workload pacing."
    else:
        severity = "HIGH_STRESS"
        interpretation = "High perceived stress level. Potential coping exhaustion."
        action = "Crew debriefing, workload reduction, and behavioral countermeasure intervention."

    return ScreenerResult(
        screener_type="PSS-4",
        total_score=total,
        max_possible_score=16,
        severity=severity,
        clinical_interpretation=interpretation,
        item_responses=clamped,
        safety_alert=False,
        action_recommendation=action,
    )


# ── 4. Longitudinal "Third-Quarter Effect" Tracker ────────────────────────────

def calculate_third_quarter_effect(
    mission_elapsed_days: float,
    mission_total_days: float,
    historical_scores: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Calculates Third-Quarter Effect vulnerability for long-duration missions.

    Based on Bechtel & Berning (1991) and Kanas et al.:
    Regardless of mission duration (e.g. 180 days or 500 days), crew psychological
    cohesion, mood, and motivation frequently experience a characteristic dip during
    the 3rd quarter (50% to 75% timeline).

    Args:
        mission_elapsed_days: Mission elapsed time (MET) in days.
        mission_total_days: Planned mission duration in days.
        historical_scores: List of historical screener records with date and scores.

    Returns:
        Dict with mission progress fraction, quarter designation,
        vulnerability index (0-100), and proactive behavioral countermeasures.
    """
    if mission_total_days <= 0:
        mission_total_days = 180.0

    progress_frac = max(0.0, min(1.0, mission_elapsed_days / mission_total_days))

    if progress_frac < 0.25:
        quarter = 1
        quarter_name = "Q1 — Launch & Initial Adaptation"
        is_third_quarter = False
    elif progress_frac < 0.50:
        quarter = 2
        quarter_name = "Q2 — Established Routine & Nominal Ops"
        is_third_quarter = False
    elif progress_frac < 0.75:
        quarter = 3
        quarter_name = "Q3 — High Confinement & Monotony (Third-Quarter Zone)"
        is_third_quarter = True
    else:
        quarter = 4
        quarter_name = "Q4 — Terminal Phase & Return Anticipation"
        is_third_quarter = False

    # Base vulnerability score depending on mission phase
    if is_third_quarter:
        # Distance from midpoint of Q3 (0.625)
        dist_from_peak = abs(progress_frac - 0.625) / 0.125
        base_vulnerability = 70.0 * (1.0 - 0.5 * dist_from_peak)
    elif quarter == 2:
        base_vulnerability = 25.0
    elif quarter == 4:
        base_vulnerability = 30.0
    else:
        base_vulnerability = 20.0

    # Trend adjustment from longitudinal screener history if provided
    trend_delta = 0.0
    if historical_scores and len(historical_scores) >= 2:
        # Sort by date/timestamp
        recent = historical_scores[-3:]
        prior = historical_scores[:-3] if len(historical_scores) > 3 else historical_scores[:1]

        avg_recent = sum(r.get("total_score", 0) for r in recent) / len(recent)
        avg_prior = sum(r.get("total_score", 0) for r in prior) / len(prior)
        if avg_prior > 0:
            pct_change = (avg_recent - avg_prior) / avg_prior
            trend_delta = max(-20.0, min(30.0, pct_change * 40.0))

    final_vulnerability = max(0.0, min(100.0, base_vulnerability + trend_delta))

    if final_vulnerability < 35.0:
        risk_level = "LOW"
        guidance = "Nominal morale and psychological resilience. Continue current schedule."
    elif final_vulnerability < 65.0:
        risk_level = "ELEVATED"
        guidance = (
            "Third-Quarter vulnerability elevated. Proactively introduce sensory variety, "
            "private videoconference uplinks with family, and schedule decompression."
        )
    else:
        risk_level = "HIGH"
        guidance = (
            "Significant Third-Quarter psychological dip detected. Behavioral health countermeasure: "
            "reduce non-critical operational demands, organize crew shared celebration, and review mood."
        )

    return {
        "mission_elapsed_days": round(mission_elapsed_days, 1),
        "mission_total_days": round(mission_total_days, 1),
        "progress_percent": round(progress_frac * 100.0, 1),
        "quarter": quarter,
        "quarter_name": quarter_name,
        "is_third_quarter": is_third_quarter,
        "vulnerability_index": round(final_vulnerability, 1),
        "risk_level": risk_level,
        "countermeasure_guidance": guidance,
        "scientific_basis": "Bechtel & Berning 1991 / Kanas et al. 2006",
    }
