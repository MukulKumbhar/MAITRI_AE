"""
modules/phase2_core.py
Phase 2 conversational AI backend for MAITRI 2.0.

Completely self-contained: safe to import even when Phase 2 models are absent.
Phase 1 is never impacted — models are only loaded on explicit call to load_models().
"""

from __future__ import annotations

import io
import logging
import os
import threading
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ── Default model paths relative to project root ─────────────────────────────
_HERE = Path(__file__).resolve().parent.parent  # project root
_MODELS = _HERE / "models"


@dataclass
class Phase2Config:
    """Paths to Phase 2 model files and feature flags."""
    llm_model_path: str = str(_MODELS / "phi3_mini_q4.gguf")
    whisper_model_dir: str = str(_MODELS / "whisper_tiny_en")
    piper_onnx_path: str = str(_MODELS / "piper_voice" / "en_US-lessac-medium.onnx")
    piper_json_path: str = str(_MODELS / "piper_voice" / "en_US-lessac-medium.onnx.json")

    llm_enabled: bool = True
    tts_enabled: bool = True
    asr_enabled: bool = True

    # LLM generation params
    llm_n_ctx: int = 2048
    llm_max_tokens: int = 160
    llm_temperature: float = 0.6

    # Extra fields for forward-compat
    extra: dict = field(default_factory=dict)


def _resolve_whisper_model_path(whisper_model_dir: str) -> str:
    """
    faster-whisper stores models inside an HF cache sub-structure:
      <download_root>/models--Systran--faster-whisper-tiny.en/snapshots/<hash>/
    Walk the tree to find model.bin and return that directory.
    Falls back to the dir itself if model.bin lives there directly.
    """
    base = Path(whisper_model_dir)
    # Direct layout
    if (base / "model.bin").exists():
        return str(base)
    # HF cache layout: walk up to 4 levels
    for model_bin in base.rglob("model.bin"):
        return str(model_bin.parent)
    # If nothing found return original dir (WhisperModel will raise a clear error)
    return str(base)


class Phase2Manager:
    """
    Lazy-loading manager for Phase 2 AI models (LLM, ASR, TTS).

    Usage:
        cfg = Phase2Config()
        mgr = Phase2Manager()
        mgr.load_models(cfg)           # blocks until all models ready
        text  = mgr.transcribe(audio)
        reply = mgr.generate_response(text, emotion="neutral", stress_pct=30.0)
        wav   = mgr.speak(reply)
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._llm = None
        self._whisper = None
        self._piper = None
        self._piper_config = None
        self._loaded = False
        self._config: Optional[Phase2Config] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def load_models(self, config: Optional[Union[Phase2Config, dict]] = None) -> None:
        """
        Lazy-load LLM, Whisper and Piper models.
        Safe to call multiple times — subsequent calls are no-ops.
        Runs synchronously in the calling thread (call from a background thread
        if you want non-blocking startup).
        """
        with self._lock:
            if self._loaded:
                return
            if config is None:
                config = Phase2Config()
            elif isinstance(config, dict):
                import dataclasses
                valid_fields = {f.name for f in dataclasses.fields(Phase2Config)}
                filtered = {k: v for k, v in config.items() if k in valid_fields}
                config = Phase2Config(**filtered)
            self._config = config
            errors = []

            # ── 1. faster-whisper ─────────────────────────────────────────────
            if config.asr_enabled:
                try:
                    from faster_whisper import WhisperModel  # noqa: PLC0415
                    model_path = _resolve_whisper_model_path(config.whisper_model_dir)
                    self._whisper = WhisperModel(
                        model_path,
                        device="cpu",
                        compute_type="int8",
                    )
                    log.info("Phase2: Whisper tiny.en loaded from %s", model_path)
                except Exception as exc:
                    log.error("Phase2: Whisper load failed: %s", exc)
                    errors.append(f"Whisper: {exc}")

            # ── 2. llama-cpp-python (Phi-3-Mini) ──────────────────────────────
            if config.llm_enabled:
                try:
                    from llama_cpp import Llama  # noqa: PLC0415
                    self._llm = Llama(
                        model_path=config.llm_model_path,
                        n_ctx=config.llm_n_ctx,
                        n_threads=max(1, (os.cpu_count() or 4) - 1),
                        verbose=False,
                    )
                    log.info("Phase2: Phi-3-Mini loaded from %s", config.llm_model_path)
                except Exception as exc:
                    log.error("Phase2: LLM load failed: %s", exc)
                    errors.append(f"LLM: {exc}")

            # ── 3. Piper TTS ──────────────────────────────────────────────────
            if config.tts_enabled:
                try:
                    from piper import PiperVoice  # noqa: PLC0415
                    self._piper = PiperVoice.load(
                        model_path=config.piper_onnx_path,
                        config_path=config.piper_json_path,
                        use_cuda=False,
                    )
                    log.info("Phase2: Piper TTS loaded from %s", config.piper_onnx_path)
                except Exception as exc:
                    log.error("Phase2: Piper TTS load failed: %s", exc)
                    errors.append(f"Piper: {exc}")

            self._loaded = True
            if self._whisper is not None:
                try:
                    from modules.asr_tap import asr_buffer
                    asr_buffer.register_phase2_manager(self)
                    log.info("Phase2: Registered with autonomous ASR buffer worker.")
                except Exception as exc:
                    log.warning("Phase2: Could not register with asr_buffer: %s", exc)

            if errors:
                log.warning("Phase2: loaded with errors: %s", "; ".join(errors))

    @property
    def is_loaded(self) -> bool:
        """True once load_models() has been called (even if some models failed)."""
        return self._loaded

    def transcribe(self, audio_input) -> str:
        """
        Run Whisper tiny.en on audio input.
        Accepts:
          - np.ndarray (float32, 1-D or 2-D mono/stereo)
          - bytes or bytearray (raw audio file contents)
          - io.BytesIO or file-like object (e.g. from st.audio_input)

        Returns:
            Transcribed text string, or '' on failure / no speech detected.
        """
        import numpy as np  # noqa: PLC0415

        if self._whisper is None:
            log.debug("Phase2.transcribe: Whisper not loaded — returning ''")
            return ""

        try:
            if isinstance(audio_input, (bytes, bytearray)):
                audio_input = io.BytesIO(audio_input)

            if isinstance(audio_input, np.ndarray):
                arr = np.asarray(audio_input, dtype=np.float32)
                if arr.ndim > 1:
                    arr = arr.mean(axis=1)
                # High sensitivity AGC boost for distant or quiet speech
                peak = float(np.max(np.abs(arr))) if arr.size > 0 else 0.0
                if peak > 1e-4:
                    scale = min(35.0, 0.82 / peak)
                    arr = np.clip(arr * scale, -0.99, 0.99)
                audio_source = arr
            else:
                audio_source = audio_input

            segments, _ = self._whisper.transcribe(
                audio_source,
                language="en",
                beam_size=3,
                vad_filter=False,
            )
            raw_text = " ".join(seg.text.strip() for seg in segments).strip()
            check_str = raw_text.lower().strip(".!? ")
            hallucinations = {
                "", "you", "you.", "thank you", "thank you.", "thanks for watching",
                "thanks for watching!", "subtitles by", "[blank_audio]", "bye", "so", ".",
                "thank you very much.", "subscribe",
            }
            if check_str in hallucinations:
                return ""
            return raw_text
        except Exception as exc:
            log.error("Phase2.transcribe error: %s", exc)
            return ""

    def generate_response(
        self,
        user_text: str = "",
        emotion: str = "neutral",
        stress_pct: float = 0.0,
        astronaut_name: str = "Commander",
        mission_phase: str = "Orbital Operations",
        vitals_summary: Optional[str] = None,
        chat_history: Optional[list] = None,
        **kwargs: Any,
    ) -> str:
        """
        Build an aerospace clinical system prompt and run Phi-3-Mini to produce an empathetic reply.

        Args:
            user_text:       What the astronaut said (or pass query='...').
            emotion:         Current dominant emotion label (or pass dominant_emotion='...').
            stress_pct:      Current stress percentage [0–100].
            astronaut_name:  Crew member title/name (or pass crew_name='...').
            mission_phase:   Active mission profile (or pass mission='...').
            vitals_summary:  Physiological vitals reading if available.
            chat_history:    List of prior chat messages [{'role': 'user'|'assistant', 'content': '...'}]
            **kwargs:        Extra keywords accepted for seamless backward/forward compatibility.

        Returns:
            Model reply string, or '' on failure / model not loaded.
        """
        # Resolve aliases from kwargs if passed
        if not user_text and "query" in kwargs:
            user_text = str(kwargs["query"])
        if "dominant_emotion" in kwargs:
            emotion = str(kwargs["dominant_emotion"])
        if "crew_name" in kwargs:
            astronaut_name = str(kwargs["crew_name"])
        if "mission" in kwargs:
            mission_phase = str(kwargs["mission"])
        if self._llm is None:
            log.debug("Phase2.generate_response: LLM not loaded — returning ''")
            return ""

        # ── Local Curated Clinical Knowledge Base Scoping ─────────────────
        from modules.medical_kb import (
            is_medical_inquiry,
            is_query_in_scope,
            get_curated_grounding_context,
            EXPLICIT_REFUSAL_MESSAGE,
        )
        force_kb = kwargs.get("require_kb_grounding", False)
        is_med = force_kb or (user_text and is_medical_inquiry(user_text))

        grounding_context = ""
        if is_med:
            in_scope, matched = is_query_in_scope(user_text)
            if not in_scope:
                log.info("Phase2: Medical query out of local KB scope — issuing explicit refusal.")
                return EXPLICIT_REFUSAL_MESSAGE
            grounding_context, _ = get_curated_grounding_context(user_text)

        vitals_str = f" Physiological vitals: {vitals_summary}." if vitals_summary else ""
        system_prompt = (
            f"You are MAITRI, the autonomous onboard AI psychological and clinical support companion "
            f"for crewed spaceflight missions (ISRO Gaganyaan, ISS, and deep-space analogues). "
            f"You are speaking directly with {astronaut_name} during the {mission_phase} phase.\n"
            f"Telemetry state: Detected affect is {str(emotion).upper()} with an estimated "
            f"stress strain index of {stress_pct:.1f}%.{vitals_str}\n"
            f"Clinical Instructions:\n"
            f"- Address {astronaut_name} respectfully and warmly.\n"
            f"- Respond in 2 to 3 concise, supportive, and clinically grounded sentences tailored for spoken voice audio.\n"
            f"- This is an orbital/deep-space astronaut mission. Do NOT refer to commercial airlines, passenger cabins, or flight attendants. You are the spacecraft AI companion speaking directly to {astronaut_name}.\n"
            f"- If stress is elevated (>60%) or acute emotions (fear, panic, exhaustion) are detected, integrate "
            f"Cognitive Behavioral Therapy (CBT) grounding: suggest slow rhythmic breathing (4-4-4-4 box breathing or 4-7-8) "
            f"and sensory anchoring.\n"
            f"- Never panic, never suggest aborting unless life-critical, and maintain calm reassuring mission presence."
        )

        if grounding_context:
            system_prompt += (
                f"\n\nLocal Verified Aerospace Clinical Knowledge Reference:\n{grounding_context}\n"
                f"- Ground your response strictly on the verified reference above.\n"
                f"- Cite the source reference (e.g. PubMed/NASA-STD-3001) in your response.\n"
                f"- Never speculate or fabricate clinical diagnoses beyond this reference."
            )

        prompt_parts = [f"<|system|>\n{system_prompt}<|end|>"]
        if chat_history:
            recent_turns = chat_history[-6:]
            for turn in recent_turns:
                role = turn.get("role")
                content = turn.get("content")
                if role in ("user", "assistant") and content:
                    prompt_parts.append(f"<|{role}|>\n{content}<|end|>")
        prompt_parts.append(f"<|user|>\n{user_text}<|end|>\n<|assistant|>\n")
        full_prompt = "\n".join(prompt_parts)

        try:
            with self._lock:
                response = self._llm(
                    full_prompt,
                    max_tokens=self._config.llm_max_tokens if self._config else 160,
                    temperature=self._config.llm_temperature if self._config else 0.6,
                    stop=["<|end|>", "<|endoftext|>", "<|user|>", "<|system|>"],
                )
            return response["choices"][0]["text"].strip()
        except Exception as exc:
            log.error("Phase2.generate_response error: %s", exc)
            return ""

    def generate_grounding_protocol(
        self,
        astronaut_name: str = "Commander",
        stress_pct: float = 75.0,
    ) -> str:
        """
        Generate a structured audio-guided 4-7-8 breathing and sensory grounding script.
        """
        return (
            f"{astronaut_name}, I am initiating an immediate grounding cycle. "
            f"Rest your shoulders back and close your eyes. "
            f"Inhale slowly through your nose for four seconds: one, two, three, four. "
            f"Hold your breath gently for seven seconds: one, two, three, four, five, six, seven. "
            f"Now exhale completely through your mouth for eight seconds: one, two, three, four, five, six, seven, eight. "
            f"Your vitals are monitored and secure. You are in full control."
        )

    def speak(self, text: str) -> bytes:
        """
        Synthesise text with Piper TTS and return raw WAV bytes.

        Returns:
            WAV bytes (16-bit PCM, mono, 22050 Hz for lessac-medium), or b'' on failure.
        """
        if self._piper is None:
            log.debug("Phase2.speak: Piper not loaded — returning b''")
            return b""

        try:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wav_file:
                self._piper.synthesize_wav(text, wav_file)
            return buf.getvalue()
        except Exception as exc:
            log.error("Phase2.speak error: %s", exc)
            return b""


def get_evolved_presets(
    chat_history: Optional[list] = None,
    cur_emotion: str = "neutral",
    stress_pct: float = 0.0,
    mission_phase: str = "LEO Operations",
) -> list[tuple[str, str]]:
    """
    Returns 2 permanent core presets + 3-4 context-adaptive dynamic presets
    that evolve based on astronaut responses, conversation keywords, and affective telemetry.
    """
    # ── 1. Core Permanent Presets (Always Preserved) ─────────────────────────
    core_presets = [
        ("🧘 4-7-8 Grounding", "Guide me through a 4-7-8 sensory grounding exercise."),
        ("📊 Full Telemetry Check", "Assess my current fatigue and stress telemetry across all sensors."),
    ]

    # ── 2. Scan Conversation Context for Keyword Triggers ────────────────────
    last_text = ""
    if chat_history:
        for turn in reversed(chat_history):
            content = turn.get("content", "")
            if content:
                last_text = (last_text + " " + content.lower()).strip()
                if len(last_text) > 400:
                    break

    emo = str(cur_emotion).lower()
    stress = float(stress_pct)

    dynamic_pool: list[tuple[str, str]] = []

    # Telemetry-based priorities
    if stress >= 65.0 or emo in ("fear", "panic"):
        dynamic_pool.append(("🫁 Box Breathing (4-4-4-4)", "Initiate acute stress reduction with 4x4 box breathing."))
        dynamic_pool.append(("🧊 Cold Sensory Anchor", "Guide me through tactical sensory cold anchoring to suppress tachycardia."))
    elif emo == "angry":
        dynamic_pool.append(("🛑 Cognitive Defusion", "Assist with task prioritization and emotional reframing."))
        dynamic_pool.append(("📋 Task De-escalation", "Recommend operational pacing adjustments for current EVA tasks."))
    elif emo == "sad":
        dynamic_pool.append(("👨‍👩‍👧 Family Comms Status", "Check DTN ground uplink status for crew personal messages."))
        dynamic_pool.append(("🎵 Audio Soundscape", "Recommend psycho-acoustic countermeasure for mission isolation."))

    # Keyword context triggers
    if any(k in last_text for k in ("sleep", "insomnia", "tired", "rest", "circadian")):
        dynamic_pool.append(("💤 Sleep Reset Protocol", "Provide sleep and circadian rest guidance for spaceflight insomnia."))
        dynamic_pool.append(("👁️ Micro-sleep Guard", "Evaluate micro-sleep risks and provide active countermeasures."))

    if any(k in last_text for k in ("dock", "docking", "rendezvous", "orbit", "thruster", "alignment")):
        dynamic_pool.append(("🛰️ Docking Readiness Check", "Conduct cognitive focus check for orbital docking approach."))

    if any(k in last_text for k in ("headache", "nausea", "dizzy", "vomit", "sick", "sms")):
        dynamic_pool.append(("💊 Motion Sickness Relief", "Review non-pharmacological relief for Space Motion Sickness (SMS)."))

    if any(k in last_text for k in ("eva", "suit", "airlock", "spacewalk", "glove", "pressure")):
        dynamic_pool.append(("👨‍🚀 EVA Cognitive Brief", "Review pre-EVA psychological checklist and sensory grounding."))

    if any(k in last_text for k in ("co2", "hypercapnia", "carbon", "dioxide", "air", "suffocat", "ventilation", "scrubber")):
        dynamic_pool.append(("🫁 Hypercapnia Breathing Protocol", "Guide me through slow exhalations to counteract elevated cabin CO2 anxiety."))

    if any(k in last_text for k in ("checklist", "procedure", "error", "mistake", "fog", "confus", "overwhelm", "task")):
        dynamic_pool.append(("🧠 Cognitive De-clutter", "Help me break down complex flight procedures and clear operational cognitive fog."))

    if any(k in last_text for k in ("alone", "isolate", "miss", "home", "family", "lonely", "earth")):
        dynamic_pool.append(("🌍 Earth Connection Anchor", "Guide me through positive psychological grounding for deep-space mission isolation."))

    # Nominal fallback presets
    fallback_pool = [
        ("🚀 Docking Stress", "I'm feeling high anxiety during this docking phase."),
        ("💤 Sleep Reset", "Provide sleep and circadian rest guidance for spaceflight insomnia."),
        ("🎯 60s Focus Primer", "Guide me through a 60-second operational focus and presence check."),
        ("📈 Routine Crew Brief", "Summarize overall crew cognitive readiness and mission status."),
    ]

    for item in fallback_pool:
        if len(dynamic_pool) >= 4:
            break
        if item not in dynamic_pool and item not in core_presets:
            dynamic_pool.append(item)

    # Return 2 core + up to 4 dynamic presets
    return core_presets + dynamic_pool[:4]

