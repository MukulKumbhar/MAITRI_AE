"""
MAITRI 2.0 — Voice Service (Phase 3 Full Implementation)
Streaming Offline Vosk STT, VAD, Fuzzy Intent Parser & Safety Confirmation Gate
"""

import asyncio
import base64
import json
import logging
import math
import os
import struct
import time
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional

from backend.services.intent_parser import (
    SafetyConfirmationGate,
    parse_intent,
)

logger = logging.getLogger("maitri.voice")

# VAD and Audio Parameters
_SAMPLE_RATE: int = 16000
_SPEECH_RMS_THRESHOLD: float = 0.03   # Linear RMS threshold (approx -30 dB)
_SPEECH_CHUNK_SIZE: int = 1600        # 100ms @ 16kHz samples
_RMS_WINDOW_SIZE: int = 8             # Number of recent chunks for smoothed RMS

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_VOSK_MODEL_DIR = _PROJECT_ROOT / "models" / "vosk"

_standalone_piper = None


def _get_standalone_piper():
    global _standalone_piper
    if _standalone_piper is None:
        try:
            from piper import PiperVoice
            model_path = _PROJECT_ROOT / "models" / "piper_voice" / "en_US-lessac-medium.onnx"
            config_path = _PROJECT_ROOT / "models" / "piper_voice" / "en_US-lessac-medium.onnx.json"
            if model_path.exists() and config_path.exists():
                _standalone_piper = PiperVoice.load(str(model_path), str(config_path), use_cuda=False)
                logger.info("✅ Pre-warmed standalone Piper TTS for instant voice talkback")
        except Exception as exc:
            logger.debug("Could not load standalone Piper: %s", exc)
    return _standalone_piper


def _synthesize_standalone_wav(text: str) -> Optional[bytes]:
    pv = _get_standalone_piper()
    if pv is not None:
        try:
            import io
            import wave
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                pv.synthesize_wav(text, wf)
            return buf.getvalue()
        except Exception as exc:
            logger.debug("Standalone Piper synthesis error: %s", exc)
    return None


class VoiceService:
    """
    Offline Voice Service:
    - Ingests 16 kHz 16-bit Mono PCM binary chunks from the browser AudioWorklet.
    - Ballistic VU level metering (RMS and dB).
    - Streaming Vosk Speech-to-Text hypothesis & final transcripts (<50ms latency).
    - Fuzzy intent matching with entity extraction.
    - Safety Confirmation Gate for critical actions.
    - Dispatches state actions and emits telemetry/debug events back over WebSocket.
    """

    def __init__(self) -> None:
        self._speaking: bool = False
        self._recent_rms: List[float] = []
        self._vosk_ready: bool = False
        self._vosk_model = None
        self._vosk_rec = None
        self._safety_gate = SafetyConfirmationGate(timeout_sec=10.0)
        self._callbacks: List[Callable[..., Coroutine]] = []
        self._last_speech_time: float = 0.0
        self._last_intent_info: Dict[str, Any] = {
            "intent": None,
            "confidence": 0.0,
            "transcript": "",
            "pattern": "",
            "latency_ms": 0.0,
            "status": "IDLE",
        }

    def init_vosk(self) -> bool:
        """Attempt to load Vosk model from local models directory."""
        if _VOSK_MODEL_DIR.exists():
            try:
                import vosk  # type: ignore
                # Silence Kaldi debug logs to stdout
                vosk.SetLogLevel(-1)
                self._vosk_model = vosk.Model(str(_VOSK_MODEL_DIR))
                self._vosk_rec = vosk.KaldiRecognizer(self._vosk_model, _SAMPLE_RATE)
                self._vosk_rec.SetWords(True)
                self._vosk_ready = True
                logger.info("✅ Vosk Kaldi speech model loaded from %s", _VOSK_MODEL_DIR)
                return True
            except Exception as exc:
                logger.warning("⚠️  Could not load Vosk model: %s", exc)
                self._vosk_ready = False
                return False
        else:
            logger.info("ℹ️  Vosk model directory not found at %s", _VOSK_MODEL_DIR)
            self._vosk_ready = False
            return False

    def is_vosk_ready(self) -> bool:
        return self._vosk_ready

    def add_event_callback(self, cb: Callable[..., Coroutine]) -> None:
        """Register an async callback for dispatching events to WS client."""
        if cb not in self._callbacks:
            self._callbacks.append(cb)

    def remove_event_callback(self, cb: Callable[..., Coroutine]) -> None:
        """Unregister an async callback."""
        if cb in self._callbacks:
            self._callbacks.remove(cb)

    def set_event_callback(self, cb: Optional[Callable[..., Coroutine]]) -> None:
        """Set or clear a single callback (backward compatibility helper)."""
        self._callbacks = [cb] if cb else []

    def reset_session(self) -> None:
        """Reset Kaldi recognizer and VAD state on client reconnection."""
        self._speaking = False
        self._recent_rms.clear()
        if self._vosk_ready and self._vosk_rec:
            try:
                self._vosk_rec.Reset()
            except Exception:
                pass

    async def flush(self, state: Any) -> None:
        """Force flush any pending recognizer utterance (e.g. on stream close or silence)."""
        if self._vosk_ready and self._vosk_rec:
            try:
                res = json.loads(self._vosk_rec.FinalResult())
                transcript = res.get("text", "").strip()
                if transcript:
                    await self._handle_transcript(transcript, state, is_final=True, latency_ms=0.0)
            except Exception as exc:
                logger.debug("Vosk manual flush error: %s", exc)

    async def _emit(self, event: dict) -> None:
        for cb in list(self._callbacks):
            try:
                await cb(event)
            except Exception as exc:
                logger.debug("Event emit error: %s", exc)

    async def push_audio_chunk(self, pcm_bytes: bytes, state) -> None:
        """
        Process a chunk of raw 16-bit PCM (16kHz mono).
        Updates live state voice metrics and feeds the Vosk recognizer.
        """
        if len(pcm_bytes) < 2:
            return

        t0 = time.perf_counter()

        # Unpack 16-bit PCM samples
        n_samples = len(pcm_bytes) // 2
        samples = struct.unpack(f"<{n_samples}h", pcm_bytes[:n_samples * 2])

        # Compute RMS
        rms_linear = _compute_rms_int16(samples)
        rms_float = rms_linear / 32768.0  # normalize to 0.0–1.0

        # Smoothed RMS using rolling window
        self._recent_rms.append(rms_float)
        if len(self._recent_rms) > _RMS_WINDOW_SIZE:
            self._recent_rms.pop(0)
        smoothed_rms = sum(self._recent_rms) / len(self._recent_rms)

        # Update live state voice metrics
        threshold = getattr(state, "silence_threshold", _SPEECH_RMS_THRESHOLD)
        gain = getattr(state, "mic_gain", 1.0)
        effective_rms = min(1.0, smoothed_rms * gain)
        is_speaking = effective_rms > threshold

        with state.live.voice_lock:
            state.live.voice_rms = effective_rms
            state.live.is_speaking = is_speaking

        # Emit VAD transitions
        if is_speaking and not self._speaking:
            self._speaking = True
            self._last_speech_time = time.perf_counter()
            await self._emit({"type": "vad_speech_start", "rms": round(effective_rms, 6)})
        elif not is_speaking and self._speaking:
            self._speaking = False
            await self._emit({"type": "vad_speech_end", "rms": round(effective_rms, 6)})
            # Harvest any completed utterance that Kaldi hasn't endpointed yet
            if self._vosk_ready and self._vosk_rec:
                try:
                    res = json.loads(self._vosk_rec.FinalResult())
                    transcript = res.get("text", "").strip()
                    if transcript:
                        latency_ms = (time.perf_counter() - self._last_speech_time) * 1000.0
                        await self._handle_transcript(transcript, state, is_final=True, latency_ms=latency_ms)
                except Exception as exc:
                    logger.debug("Vosk flush error on vad_speech_end: %s", exc)

        # Emit audio level for VU meter
        db = round(20 * math.log10(max(effective_rms, 1e-9)), 1)
        await self._emit({
            "type": "audio_level",
            "rms": round(effective_rms, 6),
            "db": db,
            "is_speaking": is_speaking,
            "debug": {
                "gain": gain,
                "threshold": threshold,
                "vosk_ready": self._vosk_ready,
                "last_intent": self._last_intent_info["intent"],
                "last_confidence": self._last_intent_info["confidence"],
                "safety_awaiting": self._safety_gate.is_awaiting_confirmation(time.time()),
            }
        })

        # Feed PCM to Vosk if available
        if self._vosk_ready and self._vosk_rec:
            # If mic gain is applied, scale PCM samples
            if abs(gain - 1.0) > 0.05:
                scaled_samples = [max(-32768, min(32767, int(s * gain))) for s in samples]
                pcm_to_feed = struct.pack(f"<{len(scaled_samples)}h", *scaled_samples)
            else:
                pcm_to_feed = pcm_bytes

            if self._vosk_rec.AcceptWaveform(pcm_to_feed):
                # Final transcript for utterance
                res = json.loads(self._vosk_rec.Result())
                transcript = res.get("text", "").strip()
                if transcript:
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    await self._handle_transcript(transcript, state, is_final=True, latency_ms=latency_ms)
            else:
                # Partial / interim transcript
                partial = json.loads(self._vosk_rec.PartialResult())
                partial_text = partial.get("partial", "").strip()
                if partial_text:
                    await self._emit({
                        "type": "asr_interim_transcript",
                        "transcript": partial_text,
                    })

    async def _handle_transcript(
        self, transcript: str, state: Any, is_final: bool, latency_ms: float = 0.0
    ) -> None:
        """Parse intent from final transcript and execute matching action."""
        logger.info("🗣️ ASR Final Transcript: '%s'", transcript)
        await self._emit({
            "type": "asr_final_transcript",
            "transcript": transcript,
            "latency_ms": round(latency_ms, 2),
        })

        # Parse intent
        parsed = parse_intent(transcript, confidence_threshold=0.55)
        intent = parsed.get("intent")
        confidence = parsed.get("confidence", 0.0)
        pattern = parsed.get("matched_pattern", "")

        self._last_intent_info = {
            "intent": intent,
            "confidence": confidence,
            "transcript": transcript,
            "pattern": pattern,
            "latency_ms": round(latency_ms, 2),
            "status": "MATCHED" if intent else "NO_MATCH",
        }

        # Check safety gate confirmation
        now = time.time()
        if intent == "confirm_critical":
            confirmed_action = self._safety_gate.confirm_action(now)
            if confirmed_action:
                logger.info("🛡️ Safety Gate: Confirmed critical action '%s'", confirmed_action)
                state.watchdog.acknowledge()
                await self._emit({
                    "type": "voice_action_dispatched",
                    "action": "critical_override_confirmed",
                    "message": "Incapacitation emergency overridden and reset.",
                    "status": "SUCCESS",
                })
                await self._speak_feedback("Incapacitation override confirmed. Systems reset to nominal.")
                return

        if parsed.get("requires_confirmation", False):
            # Prompt user for confirmation
            prompt_msg = self._safety_gate.request_critical_action(intent, now)
            await self._emit({
                "type": "safety_gate_challenge",
                "action": intent,
                "message": prompt_msg,
                "timeout_sec": self._safety_gate.timeout_sec,
            })
            await self._speak_feedback("Safety confirmation required. Say 'Confirm override' or press the console button.")
            return

        # Execute normal intent actions
        if intent:
            await self._execute_intent_action(intent, parsed, state)

    async def _execute_intent_action(
        self, intent: str, parsed: Dict[str, Any], state: Any
    ) -> None:
        """Dispatch state updates and inform UI."""
        entities = parsed.get("entities", {})

        if intent == "navigate_live":
            await self._emit({"type": "voice_action_dispatched", "action": "navigate", "target": "live"})
            await self._speak_feedback("Switching to live cockpit.")
        elif intent == "navigate_logs":
            await self._emit({"type": "voice_action_dispatched", "action": "navigate", "target": "logs"})
            await self._speak_feedback("Opening mission telemetry logs.")
        elif intent == "navigate_mission":
            await self._emit({"type": "voice_action_dispatched", "action": "navigate", "target": "mission"})
            await self._speak_feedback("Opening mission scenarios and dossier.")
        elif intent == "navigate_support":
            await self._emit({"type": "voice_action_dispatched", "action": "navigate", "target": "support"})
            await self._speak_feedback("Connecting to psychological support engine.")
        elif intent == "navigate_clinical":
            await self._emit({"type": "voice_action_dispatched", "action": "navigate", "target": "clinical"})
            await self._speak_feedback("Opening clinical monitoring and diagnostics panel.")
        elif intent == "navigate_sleep":
            await self._emit({"type": "voice_action_dispatched", "action": "navigate", "target": "sleep"})
            await self._speak_feedback("Opening circadian and orbital cycle tracker.")

        elif intent == "start_pvt":
            from modules.pvt_module import PVTSession
            from backend.api import clinical
            clinical._active_pvt_session = PVTSession(crew_member=getattr(state, "active_crew", "Astronaut"), duration_s=180.0)
            clinical._active_pvt_session.start()
            await self._emit({
                "type": "voice_action_dispatched",
                "action": "start_pvt",
                "session": clinical._active_pvt_session.get_status(),
            })
            await self._speak_feedback("Starting PVT-B Reaction Self Test. Tap console when stimulus appears.")

        elif intent == "stop_pvt":
            from backend.api import clinical
            if clinical._active_pvt_session:
                clinical._active_pvt_session.abort()
            await self._emit({
                "type": "voice_action_dispatched",
                "action": "stop_pvt",
            })
            await self._speak_feedback("Psychomotor Vigilance Test aborted.")

        elif intent == "screener_depression":
            await self._emit({
                "type": "voice_action_dispatched",
                "action": "open_screener",
                "screener_type": "PHQ-9",
            })
            await self._speak_feedback("Opening PHQ-9 depression screener on console.")

        elif intent == "screener_anxiety":
            await self._emit({
                "type": "voice_action_dispatched",
                "action": "open_screener",
                "screener_type": "GAD-7",
            })
            await self._speak_feedback("Opening GAD-7 anxiety screener on console.")

        elif intent == "checklist_ammonia":
            from modules.medical_kb import get_emergency_checklist
            cl = get_emergency_checklist("checklist_ammonia")
            await self._emit({
                "type": "voice_action_dispatched",
                "action": "open_checklist",
                "checklist": cl,
            })
            await self._speak_feedback("Ammonia leak checklist initiated. Don emergency mask immediately.")

        elif intent == "checklist_trauma":
            from modules.medical_kb import get_emergency_checklist
            cl = get_emergency_checklist("checklist_trauma")
            await self._emit({
                "type": "voice_action_dispatched",
                "action": "open_checklist",
                "checklist": cl,
            })
            await self._speak_feedback("Acute trauma checklist initiated. Apply direct pressure to wound.")

        elif intent == "set_heart_rate":
            val = entities.get("value")
            if val is not None:
                clamped = max(50.0, min(160.0, float(val)))
                state.heart_rate = clamped
                await self._emit({"type": "voice_action_dispatched", "action": "set_heart_rate", "value": clamped})
                await self._speak_feedback(f"Heart rate set to {int(clamped)} beats per minute.")

        elif intent == "set_oxygen":
            val = entities.get("value")
            if val is not None:
                clamped = max(85.0, min(100.0, float(val)))
                state.spo2 = clamped
                await self._emit({"type": "voice_action_dispatched", "action": "set_oxygen", "value": clamped})
                await self._speak_feedback(f"Blood oxygen set to {int(clamped)} percent.")

        elif intent == "watchdog_ack":
            state.watchdog.acknowledge()
            await self._emit({"type": "voice_action_dispatched", "action": "watchdog_ack", "status": "ACKNOWLEDGED"})
            await self._speak_feedback("Watchdog presence acknowledged. Systems nominal.")

        elif intent == "log_reading":
            # Post log to database
            from modules.database_module import log_event
            from modules.database_module import log_event
            from modules.alert_module import get_alert
            try:
                face_snap = state.live.snapshot_face()
                voice_snap = state.live.snapshot_voice()
                stress_val = getattr(state.fusion, "last_stress", 20.0)
                dominant_emo = getattr(state.fusion, "last_emotion", face_snap.get("face_emotion", "neutral"))
                alert_res = get_alert(stress_val, dominant_emo, face_snap.get("fatigue_label", "Normal"))
                log_event(
                    face_emotion=face_snap.get("face_emotion", "neutral"),
                    fused_emotion=dominant_emo,
                    voice_state="speaking" if voice_snap.get("is_speaking") else "silent",
                    heart_rate=state.heart_rate,
                    temperature=state.temperature,
                    spo2=state.spo2,
                    blink_rate=face_snap.get("blink_rate", 14.0),
                    fatigue_label=face_snap.get("fatigue_label", "Normal"),
                    stress_score=stress_val,
                    stress_level=alert_res.stress_level,
                    alert_triggered=alert_res.header,
                    response_msg=alert_res.body,
                    emotion_probs=face_snap.get("emotion_probs"),
                )
                await self._emit({"type": "voice_action_dispatched", "action": "log_reading", "status": "LOGGED"})
            except Exception as exc:
                logger.error("Voice log_reading error: %s", exc)

        elif intent == "start_breathing":
            await self._emit({
                "type": "voice_action_dispatched",
                "action": "start_grounding",
                "technique": "4-7-8 Breathing Protocol",
            })
            await self._speak_feedback("Initiating 4-7-8 breathing protocol. Inhale for 4 seconds, hold for 7, exhale for 8.")

        elif intent == "read_vitals":
            msg = f"Current heart rate is {int(state.heart_rate)} beats per minute. Blood oxygen is {int(state.spo2)} percent."
            await self._emit({"type": "voice_action_dispatched", "action": "read_vitals", "message": msg})
            await self._speak_feedback(msg)

        elif intent == "read_stress":
            stress_val = getattr(state.fusion, "last_stress", 20.0)
            dominant = getattr(state.fusion, "last_emotion", "neutral")
            level = "nominal" if stress_val < 35.0 else ("mild" if stress_val < 55.0 else ("elevated" if stress_val < 75.0 else "critical"))
            msg = f"Current stress index is {stress_val:.1f} percent, status {level}. Dominant affect is {dominant}."
            await self._emit({
                "type": "voice_action_dispatched",
                "action": "read_stress",
                "message": msg,
                "stress": stress_val,
                "level": level,
            })
            await self._speak_feedback(msg)

    async def _speak_feedback(self, text: str) -> None:
        """Synthesize spoken feedback using Piper TTS (with standalone fallback)."""
        try:
            wav_bytes: Optional[bytes] = None
            from backend.services.psych_service import get_phase2_manager, is_loaded
            if is_loaded():
                mgr = get_phase2_manager()
                if mgr and hasattr(mgr, "speak"):
                    if asyncio.iscoroutinefunction(mgr.speak):
                        wav_bytes = await mgr.speak(text)
                    else:
                        wav_bytes = await asyncio.to_thread(mgr.speak, text)

            if not wav_bytes:
                wav_bytes = await asyncio.to_thread(_synthesize_standalone_wav, text)

            if wav_bytes:
                b64_wav = base64.b64encode(wav_bytes).decode("ascii")
                await self._emit({
                    "type": "tts_audio_response",
                    "text": text,
                    "audio_base64": b64_wav,
                })
        except Exception as exc:
            logger.debug("TTS feedback synthesis skipped: %s", exc)


def _compute_rms_int16(samples: tuple) -> float:
    """Compute RMS of 16-bit integer PCM samples."""
    if not samples:
        return 0.0
    sq_sum = sum(s * s for s in samples)
    return (sq_sum / len(samples)) ** 0.5


# Module-level singleton
_voice_service: Optional[VoiceService] = None


def get_voice_service() -> VoiceService:
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService()
    return _voice_service
