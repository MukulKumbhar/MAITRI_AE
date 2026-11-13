"""
MAITRI 2.0 — M3: Vitals & Physiological Strain Module
Comprehensive Cardio-Respiratory and Autonomic Strain Engine.
Computes physiological strain from Heart Rate, Skin Temperature, SpO2,
Respiratory Rate, and Heart Rate Variability (rMSSD, SDNN, Baevsky Stress Index).

Clinical Standards & Citations:
- ESC/NASPE Task Force (1996): "Heart rate variability: standards of measurement,
  physiological interpretation and clinical use." Circulation 93.5 (1996): 1043-1065.
- Baevsky, R. M., et al. (1984, 2001): "Analysis of Heart Rate Variability in
  Space Medicine." Human Physiology / Aerosp. Environ. Med.
- NASA-STD-3001 Technical Standard Vol 1 & 2: Crew Health and Medical Operations.
"""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Sequence


# ─────────────────────────────────────────────────────────────────────────────
# Bilateral Clinical Threshold Bounds & Citations
# ─────────────────────────────────────────────────────────────────────────────

CARDIO_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "heart_rate": {
        "unit": "BPM",
        "low_critical": 45.0,     # Severe sinus bradycardia / heart block
        "low_warning": 55.0,      # Mild resting bradycardia (common in microgravity rest)
        "nominal_min": 60.0,      # Standard adult resting floor
        "nominal_max": 90.0,      # Standard resting ceiling
        "high_warning": 100.0,    # Sinus tachycardia
        "high_critical": 130.0,   # Severe exertion / supraventricular tachycardia
        "citation": "ESC/NASPE Task Force (1996); NASA-STD-3001 Vol 1/2",
    },
    "respiratory_rate": {
        "unit": "breaths/min",
        "low_critical": 8.0,      # Severe bradypnea / central depression
        "low_warning": 10.0,      # Mild hypoventilation
        "nominal_min": 12.0,      # Nominal eupnea floor
        "nominal_max": 20.0,      # Nominal eupnea ceiling
        "high_warning": 22.0,     # Tachypnea (e.g. CO2 retention or exertion)
        "high_critical": 28.0,    # Severe tachypnea / acute respiratory distress
        "citation": "NASA-STD-3001 Rev B; Guyton & Hall Textbook of Medical Physiology",
    },
    "rmssd": {
        "unit": "ms",
        "low_critical": 15.0,     # Severe vagal withdrawal / high sympathetic exhaustion
        "low_warning": 25.0,      # Moderate parasympathetic suppression
        "nominal_min": 25.0,      # Nominal resting floor
        "nominal_max": 80.0,      # Nominal resting ceiling
        "high_warning": 110.0,    # Marked vagal dominance / respiratory sinus arrhythmia
        "high_critical": 150.0,   # Potential sinus arrhythmia / conduction anomaly
        "citation": "ESC/NASPE Task Force (1996) Circulation 93:1043-1065",
    },
    "sdnn": {
        "unit": "ms",
        "low_critical": 25.0,     # Clinically compromised autonomic regulation
        "low_warning": 40.0,      # Moderate autonomic strain
        "nominal_min": 50.0,      # Normal resting floor
        "nominal_max": 100.0,     # Normal resting ceiling
        "high_warning": 130.0,    # High autonomic modulation
        "high_critical": 160.0,
        "citation": "ESC/NASPE Task Force (1996) Standards of HRV",
    },
    "baevsky_index": {
        "unit": "SI units",
        "low_critical": 20.0,     # Extreme parasympathetic dominance / hypo-reactivity
        "low_warning": 40.0,      # Mild vagotonia
        "nominal_min": 50.0,      # Normotonia / autonomic balance
        "nominal_max": 150.0,     # Autonomic equilibrium ceiling
        "high_warning": 250.0,    # Sympathetic predominance / moderate strain
        "high_critical": 450.0,   # Pronounced sympathetic exhaustion / severe strain
        "citation": "Baevsky et al. (1984, 2001) Space Medicine & Human Physiology",
    },
    "spo2": {
        "unit": "%",
        "low_critical": 88.0,     # Severe hypoxemia (emergency cabin O2 protocol)
        "low_warning": 93.0,      # Mild hypoxemia
        "nominal_min": 95.0,      # Target mission minimum
        "nominal_max": 100.0,     # Target mission maximum
        "high_warning": 100.0,
        "high_critical": 100.0,
        "citation": "NASA-STD-3001 Vol 2 Human Factors; WHO Pulse Oximetry Guide",
    },
    "temperature": {
        "unit": "°C",
        "low_critical": 35.0,     # Hypothermia
        "low_warning": 36.0,      # Mild core cooling
        "nominal_min": 36.5,      # Normal oral/tympanic floor
        "nominal_max": 37.5,      # Normal oral/tympanic ceiling
        "high_warning": 38.0,     # Pyrexia / low-grade fever
        "high_critical": 39.2,    # High fever / hyperthermia risk
        "citation": "NASA-STD-3001 Rev B; Space Flight Operations Medical Standard",
    },
}

CITATIONS: Dict[str, str] = {
    "hrv_standards": "ESC/NASPE Task Force (1996) Heart rate variability: standards of measurement, physiological interpretation and clinical use. Circulation 93.5: 1043-1065.",
    "baevsky_index": "Baevsky, R. M., et al. (1984, 2001) Analysis of Heart Rate Variability in Space Medicine. Human Physiology 27(6): 735-748.",
    "space_crew_health": "NASA-STD-3001 Technical Standard: NASA Spaceflight Human-System Standard, Volumes 1 & 2.",
}


@dataclass
class VitalsResult:
    # ── Original 8 attributes preserved in exact positional order ─────────────
    heart_rate:    float   # BPM
    temperature:   float   # °C
    spo2:          float   # % oxygen saturation
    hr_strain:     float   # 0–1
    temp_strain:   float   # 0–1
    spo2_strain:   float   # 0–1
    vitals_strain: float   # 0–1 (weighted composite)
    status:        str     # "Normal" / "Elevated" / "Critical"

    # ── Extended Cardio-Respiratory & HRV Metrics ─────────────────────────────
    respiratory_rate: float = 14.0  # breaths/min
    rmssd:            float = 42.0  # ms
    sdnn:             float = 55.0  # ms
    baevsky_index:    float = 95.0  # Baevsky Stress Index (SI)
    hrv_strain:       float = 0.0   # 0–1
    thresholds:       Dict[str, Any] = field(default_factory=lambda: CARDIO_THRESHOLDS)
    citations:        Dict[str, str] = field(default_factory=lambda: CITATIONS)


def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, val))


# ─────────────────────────────────────────────────────────────────────────────
# HRV & Autonomic Calculations (ESC/NASPE 1996 & Baevsky 1984, 2001)
# ─────────────────────────────────────────────────────────────────────────────

def calculate_hrv_metrics(rr_intervals_ms: Sequence[float]) -> Dict[str, float]:
    """
    Computes time-domain HRV metrics and Baevsky Stress Index from a sequence of
    consecutive RR (NN) intervals in milliseconds.

    Metrics:
    - mean_rr: Mean RR interval (ms)
    - sdnn: Standard Deviation of NN intervals (ms) [ESC/NASPE 1996]
    - rmssd: Root Mean Square of Successive Differences (ms) [ESC/NASPE 1996]
    - pnn50: Percentage of successive RR differences > 50 ms (%) [ESC/NASPE 1996]
    - mode_rr: Mode RR interval Mo (seconds) [Baevsky 1984]
    - amo: Amplitude of Mode AMo (%) [Baevsky 1984]
    - mx_dmn: Variation range MxDMn (seconds) [Baevsky 1984]
    - baevsky_index: Baevsky Stress Index SI = AMo / (2 * Mo * MxDMn)
    """
    cleaned = [float(rr) for rr in rr_intervals_ms if rr > 200.0 and rr < 2500.0]
    n = len(cleaned)

    if n < 2:
        return {
            "mean_rr": 800.0,
            "sdnn": 50.0,
            "rmssd": 40.0,
            "pnn50": 15.0,
            "mode_rr": 0.8,
            "amo": 35.0,
            "mx_dmn": 0.25,
            "baevsky_index": 87.5,
        }

    mean_rr = sum(cleaned) / n

    # 1. SDNN
    var = sum((rr - mean_rr) ** 2 for rr in cleaned) / (n - 1)
    sdnn = math.sqrt(max(0.0, var))

    # 2. rMSSD and pNN50
    diffs = [cleaned[i + 1] - cleaned[i] for i in range(n - 1)]
    sum_sq_diff = sum(d * d for d in diffs)
    rmssd = math.sqrt(sum_sq_diff / (n - 1)) if diffs else 0.0
    nn50_count = sum(1 for d in diffs if abs(d) > 50.0)
    pnn50 = (nn50_count / (n - 1) * 100.0) if diffs else 0.0

    # 3. Baevsky Stress Index (SI = AMo / (2 * Mo * MxDMn))
    # Intervals converted to seconds; bin width = 50 ms (0.05 s)
    rr_sec = [rr / 1000.0 for rr in cleaned]
    bin_width = 0.05  # 50 ms standard Baevsky bin width
    min_sec = min(rr_sec)
    max_sec = max(rr_sec)
    mx_dmn = max(0.02, max_sec - min_sec)  # clamp to avoid zero-range singularity

    # Form histogram bins
    bins: Dict[int, int] = {}
    for r in rr_sec:
        b_idx = int(math.floor(r / bin_width))
        bins[b_idx] = bins.get(b_idx, 0) + 1

    modal_bin = max(bins, key=bins.get)
    mode_rr = max(0.30, (modal_bin + 0.5) * bin_width)
    amo = (bins[modal_bin] / n) * 100.0  # percentage of intervals in modal bin

    baevsky_index = amo / (2.0 * mode_rr * mx_dmn)
    baevsky_index = max(10.0, min(2000.0, baevsky_index))

    return {
        "mean_rr": round(mean_rr, 2),
        "sdnn": round(sdnn, 2),
        "rmssd": round(rmssd, 2),
        "pnn50": round(pnn50, 2),
        "mode_rr": round(mode_rr, 3),
        "amo": round(amo, 2),
        "mx_dmn": round(mx_dmn, 3),
        "baevsky_index": round(baevsky_index, 1),
    }


def generate_synthetic_rr(
    heart_rate: float,
    count: int = 60,
    stress_factor: float = 0.0,
    respiratory_rate: float = 14.0,
) -> List[float]:
    """
    Generates a physiologically realistic sequence of RR intervals with
    Respiratory Sinus Arrhythmia (RSA, high-frequency) and Mayer-wave autonomic
    variability (low-frequency), modulated by heart rate and stress.
    """
    hr = max(35.0, min(200.0, heart_rate))
    mean_rr = 60000.0 / hr
    stress_k = _clamp(stress_factor, 0.0, 1.0)

    # Base modulation amplitude (ms): reduced under high sympathetic stress
    rsa_amp = (40.0 * (1.0 - 0.7 * stress_k)) * (mean_rr / 1000.0)
    mayer_amp = (25.0 * (1.0 - 0.5 * stress_k)) * (mean_rr / 1000.0)

    f_resp = max(0.15, min(0.45, respiratory_rate / 60.0))
    f_mayer = 0.10  # ~0.1 Hz sympathetic vasomotor oscillation

    rr_list: List[float] = []
    t = 0.0
    for i in range(count):
        # Time-domain modulation: RSA + Mayer vasomotor waves + autonomic variability
        mod = (
            rsa_amp * math.sin(2 * math.pi * f_resp * t)
            + mayer_amp * math.cos(2 * math.pi * f_mayer * t + 0.5)
            + (18.0 * (1.0 - 0.5 * stress_k)) * math.sin(i * 1.7)
            + (12.0 * (1.0 - 0.5 * stress_k)) * math.cos(i * 2.3)
        )
        rr = mean_rr + mod
        rr = max(300.0, min(1800.0, rr))
        rr_list.append(round(rr, 1))
        t += rr / 1000.0

    return rr_list


def calculate_respiratory_rate(
    rr_intervals_ms: Optional[Sequence[float]] = None,
    heart_rate: float = 75.0,
    base_rr: Optional[float] = None,
) -> float:
    """
    Determine respiratory rate in breaths/minute.
    - If base_rr is supplied (e.g. from manual slider or sensor), clamps and returns it.
    - If RR intervals are provided, estimates RSA modulation frequency.
    - Otherwise, derives resting physiological respiratory rate from cardio-respiratory coupling.
    """
    if base_rr is not None and base_rr > 0:
        return round(_clamp(base_rr, 6.0, 40.0), 1)

    if rr_intervals_ms and len(rr_intervals_ms) >= 15:
        # Detect zero-crossings / peak intervals of RR oscillations for RSA
        mean_v = sum(rr_intervals_ms) / len(rr_intervals_ms)
        diffs = [rr - mean_v for rr in rr_intervals_ms]
        crossings = 0
        for i in range(len(diffs) - 1):
            if (diffs[i] <= 0 and diffs[i + 1] > 0) or (diffs[i] >= 0 and diffs[i + 1] < 0):
                crossings += 1
        total_time_sec = sum(rr_intervals_ms) / 1000.0
        if total_time_sec > 2.0 and crossings >= 2:
            cycles = crossings / 2.0
            freq_hz = cycles / total_time_sec
            resp_bpm = freq_hz * 60.0
            if 8.0 <= resp_bpm <= 35.0:
                return round(resp_bpm, 1)

    # Guyton physiological resting coupling estimation
    coupled = 12.0 + 0.12 * max(0.0, heart_rate - 65.0)
    return round(_clamp(coupled, 10.0, 32.0), 1)


def compute_hrv_strain(rmssd: float, baevsky_index: float) -> float:
    """
    Computes normalised autonomic strain [0–1] from rMSSD and Baevsky Stress Index.
    - rMSSD >= 25 ms is nominal resting floor (strain = 0.0); < 25 ms indicates
      vagal withdrawal / parasympathetic depression (strain -> 1.0 at <= 15 ms).
    - Baevsky SI <= 150 is nominal resting balance (strain = 0.0); > 150 indicates
      sympathetic hyperactivity / operational exhaustion (strain -> 1.0 at >= 450).
    """
    if rmssd < 25.0:
        rmssd_strain = _clamp((25.0 - rmssd) / 10.0)
    else:
        rmssd_strain = 0.0

    if baevsky_index > 150.0:
        baevsky_strain = _clamp((baevsky_index - 150.0) / 300.0)
    else:
        baevsky_strain = 0.0

    return _clamp(0.50 * rmssd_strain + 0.50 * baevsky_strain)


# ─────────────────────────────────────────────────────────────────────────────
# Composite Cardio-Respiratory & Vitals Strain
# ─────────────────────────────────────────────────────────────────────────────

def compute_vitals_strain(
    heart_rate: float,
    temperature: float,
    spo2: float,
    respiratory_rate: Optional[float] = None,
    rr_intervals: Optional[Sequence[float]] = None,
    rmssd: Optional[float] = None,
    sdnn: Optional[float] = None,
    baevsky_index: Optional[float] = None,
) -> VitalsResult:
    """
    Compute composite physiological and autonomic cardio-respiratory strain.

    HR normalisation:
        ≤70 BPM → 0  (resting)
        130 BPM → 1  (high exertion / stress)

    Temperature normalisation:
        ≤37.0 °C → 0  (normal core)
        39.0 °C  → 1  (fever / hyperthermia)

    SpO2 normalisation:
        ≥98% → 0   (optimal)
        85%  → 1   (hypoxic — mission-critical concern)

    Composite weights:
    - Base: HR 50%, Temp 30%, SpO2 20% (guarantees 100% backward compatibility)
    - If advanced HRV metrics are provided or calculated, hrv_strain is integrated.
    """
    hr_strain   = _clamp((heart_rate - 70.0) / 60.0)
    temp_strain = _clamp((temperature - 37.0) / 2.0)
    spo2_strain = _clamp((98.0 - spo2) / 13.0)

    # Derive or compute HRV metrics
    if rr_intervals is not None and len(rr_intervals) >= 2:
        hrv_dict = calculate_hrv_metrics(rr_intervals)
        calc_rmssd = hrv_dict["rmssd"]
        calc_sdnn = hrv_dict["sdnn"]
        calc_baevsky = hrv_dict["baevsky_index"]
    else:
        # Synthetic / estimate consistent with heart rate & strain
        effective_stress = 0.5 * hr_strain + 0.3 * temp_strain + 0.2 * spo2_strain
        synth_rr = generate_synthetic_rr(heart_rate, count=30, stress_factor=effective_stress)
        hrv_dict = calculate_hrv_metrics(synth_rr)
        calc_rmssd = rmssd if rmssd is not None else hrv_dict["rmssd"]
        calc_sdnn = sdnn if sdnn is not None else hrv_dict["sdnn"]
        calc_baevsky = baevsky_index if baevsky_index is not None else hrv_dict["baevsky_index"]

    calc_resp = calculate_respiratory_rate(
        rr_intervals_ms=rr_intervals,
        heart_rate=heart_rate,
        base_rr=respiratory_rate,
    )
    hrv_strain = compute_hrv_strain(calc_rmssd, calc_baevsky)

    # Baseline composite strain (exact formula expected by legacy tests)
    base_vitals_strain = (
        0.50 * hr_strain
        + 0.30 * temp_strain
        + 0.20 * spo2_strain
    )
    base_vitals_strain = _clamp(base_vitals_strain)

    if rr_intervals is not None or rmssd is not None or baevsky_index is not None:
        vitals_strain = _clamp(0.75 * base_vitals_strain + 0.25 * hrv_strain)
    else:
        vitals_strain = base_vitals_strain

    # Status label (used in dashboard badge)
    if vitals_strain >= 0.70:
        status = "Critical"
    elif vitals_strain >= 0.40:
        status = "Elevated"
    else:
        status = "Normal"

    return VitalsResult(
        heart_rate=heart_rate,
        temperature=temperature,
        spo2=spo2,
        hr_strain=hr_strain,
        temp_strain=temp_strain,
        spo2_strain=spo2_strain,
        vitals_strain=round(vitals_strain, 4),
        status=status,
        respiratory_rate=calc_resp,
        rmssd=calc_rmssd,
        sdnn=calc_sdnn,
        baevsky_index=calc_baevsky,
        hrv_strain=round(hrv_strain, 4),
        thresholds=CARDIO_THRESHOLDS,
        citations=CITATIONS,
    )
