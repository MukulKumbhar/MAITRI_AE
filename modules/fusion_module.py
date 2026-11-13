"""
MAITRI 2.0 — M4: Multimodal Fusion Module
Quality-aware weighted fusion of face emotion + voice emotion + vitals strain + eye fatigue.
Uses EMA temporal smoothing with adaptive reactivity to prevent flickering.

Phase 2 Extensions:
- Personal Baseline Calibration (Z-Score & CUSUM drift detection) to mitigate
  cephalic fluid shift ("puffy-face" syndrome) bias in microgravity.
- Explainable fusion breakdown with percentage weights and clinical rationales.

Modality Structure:
- Behavioral Channels: Face (visual) + Voice (audio)
  Initial nominal baseline ratio: 60% Face / 40% Voice.
- Physiological Channel: Vitals Strain (cardiac, thermal, SpO₂, HRV, respiration)
- Ocular Channel: Eye Fatigue & Blink Strain (MediaPipe EAR)

Dynamic Quality-Aware & Silence VAD Gating:
- When astronaut is silent (VAD=0, is_speaking=False), voice weight is strictly 0.0,
  preventing background cabin/microphone noise from interfering with telemetry.
- Face carries 100% of the behavioral signal during silence.
- When speech is detected, weights dynamically balance according to relative signal quality
  or respect manual slider overrides.
"""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple

# 7 standard emotion classes (FER / DeepFace convention)
EMOTIONS = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]

# Base modality weights (sum to 1.0)
# Behavioral share = 0.60 (Face=0.36, Voice=0.24 -> 60/40 ratio)
# Physiological share = 0.25
# Ocular share = 0.15
_BASE_BEHAVIORAL_W = 0.60
_BASE_FACE_RATIO   = 0.60   # 60% Face of behavioral share
_BASE_VOICE_RATIO  = 0.40   # 40% Voice of behavioral share

_BASE_FACE_W    = _BASE_BEHAVIORAL_W * _BASE_FACE_RATIO   # 0.36
_BASE_VOICE_W   = _BASE_BEHAVIORAL_W * _BASE_VOICE_RATIO  # 0.24
_BASE_VITALS_W  = 0.25
_BASE_EYE_W     = 0.15

# EMA alpha for temporal smoothing of fused probabilities
_EMA_ALPHA_SLOW = 0.15   # smooth, anti-flicker during steady state
_EMA_ALPHA_FAST = 0.40   # reactive, responds quickly to sudden stress spikes (>20% delta)
_EMA_SPIKE_THRESHOLD = 0.20

# EMA alpha for quality gate weight adjustment
_GATE_ALPHA = 0.12

# Weight bounds per modality
_W_MIN = 0.00
_W_MAX = 0.90


def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, val))


def _normalise(probs: Dict[str, float]) -> Dict[str, float]:
    """Ensure probabilities sum to 1; handle zero-sum edge case."""
    total = sum(probs.values())
    if total <= 0:
        return {e: 1.0 / len(EMOTIONS) for e in EMOTIONS}
    return {e: probs.get(e, 0.0) / total for e in EMOTIONS}


def _neutral_probs() -> Dict[str, float]:
    return {
        "angry": 0.0, "disgust": 0.0, "fear": 0.0,
        "happy": 0.0, "neutral": 1.0, "sad": 0.0, "surprise": 0.0
    }


def _uniform() -> Dict[str, float]:
    return {e: 1.0 / len(EMOTIONS) for e in EMOTIONS}


# ─────────────────────────────────────────────────────────────────────────────
# Personal Baseline Calibration & Cephalic Fluid Shift Mitigation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PersonalBaseline:
    """
    Crew personal baseline calibration model.
    Mitigates cephalic fluid shift ("puffy-face") bias where cephalic venous engorgement
    and periorbital edema alter resting facial geometry in microgravity.
    Calculates personal Z-scores and Page's CUSUM control charts to detect authentic
    drift from individual resting baselines.
    """
    crew_id: str = "cdr_sharma"
    sample_count: int = 0
    calibration_target: int = 30
    is_calibrated: bool = False

    # Baseline means (mu)
    mu_negative_affect: float = 0.05
    mu_ear: float = 0.28
    mu_vitals_strain: float = 0.10
    mu_face_strain: float = 0.05

    # Baseline standard deviations (sigma)
    sigma_negative_affect: float = 0.04
    sigma_ear: float = 0.03
    sigma_vitals_strain: float = 0.08
    sigma_face_strain: float = 0.05

    # Baseline emotion probability offsets (cephalic fluid shift offsets)
    baseline_emotion_offsets: Dict[str, float] = field(default_factory=lambda: {
        "angry": 0.0, "disgust": 0.0, "fear": 0.0,
        "happy": 0.0, "neutral": 0.0, "sad": 0.0, "surprise": 0.0
    })

    # CUSUM parameters (Page's Cumulative Sum control chart)
    cusum_k: float = 0.5   # 0.5 sigma allowance slack
    cusum_h: float = 4.0   # 4.0 sigma decision boundary threshold

    # CUSUM accumulators
    cusum_sh: Dict[str, float] = field(default_factory=lambda: {
        "negative_affect": 0.0,
        "vitals_strain": 0.0,
        "face_strain": 0.0,
    })
    cusum_sl: Dict[str, float] = field(default_factory=lambda: {
        "negative_affect": 0.0,
        "vitals_strain": 0.0,
        "face_strain": 0.0,
    })
    cusum_drift: Dict[str, bool] = field(default_factory=lambda: {
        "negative_affect": False,
        "vitals_strain": False,
        "face_strain": False,
    })

    def calibrate_step(
        self,
        face_probs: Optional[Dict[str, float]],
        vitals_strain: float,
        ear: float = 0.28,
        fatigue_strain: float = 0.0,
    ) -> None:
        """Accumulate resting calibration sample using Welford's algorithm."""
        self.sample_count += 1
        n = float(self.sample_count)

        neg = 0.0
        if face_probs:
            neg = (
                face_probs.get("fear", 0.0) * 1.2
                + face_probs.get("angry", 0.0) * 1.1
                + face_probs.get("sad", 0.0) * 1.0
                + face_probs.get("disgust", 0.0) * 0.7
            )
            for e in EMOTIONS:
                val = face_probs.get(e, 0.0)
                old_m = self.baseline_emotion_offsets.get(e, 0.0)
                self.baseline_emotion_offsets[e] = old_m + (val - old_m) / n

        self.mu_negative_affect += (neg - self.mu_negative_affect) / n
        self.mu_vitals_strain += (vitals_strain - self.mu_vitals_strain) / n
        self.mu_ear += (ear - self.mu_ear) / n
        self.mu_face_strain += (fatigue_strain - self.mu_face_strain) / n

        if self.sample_count >= self.calibration_target:
            self.is_calibrated = True

    def compute_z_score(self, metric: str, value: float) -> float:
        """Compute standard normal deviation Z = (x - mu) / sigma."""
        mu_map = {
            "negative_affect": self.mu_negative_affect,
            "vitals_strain": self.mu_vitals_strain,
            "ear": self.mu_ear,
            "face_strain": self.mu_face_strain,
        }
        sig_map = {
            "negative_affect": max(0.01, self.sigma_negative_affect),
            "vitals_strain": max(0.01, self.sigma_vitals_strain),
            "ear": max(0.01, self.sigma_ear),
            "face_strain": max(0.01, self.sigma_face_strain),
        }
        mu = mu_map.get(metric, 0.0)
        sigma = sig_map.get(metric, 1.0)
        return round((value - mu) / sigma, 3)

    def update_cusum(self, metric: str, value: float) -> Tuple[float, float, bool]:
        """
        Two-sided tabular CUSUM step:
        Sh[t] = max(0, Sh[t-1] + z - k)
        Sl[t] = max(0, Sl[t-1] - z - k)
        Flags drift when Sh > h or Sl > h.
        """
        z = self.compute_z_score(metric, value)
        k = self.cusum_k
        h = self.cusum_h

        sh_prev = self.cusum_sh.get(metric, 0.0)
        sl_prev = self.cusum_sl.get(metric, 0.0)

        sh_new = max(0.0, sh_prev + z - k)
        sl_new = max(0.0, sl_prev - z - k)

        self.cusum_sh[metric] = round(sh_new, 3)
        self.cusum_sl[metric] = round(sl_new, 3)

        drift = (sh_new >= h) or (sl_new >= h)
        self.cusum_drift[metric] = drift
        return sh_new, sl_new, drift

    def adjust_for_cephalic_fluid_shift(
        self,
        face_probs: Optional[Dict[str, float]],
    ) -> Dict[str, float]:
        """
        Mitigates cephalic fluid shift ("puffy-face") bias by subtracting
        the calibrated resting facial affect offsets.
        """
        if not face_probs:
            return _neutral_probs()
        if not self.is_calibrated:
            return _normalise(face_probs)

        adjusted: Dict[str, float] = {}
        for e in EMOTIONS:
            raw = face_probs.get(e, 0.0)
            offset = self.baseline_emotion_offsets.get(e, 0.0)
            # Suppress static microgravity edema offset for distress emotions
            if e in ("disgust", "angry", "sad"):
                adjusted[e] = max(0.0, raw - 0.75 * offset)
            else:
                adjusted[e] = max(0.0, raw)

        return _normalise(adjusted)


@dataclass
class FusionState:
    """
    Persists EMA state across frames.
    Must be stored as a single object to survive updates cleanly.
    """
    ema_probs:      Dict[str, float] = field(default_factory=_neutral_probs)
    w_face:         float = _BASE_FACE_W
    w_voice:        float = 0.0     # Starts at 0 until speech is verified
    w_vitals:       float = _BASE_VITALS_W
    w_eye:          float = _BASE_EYE_W
    last_emotion:   str   = "neutral"
    last_stress:    float = 0.0
    initialized:    bool  = False
    baseline:       PersonalBaseline = field(default_factory=PersonalBaseline)


@dataclass
class FusionResult:
    fused_probs:       Dict[str, float]  # smoothed 7-class distribution
    dominant_emotion:  str
    face_weight:       float
    voice_weight:      float
    vitals_weight:     float
    eye_weight:        float
    stress_pct:        float
    is_speaking:       bool = False
    explainable_breakdown: Dict[str, Any] = field(default_factory=dict)


def _vitals_to_probs(vitals_strain: float) -> Dict[str, float]:
    """Map scalar vitals strain (0–1) to emotion pseudo-probabilities."""
    neutral_p = _clamp(1.0 - vitals_strain)
    stress_p  = _clamp(vitals_strain)
    return {
        "angry":    stress_p * 0.30,
        "disgust":  stress_p * 0.10,
        "fear":     stress_p * 0.30,
        "happy":    neutral_p * 0.40,
        "neutral":  neutral_p * 0.60,
        "sad":      stress_p * 0.30,
        "surprise": 0.0,
    }


def _eye_to_probs(fatigue_strain: float) -> Dict[str, float]:
    """Map eye fatigue strain (0–1) to emotion pseudo-probabilities."""
    neutral_p = _clamp(1.0 - fatigue_strain * 0.8)
    sad_p     = _clamp(fatigue_strain * 0.6)
    return {
        "angry":    0.0,
        "disgust":  0.0,
        "fear":     fatigue_strain * 0.10,
        "happy":    neutral_p * 0.20,
        "neutral":  neutral_p * 0.80,
        "sad":      sad_p,
        "surprise": 0.0,
    }


def fuse(
    state:          FusionState,
    face_probs:     Optional[Dict[str, float]],
    face_quality:   float,
    vitals_strain:  float,
    fatigue_strain: float,
    eye_quality:    float,
    voice_probs:    Optional[Dict[str, float]] = None,
    voice_quality:  float = 0.0,
    is_speaking:    bool = False,
    manual_override: bool = False,
    manual_face_ratio: float = 0.60,
    calibrate_baseline: bool = False,
) -> FusionResult:
    """
    Run one multimodal fusion step. Updates `state` in-place.

    Args:
        state:             Persisted EMA state object
        face_probs:        7-class face emotion distribution (or None)
        face_quality:      Face clarity & confidence score (0–1)
        vitals_strain:     Composite physiological strain (0–1)
        fatigue_strain:    Eye fatigue level (0–1)
        eye_quality:       Eye tracking availability (0 or 1)
        voice_probs:       7-class voice emotion distribution (or None)
        voice_quality:     Microphone signal quality (0–1)
        is_speaking:       True if speech activity detected, False if silence
        manual_override:   If True, use user slider weights rather than dynamic quality
        manual_face_ratio: Behavioral ratio allocated to Face (e.g. 0.60 = 60% Face, 40% Voice)
        calibrate_baseline:If True, contributes this frame to crew personal baseline
    """
    # Ensure baseline object is present on state
    if not hasattr(state, "baseline") or state.baseline is None:
        state.baseline = PersonalBaseline()

    if calibrate_baseline:
        state.baseline.calibrate_step(
            face_probs=face_probs,
            vitals_strain=vitals_strain,
            fatigue_strain=fatigue_strain,
        )

    # ── 1. Cephalic Fluid Shift Bias Mitigation ───────────────────────────
    compensated_face_probs = state.baseline.adjust_for_cephalic_fluid_shift(face_probs)

    # ── 2. Build per-modality probability vectors ─────────────────────────
    f_probs = _normalise(compensated_face_probs) if compensated_face_probs else _neutral_probs()
    v_probs = _normalise(_vitals_to_probs(vitals_strain))
    e_probs = _normalise(_eye_to_probs(fatigue_strain))
    vo_probs = _normalise(voice_probs) if (voice_probs and is_speaking) else _neutral_probs()

    # ── 3. Determine target weights ───────────────────────────────────────
    if manual_override:
        # User manual mode: slider specifies Face vs Voice ratio
        face_ratio = _clamp(manual_face_ratio, 0.0, 1.0)
        voice_ratio = 1.0 - face_ratio

        if not is_speaking:
            # Safety silence gating: if astronaut is silent, voice weight drops to 0
            target_w_face  = _BASE_BEHAVIORAL_W
            target_w_voice = 0.0
        else:
            target_w_face  = _BASE_BEHAVIORAL_W * face_ratio
            target_w_voice = _BASE_BEHAVIORAL_W * voice_ratio

        target_w_vitals = _BASE_VITALS_W
        target_w_eye    = _BASE_EYE_W * eye_quality
    else:
        # Automatic Dynamic Quality-Aware Mode
        q_f = _BASE_FACE_RATIO * face_quality
        q_v = _BASE_VOICE_RATIO * voice_quality if is_speaking else 0.0
        norm_q = q_f + q_v

        if norm_q > 0:
            target_w_face  = _BASE_BEHAVIORAL_W * (q_f / norm_q)
            target_w_voice = _BASE_BEHAVIORAL_W * (q_v / norm_q)
        else:
            # Both face and voice absent/silent: no behavioral signal
            target_w_face  = 0.0
            target_w_voice = 0.0

        target_w_eye = _BASE_EYE_W * eye_quality
        target_w_vitals = _BASE_VITALS_W

    # ── 4. Smooth weights via EMA ─────────────────────────────────────────
    gate_alpha_voice = 0.35 if not is_speaking else _GATE_ALPHA

    state.w_face   = (1 - _GATE_ALPHA) * state.w_face   + _GATE_ALPHA * target_w_face
    state.w_voice  = (1 - gate_alpha_voice) * state.w_voice  + gate_alpha_voice * target_w_voice
    state.w_eye    = (1 - _GATE_ALPHA) * state.w_eye    + _GATE_ALPHA * target_w_eye
    state.w_vitals = (1 - _GATE_ALPHA) * state.w_vitals + _GATE_ALPHA * target_w_vitals

    # Renormalise so weights sum to exactly 1.0
    total_w = state.w_face + state.w_voice + state.w_vitals + state.w_eye
    if total_w <= 0:
        w_f, w_vo, w_v, w_e = _BASE_FACE_W, 0.0, _BASE_VITALS_W, _BASE_EYE_W
    else:
        w_f  = state.w_face   / total_w
        w_vo = state.w_voice  / total_w
        w_v  = state.w_vitals / total_w
        w_e  = state.w_eye    / total_w

    # ── 5. Weighted probability fusion ────────────────────────────────────
    raw_probs = {
        e: (w_f * f_probs[e] + w_vo * vo_probs[e] + w_v * v_probs[e] + w_e * e_probs[e])
        for e in EMOTIONS
    }

    # ── 6. Adaptive EMA temporal smoothing (anti-flicker) ─────────────────
    prev_stress_norm = state.last_stress / 100.0
    _raw_neg = _clamp(
        raw_probs.get("fear", 0.0) * 1.2
        + raw_probs.get("angry", 0.0) * 1.1
        + raw_probs.get("sad", 0.0) * 1.0
        + raw_probs.get("disgust", 0.0) * 0.7
    )
    _raw_stress_est = _clamp(
        w_f * _raw_neg + w_vo * _raw_neg + w_v * vitals_strain + w_e * fatigue_strain
    )
    stress_delta = abs(_raw_stress_est - prev_stress_norm)
    ema_alpha = _EMA_ALPHA_FAST if stress_delta >= _EMA_SPIKE_THRESHOLD else _EMA_ALPHA_SLOW

    if not state.initialized:
        state.ema_probs = _normalise(raw_probs)
        state.initialized = True
    else:
        smoothed = {
            e: (1 - ema_alpha) * state.ema_probs[e] + ema_alpha * raw_probs[e]
            for e in EMOTIONS
        }
        state.ema_probs = _normalise(smoothed)

    # ── 7. Composite stress calculation ───────────────────────────────────
    neg_score = _clamp(
        state.ema_probs.get("fear", 0.0) * 1.2
        + state.ema_probs.get("angry", 0.0) * 1.1
        + state.ema_probs.get("sad", 0.0) * 1.0
        + state.ema_probs.get("disgust", 0.0) * 0.7
    )

    composite_stress = (
        (w_f + w_vo) * neg_score
        + w_v * vitals_strain
        + w_e * fatigue_strain
    )

    stress_raw = max(
        composite_stress,
        0.80 * vitals_strain,
        0.75 * neg_score,
        0.70 * fatigue_strain if fatigue_strain >= 0.70 else 0.0,
    )
    stress_pct = round(_clamp(stress_raw) * 100, 2)

    dominant = max(state.ema_probs, key=state.ema_probs.get)
    state.last_emotion = dominant
    state.last_stress  = stress_pct

    # ── 8. CUSUM Drift & Explainable Clinical Breakdown ───────────────────
    state.baseline.update_cusum("negative_affect", neg_score)
    state.baseline.update_cusum("vitals_strain", vitals_strain)
    state.baseline.update_cusum("face_strain", fatigue_strain)

    rationales: List[str] = []
    # Behavioral rationale
    if w_f > 0.0:
        calib_str = "cephalic fluid shift baseline compensated" if state.baseline.is_calibrated else "uncalibrated"
        rationales.append(
            f"Face affect allocated {w_f*100:.1f}% weight (quality: {face_quality:.2f}; {calib_str})."
        )
    if is_speaking and w_vo > 0.0:
        rationales.append(
            f"Voice affect active at {w_vo*100:.1f}% weight (quality: {voice_quality:.2f}; acoustic speech confirmed)."
        )
    else:
        rationales.append(
            "Voice gated to 0.0% during silence to prevent cabin acoustic noise contamination."
        )

    # Physiological rationale
    rationales.append(
        f"Physiological channel allocated {w_v*100:.1f}% weight (vitals strain: {vitals_strain*100:.1f}%)."
    )

    # Ocular rationale
    if eye_quality > 0.0:
        rationales.append(
            f"Ocular channel allocated {w_e*100:.1f}% weight (fatigue strain: {fatigue_strain*100:.1f}%)."
        )

    # Drift rationale
    for metric, drift in state.baseline.cusum_drift.items():
        if drift:
            sh = state.baseline.cusum_sh.get(metric, 0.0)
            rationales.append(
                f"CUSUM alert: sustained upward drift in {metric} (Sh={sh:.2f} > h={state.baseline.cusum_h})."
            )

    explainable_breakdown = {
        "weights_pct": {
            "face": round(w_f * 100.0, 1),
            "voice": round(w_vo * 100.0, 1),
            "vitals": round(w_v * 100.0, 1),
            "eye": round(w_e * 100.0, 1),
        },
        "modality_contributions_pct": {
            "face": round(w_f * neg_score * 100.0, 1),
            "voice": round(w_vo * neg_score * 100.0, 1),
            "vitals": round(w_v * vitals_strain * 100.0, 1),
            "eye": round(w_e * fatigue_strain * 100.0, 1),
        },
        "baseline": {
            "is_calibrated": state.baseline.is_calibrated,
            "sample_count": state.baseline.sample_count,
            "cephalic_shift_compensated": state.baseline.is_calibrated,
            "z_scores": {
                "negative_affect": state.baseline.compute_z_score("negative_affect", neg_score),
                "vitals_strain": state.baseline.compute_z_score("vitals_strain", vitals_strain),
                "face_strain": state.baseline.compute_z_score("face_strain", fatigue_strain),
            },
            "cusum_drift": dict(state.baseline.cusum_drift),
            "cusum_sh": dict(state.baseline.cusum_sh),
        },
        "clinical_rationales": rationales,
    }

    return FusionResult(
        fused_probs=dict(state.ema_probs),
        dominant_emotion=dominant,
        face_weight=w_f,
        voice_weight=w_vo,
        vitals_weight=w_v,
        eye_weight=w_e,
        stress_pct=stress_pct,
        is_speaking=is_speaking,
        explainable_breakdown=explainable_breakdown,
    )
