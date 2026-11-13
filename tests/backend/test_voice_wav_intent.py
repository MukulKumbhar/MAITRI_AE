"""
MAITRI 2.0 — End-to-End Streaming WAV Audio Intent & Safety Tests
Tests real 16 kHz WAV audio files decoded through the offline Vosk Kaldi speech recognizer,
parsed through the fuzzy intent parser with spoken word entity extraction, and guarded by
the SafetyConfirmationGate.
"""

import asyncio
import io
import json
import wave
from pathlib import Path
import pytest
import numpy as np
from scipy.signal import resample

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

from modules.phase2_core import Phase2Manager, Phase2Config
from backend.services.voice_service import VoiceService
from backend.state import AppState


@pytest.fixture(scope="module")
def audio_synthesizer():
    """Module-level Piper TTS synthesizer for generating offline 16kHz test WAV files."""
    mgr = Phase2Manager()
    cfg = Phase2Config()
    cfg.llm_enabled = False
    cfg.asr_enabled = False
    cfg.tts_enabled = True
    mgr.load_models(cfg)

    def synth_16k_wav(phrase: str):
        raw_wav = mgr.speak(phrase)
        assert len(raw_wav) > 44, f"TTS synthesis failed for phrase '{phrase}'"
        with wave.open(io.BytesIO(raw_wav), "rb") as wf:
            sr = wf.getframerate()
            n_frames = wf.getnframes()
            pcm = np.frombuffer(wf.readframes(n_frames), dtype=np.int16)
        num_target = int(len(pcm) * 16000 / sr)
        pcm16 = resample(pcm, num_target).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as out_wf:
            out_wf.setnchannels(1)
            out_wf.setsampwidth(2)
            out_wf.setframerate(16000)
            out_wf.writeframes(pcm16.tobytes())
        return buf.getvalue(), pcm16.tobytes()

    return synth_16k_wav


@pytest.fixture
def voice_pipeline():
    svc = VoiceService()
    assert svc.init_vosk() is True
    state = AppState()
    return svc, state


async def stream_audio_to_service(svc: VoiceService, pcm_bytes: bytes, state: AppState, chunk_size: int = 1600):
    """Stream PCM audio in 100ms chunks followed by silence to trigger VAD speech end."""
    for i in range(0, len(pcm_bytes), chunk_size):
        await svc.push_audio_chunk(pcm_bytes[i:i + chunk_size], state)
    # Stream 500ms trailing silence to trigger VAD speech end and flush FinalResult
    silence = bytes(16000)
    for i in range(0, len(silence), chunk_size):
        await svc.push_audio_chunk(silence[i:i + chunk_size], state)


class TestWavVoiceIntentPipeline:
    def test_wav_speech_navigation_live(self, audio_synthesizer, voice_pipeline):
        svc, state = voice_pipeline
        wav_bytes, pcm_bytes = audio_synthesizer("open live feed")
        assert len(wav_bytes) > 0

        events = []
        async def on_event(evt):
            events.append(evt)
        svc.add_event_callback(on_event)

        asyncio.run(stream_audio_to_service(svc, pcm_bytes, state))

        # Check VAD fired
        assert any(e.get("type") == "vad_speech_start" for e in events)
        assert any(e.get("type") == "vad_speech_end" for e in events)

        # Check final transcript and action
        finals = [e for e in events if e.get("type") == "asr_final_transcript"]
        assert len(finals) > 0
        assert "open live feed" in finals[0]["transcript"].lower()
        assert finals[0]["latency_ms"] > 0

        actions = [e for e in events if e.get("type") == "voice_action_dispatched"]
        assert any(a.get("action") == "navigate" and a.get("target") == "live" for a in actions)

    def test_wav_speech_show_vitals(self, audio_synthesizer, voice_pipeline):
        svc, state = voice_pipeline
        state.heart_rate = 88.0
        state.spo2 = 97.0
        _, pcm_bytes = audio_synthesizer("show vitals")

        events = []
        async def on_event(evt):
            events.append(evt)
        svc.add_event_callback(on_event)

        asyncio.run(stream_audio_to_service(svc, pcm_bytes, state))

        actions = [e for e in events if e.get("type") == "voice_action_dispatched"]
        assert any(a.get("action") == "read_vitals" for a in actions)
        vitals_action = next(a for a in actions if a.get("action") == "read_vitals")
        assert "88 beats per minute" in vitals_action["message"]
        assert "97 percent" in vitals_action["message"]

    def test_wav_speech_read_stress(self, audio_synthesizer, voice_pipeline):
        svc, state = voice_pipeline
        state.fusion.last_stress = 42.5
        state.fusion.last_emotion = "calm"
        _, pcm_bytes = audio_synthesizer("show stress")

        events = []
        async def on_event(evt):
            events.append(evt)
        svc.add_event_callback(on_event)

        asyncio.run(stream_audio_to_service(svc, pcm_bytes, state))

        actions = [e for e in events if e.get("type") == "voice_action_dispatched"]
        assert any(a.get("action") == "read_stress" for a in actions)
        stress_action = next(a for a in actions if a.get("action") == "read_stress")
        assert "42.5 percent" in stress_action["message"]
        assert stress_action["level"] == "mild"

    def test_wav_speech_set_heart_rate_spoken_words(self, audio_synthesizer, voice_pipeline):
        svc, state = voice_pipeline
        _, pcm_bytes = audio_synthesizer("set heart rate to eighty five")

        events = []
        async def on_event(evt):
            events.append(evt)
        svc.add_event_callback(on_event)

        asyncio.run(stream_audio_to_service(svc, pcm_bytes, state))

        actions = [e for e in events if e.get("type") == "voice_action_dispatched"]
        assert any(a.get("action") == "set_heart_rate" for a in actions)
        assert state.heart_rate == pytest.approx(85.0)

    def test_wav_speech_critical_safety_confirmation_flow(self, audio_synthesizer, voice_pipeline):
        svc, state = voice_pipeline
        # Simulate watchdog in CHECK_IN / alert state
        state.watchdog.trigger_simulation()
        assert state.watchdog.state == "CHECK_IN"

        events = []
        async def on_event(evt):
            events.append(evt)
        svc.add_event_callback(on_event)

        # 1. Spoken critical action: "override incapacitation"
        _, pcm_override = audio_synthesizer("override incapacitation")
        asyncio.run(stream_audio_to_service(svc, pcm_override, state))

        # Must trigger safety gate challenge, NOT direct override!
        challenges = [e for e in events if e.get("type") == "safety_gate_challenge"]
        assert len(challenges) > 0
        assert challenges[0]["action"] == "critical_override"
        # Watchdog must STILL be unacknowledged!
        assert state.watchdog.state == "CHECK_IN"

        # 2. Spoken confirmation: "confirm override"
        events.clear()
        _, pcm_confirm = audio_synthesizer("confirm override")
        asyncio.run(stream_audio_to_service(svc, pcm_confirm, state))

        # Must dispatch confirmed override and reset watchdog to NORMAL
        confirmed = [e for e in events if e.get("type") == "voice_action_dispatched" and e.get("action") == "critical_override_confirmed"]
        assert len(confirmed) > 0
        assert state.watchdog.state == "NORMAL"

    def test_multiple_listeners_and_session_reset(self, voice_pipeline):
        svc, state = voice_pipeline
        events_a = []
        events_b = []

        async def cb_a(e):
            events_a.append(e)

        async def cb_b(e):
            events_b.append(e)

        svc.add_event_callback(cb_a)
        svc.add_event_callback(cb_b)

        # Feed 1 chunk of silence
        silence = bytes(3200)
        asyncio.run(svc.push_audio_chunk(silence, state))

        assert len(events_a) > 0
        assert len(events_b) > 0
        assert len(events_a) == len(events_b)

        # Remove listener A
        svc.remove_event_callback(cb_a)
        events_a.clear()
        events_b.clear()

        asyncio.run(svc.push_audio_chunk(silence, state))
        assert len(events_a) == 0
        assert len(events_b) > 0

        # Session reset should not raise
        svc.reset_session()
        assert svc._speaking is False
