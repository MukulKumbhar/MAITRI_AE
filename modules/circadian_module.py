"""
MAITRI 2.0 — Sleep & Circadian Rhythm Tracker Module
Offline Aerospace Circadian Rhythm, Sleep Debt, Melatonin Suppression,
and ISS Orbital Daylight Cycle Engine.

References:
- Van Dongen HPA, Maislin G, Mullington JM, Dinges DF. The Cumulative Cost of
  Additional Wakefulness: Dose-response effects on neurobehavioral functions and
  sleep physiology via chronic sleep restriction and total sleep deprivation.
  Sleep. 2003;26(2):117-126.
- Halberg F. Chronobiology. Annu Rev Physiol. 1969;31:675-725.
- Rea MS, Figueiro MG, Bullough JD, Bierman A. A model of phototransduction by the
  human circadian system. Brain Res Rev. 2005;50(2):213-228.
- NASA-STD-3001, Vol 1 & 2: Space Flight Human-System Standard (Crew Sleep & Lighting).
"""

from __future__ import annotations

import datetime
import math
import time
from typing import Any, Dict, List, Optional, Tuple


# ── Orbital Constants for ISS (LEO) ──────────────────────────────────────────
ISS_ORBIT_PERIOD_SECONDS: float = 92.68 * 60.0    # 5560.8 seconds (~92.7 minutes)
ISS_DAYLIGHT_FRACTION: float = 0.615              # ~57 minutes daylight
ISS_DAYLIGHT_SECONDS: float = ISS_ORBIT_PERIOD_SECONDS * ISS_DAYLIGHT_FRACTION  # ~3420s
ISS_NIGHT_SECONDS: float = ISS_ORBIT_PERIOD_SECONDS - ISS_DAYLIGHT_SECONDS      # ~2140s

# Arbitrary fixed reference epoch for deterministic orbital phasing (2026-01-01 00:00:00 UTC)
ISS_EPOCH_REFERENCE: float = 1767225600.0


# ── 1. Cumulative Sleep Debt Calculator ────────────────────────────────────────

def calculate_sleep_debt(
    actual_sleep_hours: float,
    target_sleep_hours: float = 8.0,
    prior_cumulative_debt_hours: float = 0.0,
    recovery_efficiency: float = 0.85,
) -> Dict[str, Any]:
    """
    Computes acute and cumulative sleep debt with decay/recovery modeling.

    Based on Van Dongen et al. (2003):
    Sleep debt accumulates linearly with restriction (<7h/night), while neurobehavioral
    impairment builds cumulatively and requires multi-day recovery.

    Args:
        actual_sleep_hours: Sleep duration recorded for the current 24h cycle.
        target_sleep_hours: Prescribed baseline sleep goal (default 8.0h).
        prior_cumulative_debt_hours: Carried-over debt from prior days.
        recovery_efficiency: Rate at which excess sleep pays down existing debt (0.85).

    Returns:
        Dict with acute deficit, updated cumulative debt, fatigue risk score,
        and clinical countermeasure guidance.
    """
    daily_delta = target_sleep_hours - actual_sleep_hours

    if daily_delta > 0:
        # Additional debt accrued
        new_cumulative_debt = prior_cumulative_debt_hours + daily_delta
    else:
        # Excess sleep: pays down existing debt with physiological recovery efficiency
        recovery_hours = abs(daily_delta) * recovery_efficiency
        new_cumulative_debt = max(0.0, prior_cumulative_debt_hours - recovery_hours)

    # Chronic fatigue risk index (0 to 100):
    # 0h debt -> 0, 5h debt -> 25, 10h debt -> 55, 16h debt -> 90+
    # Logistic scaling of neurobehavioral deficit
    fatigue_index = min(100.0, (1.0 / (1.0 + math.exp(-0.35 * (new_cumulative_debt - 8.0)))) * 100.0)

    # Clinical status
    if new_cumulative_debt < 3.0:
        clinical_status = "NOMINAL"
        recommendation = "Circadian sleep reserve adequate for all mission flight duties."
    elif new_cumulative_debt < 7.0:
        clinical_status = "MILD_DEFICIT"
        recommendation = "Recommend 30-min sleep extension and pre-sleep relaxation protocol."
    elif new_cumulative_debt < 12.0:
        clinical_status = "MODERATE_DEBT"
        recommendation = "Cognitive degradation risk. Restrict non-critical EVA; schedule 90-min recovery nap."
    else:
        clinical_status = "CRITICAL_DEPRIVATION"
        recommendation = "Severe neurobehavioral impairment risk. CMO consultation and compulsory sleep countermeasure."

    return {
        "actual_sleep_hours": round(actual_sleep_hours, 2),
        "target_sleep_hours": round(target_sleep_hours, 2),
        "daily_delta_hours": round(daily_delta, 2),
        "cumulative_debt_hours": round(new_cumulative_debt, 2),
        "chronic_fatigue_risk_index": round(fatigue_index, 1),
        "clinical_status": clinical_status,
        "recommendation": recommendation,
        "recovery_sleep_needed_hours": round(max(0.0, new_cumulative_debt), 2),
        "source": "Van Dongen et al. 2003 / NASA-STD-3001",
    }


# ── 2. Cosinor Circadian Rhythm & Phase Angle Engine ──────────────────────────

def cosinor_model_predict(
    time_hours: float,
    mesor: float = 36.8,
    amplitude: float = 0.45,
    acrophase_rad: float = 2.88,  # Peak around 11:00 AM (2.88 rad ~ 11.0h)
    period_hours: float = 24.0,
) -> float:
    """
    Computes single-harmonic Cosinor model:
    Y(t) = Mesor + Amplitude * cos((2*pi*t / Period) - Acrophase)

    Standard chronobiological model (Halberg 1969, Nelson et al. 1979).
    """
    omega = 2.0 * math.pi / period_hours
    return mesor + amplitude * math.cos(omega * time_hours - acrophase_rad)


def calculate_circadian_phase(
    current_hour_decimal: float,
    habitual_wake_hour: float = 6.0,
    acrophase_hour: float = 14.0,
) -> Dict[str, Any]:
    """
    Computes circadian phase angle phi, alertness expectation, and phase shift.

    Args:
        current_hour_decimal: Current time of day [0.0 - 24.0).
        habitual_wake_hour: Scheduled wake time (default 06:00).
        acrophase_hour: Peak alertness / body temp acrophase (default 14:00).

    Returns:
        Circadian phase details including phase angle phi (radians and degrees),
        circadian alertness factor (0.0 to 1.0), and nadir estimate.
    """
    # Acrophase in radians [0, 2*pi)
    acrophase_rad = (acrophase_hour / 24.0) * 2.0 * math.pi

    # Current phase angle phi
    phase_rad = ((current_hour_decimal / 24.0) * 2.0 * math.pi) % (2.0 * math.pi)
    phase_angle_deg = math.degrees(phase_rad)

    # Circadian nadir (minimum alertness / core temperature minimum, typically 12h opposite to acrophase)
    nadir_hour = (acrophase_hour + 12.0) % 24.0

    # Normalized circadian alertness potential (0.0 to 1.0) using cosinor
    # Minimum at nadir (typically ~04:00), maximum at acrophase (~14:00)
    cos_val = math.cos(phase_rad - acrophase_rad)
    circadian_alertness = (cos_val + 1.0) / 2.0

    # Post-lunch dip phenomenon (secondary harmonic dip around 13:00 - 15:00 if awake since 06:00)
    hours_awake = (current_hour_decimal - habitual_wake_hour) % 24.0
    if 6.0 <= hours_awake <= 9.0:
        dip_attenuation = 0.12 * math.sin(math.pi * (hours_awake - 6.0) / 3.0)
        circadian_alertness = max(0.05, circadian_alertness - dip_attenuation)

    return {
        "current_hour": round(current_hour_decimal, 2),
        "phase_angle_rad": round(phase_rad, 4),
        "phase_angle_deg": round(phase_angle_deg, 1),
        "acrophase_hour": round(acrophase_hour, 1),
        "nadir_hour": round(nadir_hour, 1),
        "circadian_alertness": round(circadian_alertness, 3),
        "hours_awake": round(hours_awake, 1),
        "phase_state": "NADIR_ZONE" if abs(current_hour_decimal - nadir_hour) <= 2.0 else (
            "PEAK_ALERTNESS" if abs(current_hour_decimal - acrophase_hour) <= 2.5 else "TRANSITIONAL"
        ),
    }


# ── 3. Melatonin Suppression Model (Rea et al. 2005 / 2010) ───────────────────

def estimate_melatonin_suppression(
    light_lux: float,
    duration_minutes: float = 60.0,
    blue_spectrum_boost: float = 1.0,
) -> Dict[str, Any]:
    """
    Estimates acute nocturnal melatonin suppression caused by optical retinal exposure.

    Based on Rea et al. (2005, 2010) Circadian Stimulus (CS) phototransduction model:
    S = 100 * [1 - 1 / (1 + (lux * boost / K)^p)]
    where K ~ 120 lux (half-saturation for white LED), p ~ 1.15.

    Args:
        light_lux: Photopic illuminance at cornea (lux).
        duration_minutes: Duration of light exposure in minutes.
        blue_spectrum_boost: Multiplier for enriched 460-480nm blue light (1.0 = standard, 1.4 = blue-enriched).

    Returns:
        Dict with suppression percentage, sleep disruption hazard, and countermeasure.
    """
    effective_lux = max(0.0, light_lux * blue_spectrum_boost)

    if effective_lux <= 1.0:
        suppression_pct = 0.0
    else:
        k = 120.0
        p = 1.15
        base_suppression = 100.0 * (1.0 - (1.0 / (1.0 + (effective_lux / k) ** p)))
        # Duration scaling: reaches full suppression around 60 minutes
        dur_scale = min(1.0, duration_minutes / 60.0)
        suppression_pct = min(98.0, base_suppression * dur_scale)

    # Disruption risk
    if suppression_pct < 15.0:
        risk = "LOW"
        advice = "Lighting nominal for pre-sleep wind-down."
    elif suppression_pct < 45.0:
        risk = "MODERATE"
        advice = "Moderate melatonin suppression. Dim cockpit cabin lights to <30 lux or wear blue-blocker visor."
    else:
        risk = "HIGH"
        advice = "Severe melatonin suppression (>45%). Will delay sleep onset latency and fragment REM sleep."

    return {
        "light_lux": round(light_lux, 1),
        "effective_lux": round(effective_lux, 1),
        "duration_minutes": round(duration_minutes, 1),
        "melatonin_suppression_pct": round(suppression_pct, 1),
        "risk_level": risk,
        "clinical_advice": advice,
        "model_reference": "Rea et al. 2005 / Circadian Stimulus (CS)",
    }


# ── 4. ISS 90-Minute Daylight/Night Orbital Cycle Tracker ─────────────────────

def get_iss_orbital_cycle(current_time: Optional[float] = None) -> Dict[str, Any]:
    """
    Calculates real-time ISS 90-minute daylight/night orbital cycle status.

    ISS orbits Earth every ~92.7 minutes, producing ~15.5 day/night cycles per 24 hours.
    Astronauts experience ~57 minutes of daylight and ~35.7 minutes of eclipse every orbit.

    Args:
        current_time: POSIX timestamp (defaults to time.time()).

    Returns:
        Dict with phase ("DAYLIGHT" or "ORBITAL_NIGHT"), orbit progress,
        seconds to next sunrise/sunset, and circadian lighting guidance.
    """
    now = current_time or time.time()
    elapsed_since_ref = max(0.0, now - ISS_EPOCH_REFERENCE)

    orbit_index = int(elapsed_since_ref // ISS_ORBIT_PERIOD_SECONDS)
    seconds_in_orbit = elapsed_since_ref % ISS_ORBIT_PERIOD_SECONDS
    orbital_fraction = seconds_in_orbit / ISS_ORBIT_PERIOD_SECONDS

    if seconds_in_orbit < ISS_DAYLIGHT_SECONDS:
        current_phase = "DAYLIGHT"
        seconds_to_transition = ISS_DAYLIGHT_SECONDS - seconds_in_orbit
        next_event = "SUNSET"
    else:
        current_phase = "ORBITAL_NIGHT"
        seconds_to_transition = ISS_ORBIT_PERIOD_SECONDS - seconds_in_orbit
        next_event = "SUNRISE"

    # Glare / lighting pulse hazard warning: within 3 minutes (180s) of sunrise
    transition_imminent = (next_event == "SUNRISE" and seconds_to_transition <= 180.0)

    return {
        "orbit_period_minutes": round(ISS_ORBIT_PERIOD_SECONDS / 60.0, 2),
        "orbit_index": orbit_index,
        "current_phase": current_phase,
        "orbital_fraction": round(orbital_fraction, 4),
        "seconds_into_orbit": round(seconds_in_orbit, 1),
        "seconds_to_next_transition": round(seconds_to_transition, 1),
        "minutes_to_next_transition": round(seconds_to_transition / 60.0, 1),
        "next_event": next_event,
        "transition_imminent": transition_imminent,
        "sunrises_per_24h": round(86400.0 / ISS_ORBIT_PERIOD_SECONDS, 1),
        "circadian_guidance": (
            "Prepare window shutters for upcoming orbital sunrise to prevent circadian phase disruption."
            if transition_imminent
            else (
                "Orbital daylight: nominal cabin working spectrum."
                if current_phase == "DAYLIGHT"
                else "Orbital eclipse: maintain crew sleep schedule regardless of external darkness."
            )
        ),
    }
