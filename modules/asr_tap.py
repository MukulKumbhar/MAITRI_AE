"""
modules/asr_tap.py
Thread-safe ring buffer and autonomous VAD speech segmenter for ASR audio capture.

Features:
- Module-level singleton `asr_buffer` is disabled by default -> zero Phase 1 impact.
- Ultra-sensitive acoustic detection (picks up faint / distant astronaut murmurs, RMS >= 0.002).
- Automatic Gain Control (AGC) peak normalization to ensure high Whisper accuracy.
- Rolling 350ms pre-roll buffer to prevent clipping the first consonant of speech.
- Sub-second silence-boundary segmentation (~650ms natural pause detection).
- Autonomous background transcription worker with hallucination filtering.
- Hands-free voice navigation command parsing ("switch to logs", "show live", "tab 1..4", etc.).
- Fully thread-safe with non-blocking UI polling.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from collections import deque
from typing import Any, Optional, Tuple

import numpy as np

log = logging.getLogger(__name__)

# Constants
_SAMPLE_RATE: int = 16_000
_MIN_BATCH_SAMPLES: int = 48_000        # 3 s for legacy batching
_RING_MAX_SAMPLES: int = 160_000        # ~10 s memory cap for legacy ring
_PREROLL_SAMPLES: int = 5_600           # ~350 ms pre-speech buffer
_MIN_SPEECH_SAMPLES: int = 8_000        # >= 0.50 s to qualify as spoken utterance
_MAX_UTTERANCE_SAMPLES: int = 192_000   # 12.0 s max utterance length
_SILENCE_BOUNDARY_SAMPLES: int = 10_400 # 0.65 s silence signals end-of-turn

# Canonical Tab Definitions for Navigation
TAB_NAMES = [
    "🔴 Live Monitoring",
    "📊 Mission Logs & Trends",
    "🎬 Demo & Mission Control",
    "🧠 AI Psychological Support",
]

# Targeted regex patterns for hands-free voice commands.
# Word boundaries and structural matching guarantee conversational queries
# like "Telemetry shows low cabin oxygen" or "Live video is glitching"
# are NEVER falsely intercepted as navigation commands.
_NAV_PATTERNS = [
    # Tab 0: Live Monitoring
    (0, re.compile(
        r'^(?:(?:hey\s+|dr\.?\s+)?maitri[,:]?\s*)?(?:switch\s+to|go\s+to|open|show(?:\s+me)?|display|navigate\s+to|jump\s+to)?\s*(?:the\s+)?(?:tab\s+(?:1|one)|first\s+tab|live(?:\s+monitoring|\s+feed|\s+cockpit|\s+camera|\s+view)?|cockpit(?:\s+camera)?|camera\s+feed)\s*[.!]?$',
        re.IGNORECASE
    )),
    # Tab 1: Logs & Trends
    (1, re.compile(
        r'^(?:(?:hey\s+|dr\.?\s+)?maitri[,:]?\s*)?(?:switch\s+to|go\s+to|open|show(?:\s+me)?|display|navigate\s+to|jump\s+to)?\s*(?:the\s+)?(?:tab\s+(?:2|two)|second\s+tab|(?:mission\s+)?logs(?:\s+and\s+trends|\s+tab)?|telemetry(?:\s+trends|\s+history|\s+logs)?|history(?:\s+tab|\s+trends)?|(?:emotion\s+|telemetry\s+)?graph|trends)\s*[.!]?$',
        re.IGNORECASE
    )),
    # Tab 2: Demo & Mission Control
    (2, re.compile(
        r'^(?:(?:hey\s+|dr\.?\s+)?maitri[,:]?\s*)?(?:switch\s+to|go\s+to|open|show(?:\s+me)?|display|navigate\s+to|jump\s+to)?\s*(?:the\s+)?(?:tab\s+(?:3|three)|third\s+tab|demo(?:\s+tab|\s+mode|\s+scenarios)?|mission\s+control|simulation(?:\s+tab)?|watchdog\s+dossier)\s*[.!]?$',
        re.IGNORECASE
    )),
    # Tab 3: AI Psychological Support
    (3, re.compile(
        r'^(?:(?:hey\s+|dr\.?\s+)?maitri[,:]?\s*)?(?:switch\s+to|go\s+to|open|show(?:\s+me)?|display|navigate\s+to|jump\s+to)?\s*(?:the\s+)?(?:tab\s+(?:4|four)|fourth\s+tab|psychological\s+support|psych\s+support|support(?:\s+tab|\s+chat)?|chat(?:\s+tab)?|grounding(?:\s+tab|\s+protocol)?|open\s+grounding)\s*[.!]?$',
        re.IGNORECASE
    )),
]

# Action voice command patterns (e.g. hands-free telemetry logging)
_ACTION_PATTERNS = [
    ("log_reading", re.compile(
        r'^(?:(?:hey\s+|dr\.?\s+)?maitri[,:]?\s*)?(?:log|record|save)\s+(?:the\s+)?(?:telemetry|reading|data|vitals)\s*[.!]?$',
        re.IGNORECASE
    )),
]

_HALLUCINATIONS = {
    "", "you", "you.", "thank you", "thank you.", "thanks for watching",
    "thanks for watching!", "subtitles by", "[blank_audio]", "bye", "so", ".",
    "thank you very much.", "subscribe",
}


def parse_voice_command(text: str) -> Optional[Tuple[int, str]]:
    """
    Parse transcribed astronaut text for hands-free tab switching commands.
    Uses strict regex patterns to distinguish deliberate imperative commands
    from natural conversational speech reporting telemetry or symptoms.
    Returns (tab_index, tab_name) or None if text is conversational.
    """
    clean = text.strip()
    if not clean:
        return None

    # Check against canonical navigation patterns
    for tab_idx, pattern in _NAV_PATTERNS:
        if pattern.match(clean):
            return tab_idx, TAB_NAMES[tab_idx]

    return None


def parse_voice_action(text: str) -> Optional[str]:
    """
    Parse transcribed astronaut text for voice actions (e.g. 'log reading').
    Returns action string (e.g. 'log_reading') or None.
    """
    clean = text.strip()
    if not clean:
        return None
    for action_id, pattern in _ACTION_PATTERNS:
        if pattern.match(clean):
            return action_id
    return None


class ASRBuffer:
    """
    Thread-safe ring buffer and autonomous VAD speech segmenter.

    Producer API (WebRTC recv thread or sounddevice callback):
        push(audio)

    Consumer API:
        get_batch()            -> legacy threshold batching
        drain()                -> legacy instantaneous clear
        pop_transcript()       -> non-blocking pop of autonomous ASR recognition
        pop_completed_utterance() -> pop raw normalized speech array
        get_telemetry()        -> live RMS, noise floor, and VAD speech state
    """

    def __init__(
        self,
        min_batch_samples: int = _MIN_BATCH_SAMPLES,
        max_samples: int = _RING_MAX_SAMPLES,
    ) -> None:
        self._lock = threading.Lock()
        self._enabled: bool = False

        # Legacy ring buffer structures
        self._chunks: deque[np.ndarray] = deque()
        self._total_samples: int = 0
        self._min_batch_samples = min_batch_samples
        self._max_samples = max_samples

        # Ultra-sensitive VAD and AGC parameters
        self._noise_floor: float = 0.0010
        self._min_speech_rms: float = 0.0018  # high sensitivity for distant / quiet astronaut
        self._sensitivity_mult: float = 1.25
        self._last_rms: float = 0.0

        # Segmenter state
        self._preroll: deque[np.ndarray] = deque()
        self._preroll_samples: int = 0
        self._in_speech: bool = False
        self._speech_samples: int = 0
        self._silence_samples: int = 0
        self._current_utterance: list[np.ndarray] = []

        # Output queues
        self._completed_utterances: deque[np.ndarray] = deque(maxlen=20)
        self._transcript_queue: deque[dict[str, Any]] = deque(maxlen=50)

        # Background worker management
        self._phase2_mgr: Any = None
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_worker = threading.Event()

    # ── Control & Registration ───────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, value: bool) -> None:
        """Enable or disable audio collection and autonomous segmentation."""
        with self._lock:
            self._enabled = value
            if not value:
                self._chunks.clear()
                self._total_samples = 0
                self._preroll.clear()
                self._preroll_samples = 0
                self._in_speech = False
                self._speech_samples = 0
                self._silence_samples = 0
                self._current_utterance.clear()

    def register_phase2_manager(self, mgr: Any) -> None:
        """Register the loaded Phase2Manager to enable autonomous background ASR."""
        self._phase2_mgr = mgr
        self._ensure_worker_running()

    def _ensure_worker_running(self) -> None:
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_worker.clear()
            self._worker_thread = threading.Thread(
                target=self._autonomous_asr_loop,
                daemon=True,
                name="MAITRI-AutonomousASRWorker",
            )
            self._worker_thread.start()

    # ── Producer API ─────────────────────────────────────────────────────────

    def push(self, audio: np.ndarray) -> None:
        """
        Push a float32 mono audio chunk (16 kHz).
        Performs AGC estimation, pre-roll accumulation, and silence-boundary VAD.
        """
        if not self._enabled:
            return

        chunk = np.asarray(audio, dtype=np.float32).ravel()
        if chunk.size == 0:
            return

        with self._lock:
            # 1. Feed legacy ring buffer
            self._chunks.append(chunk)
            self._total_samples += chunk.size
            while self._total_samples > self._max_samples and self._chunks:
                evicted = self._chunks.popleft()
                self._total_samples -= evicted.size

            # 2. VAD & Energy metrics
            rms = float(np.sqrt(np.mean(chunk ** 2)))
            self._last_rms = rms

            if not self._in_speech:
                # Continuously track ambient noise floor
                self._noise_floor = min(self._noise_floor * 0.995 + rms * 0.005, 0.04)

            # Adaptive threshold for speech onset
            thresh = max(self._min_speech_rms, self._noise_floor * self._sensitivity_mult)
            is_loud = rms >= thresh

            if is_loud:
                if not self._in_speech:
                    # Speech Onset detected: flush pre-roll to preserve starting consonant
                    self._in_speech = True
                    self._speech_samples = 0
                    self._silence_samples = 0
                    self._current_utterance = list(self._preroll)

                self._current_utterance.append(chunk)
                self._speech_samples += chunk.size
                self._silence_samples = 0

                # Max utterance safeguard (12s)
                if self._speech_samples >= _MAX_UTTERANCE_SAMPLES:
                    self._finalize_active_utterance_locked()

            else:
                if self._in_speech:
                    # Trailing silence after speech
                    self._current_utterance.append(chunk)
                    self._silence_samples += chunk.size

                    # Boundary detected: astronaut finished speaking!
                    if self._silence_samples >= _SILENCE_BOUNDARY_SAMPLES:
                        self._finalize_active_utterance_locked()
                else:
                    # Background pre-speech silence -> rolling pre-roll
                    self._preroll.append(chunk)
                    self._preroll_samples += chunk.size
                    while self._preroll_samples > _PREROLL_SAMPLES and self._preroll:
                        evicted_pre = self._preroll.popleft()
                        self._preroll_samples -= evicted_pre.size

    def _finalize_active_utterance_locked(self) -> None:
        """Package the completed utterance with AGC peak normalization."""
        if self._speech_samples >= _MIN_SPEECH_SAMPLES and self._current_utterance:
            audio = np.concatenate(self._current_utterance)
            # Automatic Gain Control (AGC): Peak normalize to reference 0.82
            peak = float(np.max(np.abs(audio)))
            if peak > 1e-4:
                scale = min(35.0, 0.82 / peak)  # max 35x gain for faint/distant astronaut speech
                audio = np.clip(audio * scale, -0.99, 0.99)

            self._completed_utterances.append(audio)
            log.info("ASRBuffer: speech utterance captured (%.2fs, peak=%.3f, scale=%.1f)", len(audio) / _SAMPLE_RATE, peak, scale)

        self._in_speech = False
        self._speech_samples = 0
        self._silence_samples = 0
        self._current_utterance.clear()
        self._preroll.clear()
        self._preroll_samples = 0

    # ── Background Autonomous Transcription Loop ─────────────────────────────

    def _autonomous_asr_loop(self) -> None:
        """Worker thread converting completed speech utterances to text autonomously."""
        while not self._stop_worker.is_set():
            audio_to_transcribe: Optional[np.ndarray] = None
            with self._lock:
                if self._completed_utterances:
                    audio_to_transcribe = self._completed_utterances.popleft()

            if audio_to_transcribe is not None:
                mgr = self._phase2_mgr
                if mgr is not None and getattr(mgr, "is_loaded", False):
                    try:
                        text = mgr.transcribe(audio_to_transcribe)
                        cleaned = text.strip()
                        lower_check = cleaned.lower().strip(".!? ")

                        if lower_check and lower_check not in _HALLUCINATIONS:
                            cmd = parse_voice_command(cleaned)
                            act = parse_voice_action(cleaned)
                            is_cmd = (cmd is not None) or (act is not None)
                            tab_idx, tab_name = cmd if cmd is not None else (None, None)

                            with self._lock:
                                self._transcript_queue.append({
                                    "text": cleaned,
                                    "is_command": is_cmd,
                                    "tab_index": tab_idx,
                                    "tab_name": tab_name,
                                    "action": act,
                                    "timestamp": time.time(),
                                    "duration_s": round(len(audio_to_transcribe) / _SAMPLE_RATE, 2),
                                })
                            log.info("ASRBuffer: autonomous transcription: '%s' (command=%s, act=%s)", cleaned, is_cmd, act)
                    except Exception as exc:
                        log.error("ASRBuffer worker transcription error: %s", exc)
                else:
                    # Put back and wait for manager load
                    with self._lock:
                        self._completed_utterances.appendleft(audio_to_transcribe)
                    time.sleep(0.2)
            else:
                time.sleep(0.05)

    # ── Consumer API ─────────────────────────────────────────────────────────

    def has_transcript(self) -> bool:
        """Non-blocking check if any recognized transcripts are pending in queue."""
        with self._lock:
            return len(self._transcript_queue) > 0

    def pop_transcript(self) -> Optional[dict[str, Any]]:
        """Non-blocking pop of the next autonomously recognized speech event."""
        with self._lock:
            if not self._transcript_queue:
                return None
            return self._transcript_queue.popleft()

    def pop_completed_utterance(self) -> Optional[np.ndarray]:
        """Pop the next completed audio utterance (float32 array)."""
        with self._lock:
            if not self._completed_utterances:
                return None
            return self._completed_utterances.popleft()

    def get_telemetry(self) -> dict[str, Any]:
        """Return real-time acoustic telemetry for UI display."""
        with self._lock:
            return {
                "in_speech": self._in_speech,
                "rms": round(self._last_rms, 4),
                "noise_floor": round(self._noise_floor, 4),
                "speech_duration_s": round(self._speech_samples / _SAMPLE_RATE, 2),
                "silence_duration_s": round(self._silence_samples / _SAMPLE_RATE, 2),
                "queued_utterances": len(self._completed_utterances),
                "queued_transcripts": len(self._transcript_queue),
            }

    # ── Legacy Compatibility API ─────────────────────────────────────────────

    def get_batch(self, min_samples: Optional[int] = None) -> Optional[np.ndarray]:
        """Legacy batch extraction: drain accumulated audio if >= threshold."""
        threshold = min_samples if min_samples is not None else self._min_batch_samples
        with self._lock:
            if self._total_samples < threshold:
                return None
            batch = np.concatenate(list(self._chunks))
            self._chunks.clear()
            self._total_samples = 0
        return batch

    def drain(self) -> Optional[np.ndarray]:
        """Legacy drain: immediately return all buffered audio and clear."""
        with self._lock:
            if not self._chunks or self._total_samples == 0:
                return None
            batch = np.concatenate(list(self._chunks))
            self._chunks.clear()
            self._total_samples = 0
        return batch

    @property
    def pending_samples(self) -> int:
        with self._lock:
            return self._total_samples


# ── Module-level singleton (disabled by default) ──────────────────────────────
asr_buffer: ASRBuffer = ASRBuffer()

