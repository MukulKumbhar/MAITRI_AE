import os

# ── TF / CUDA env flags (must be BEFORE any TF/ML import) ─────────────────
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"]  = "3"
os.environ["CUDA_VISIBLE_DEVICES"]  = "-1"

import queue
import threading
import time
import math
import av
import cv2
cv2.setNumThreads(1)
import numpy as np
import pandas as pd
from typing import Optional
import streamlit as st

from modules.mission_core import NativeWatchdog, NativeDTNOutbox, compile_native_dossier

MISSION_CATALOG = {
    "ISRO Gaganyaan (LEO)": 0.5,
    "Artemis Gateway (Lunar)": 2.4,
    "Mars Transit (Deep Space)": 420.0
}


# ── Pure-Python project modules (safe to import at startup) ───────────────
from modules.alert_module    import get_alert
from modules.database_module import get_logs, get_recent_trend, init_db, log_event
from modules.fusion_module   import FusionState, fuse
from modules.live_state      import LiveState
from modules.vitals_module   import compute_vitals_strain
# NOTE: face_module and eye_module are imported INSIDE MAITRIVideoProcessor
# to prevent TF/MediaPipe from loading at Streamlit startup (segfault fix).

# ── Phase 2 ASR tap (optional — zero impact on Phase 1 if absent) ─────────
try:
    from modules.asr_tap import asr_buffer as _asr_buffer
    _ASR_TAP_AVAILABLE = True
except Exception:
    _asr_buffer = None
    _ASR_TAP_AVAILABLE = False

# ── Phase 2 Backend (optional — zero impact on Phase 1 if absent) ─────────
try:
    from modules.phase2_core import Phase2Config, Phase2Manager
    _PHASE2_AVAILABLE = True
except Exception:
    Phase2Config = None
    Phase2Manager = None
    _PHASE2_AVAILABLE = False

# ── WebRTC ────────────────────────────────────────────────────────────────
try:
    from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
    import streamlit_webrtc.component as _st_webrtc_comp
    _WEBRTC_OK = True

    # ── Rock-Solid WebRTC Lifecycle & Worker Hardening ─────────────────────────
    # 0. Suppress aioice STUN retry crashes on dead/closed UDP transports
    try:
        import aioice.ice
        import aioice.stun
        _orig_stun_retry = getattr(aioice.stun.Transaction, "_Transaction__retry", None)
        if _orig_stun_retry:
            def _safe_stun_retry(self):
                try:
                    fut = getattr(self, "_Transaction__future", None)
                    if fut and fut.done():
                        return
                    proto = getattr(self, "_Transaction__protocol", None)
                    if proto:
                        tr = getattr(proto, "transport", None)
                        if tr is None or getattr(tr, "_sock", None) is None or (hasattr(tr, "is_closing") and tr.is_closing()):
                            return
                    _orig_stun_retry(self)
                except Exception:
                    pass
            aioice.stun.Transaction._Transaction__retry = _safe_stun_retry

        _orig_ice_send_stun = getattr(aioice.ice.StunProtocol, "send_stun", None)
        if _orig_ice_send_stun:
            def _safe_ice_send_stun(self, message, addr):
                if self.transport is None or getattr(self.transport, "_sock", None) is None or (hasattr(self.transport, "is_closing") and self.transport.is_closing()):
                    return
                try:
                    _orig_ice_send_stun(self, message, addr)
                except Exception:
                    pass
            aioice.ice.StunProtocol.send_stun = _safe_ice_send_stun
    except Exception:
        pass

    # 1. Prevent aiortc from aborting stream on transient ICE "disconnected" / "failed" states
    #    (e.g., 5s STUN consent check timeouts under CPU load or firewall NAT).
    try:
        from aiortc import RTCPeerConnection
        _orig_listens_to = RTCPeerConnection.listens_to
        def _hardened_listens_to(self, event: str):
            decorator = _orig_listens_to(self, event)
            if event == "iceconnectionstatechange":
                def wrapped_decorator(handler):
                    async def wrapped_handler(*args, **kwargs):
                        state = getattr(self, "iceConnectionState", None)
                        if state in ("disconnected", "failed"):
                            return  # Suppress transient ICE disconnects; keep stream running
                        return await handler(*args, **kwargs)
                    return decorator(wrapped_handler)
                return wrapped_decorator
            return decorator
        RTCPeerConnection.listens_to = _hardened_listens_to
    except Exception:
        pass

    # 2. Prevent worker from being garbage-collected during active sessions
    _orig_set_worker = _st_webrtc_comp.WebRtcStreamerContext._set_worker
    def _hardened_set_worker(self, worker):
        self._strong_worker = worker  # Prevent GC reaping
        _orig_set_worker(self, worker)
    _st_webrtc_comp.WebRtcStreamerContext._set_worker = _hardened_set_worker

    # 3. Guard _reset_context from killing an active connected peer connection
    _orig_reset_context = _st_webrtc_comp._reset_context
    def _hardened_reset_context(context):
        worker = context._get_worker() if hasattr(context, "_get_worker") else None
        pc = getattr(worker, "pc", None)
        if (
            worker
            and pc
            and pc.connectionState == "connected"
            and not getattr(context, "_user_stopped", False)
        ):
            context._set_state(_st_webrtc_comp.WebRtcStreamerState(playing=True, signalling=False))
            return
        _orig_reset_context(context)
    _st_webrtc_comp._reset_context = _hardened_reset_context

    # 4. Prevent Streamlit reruns / fragments from wiping the WebRTC component value
    def _hardened_restore_snapshot(context, component_value):
        session_info = _st_webrtc_comp.get_this_session_info()
        run_count = _st_webrtc_comp.get_script_run_count(session_info) if session_info else 0
        worker = context._get_worker() if hasattr(context, "_get_worker") else None
        pc = getattr(worker, "pc", None)
        pc_connected = (
            worker is not None
            and pc is not None
            and getattr(pc, "connectionState", None) in ("connected", "connecting")
        )

        if component_value is not None:
            if component_value.get("playing") is False:
                context._user_stopped = True
                context._last_valid_component_value = None
            elif component_value.get("playing") is True:
                context._user_stopped = False
                context._last_valid_component_value = component_value

        if (component_value is None or not component_value.get("playing")) and not getattr(context, "_user_stopped", False):
            cached = getattr(context, "_last_valid_component_value", None)
            if cached is not None and (pc_connected or getattr(context.state, "playing", False)):
                component_value = cached

        if run_count is not None:
            context._component_value_snapshot = _st_webrtc_comp.ComponentValueSnapshot(
                component_value=component_value, run_count=run_count
            )
        return component_value
    _st_webrtc_comp._restore_snapshot_if_needed = _hardened_restore_snapshot

    # 5. Prevent orphan context cleanup from killing an active streaming session
    _orig_get_or_create_context = _st_webrtc_comp._get_or_create_context
    def _hardened_get_or_create_context(key: str):
        if key in st.session_state:
            ctx = st.session_state[key]
            worker = ctx._get_worker() if hasattr(ctx, "_get_worker") else None
            pc = getattr(worker, "pc", None)
            is_active = (
                (worker is not None and pc is not None and getattr(pc, "connectionState", None) not in ("closed", "failed"))
                or getattr(ctx.state, "playing", False)
                or getattr(ctx.state, "signalling", False)
            )
            if is_active:
                sinfo = _st_webrtc_comp.get_this_session_info()
                rc = _st_webrtc_comp.get_script_run_count(sinfo) if sinfo else None
                if rc is not None:
                    ctx._last_rendered_run_count = rc
        return _orig_get_or_create_context(key)
    _st_webrtc_comp._get_or_create_context = _hardened_get_or_create_context

except ImportError:
    _WEBRTC_OK = False

# ── DB init ───────────────────────────────────────────────────────────────
init_db()

# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Project MAITRI 2.0",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.4rem !important; }
.stress-badge {
    display: inline-block; padding: 5px 14px;
    border-radius: 20px; font-weight: bold;
    font-size: 1rem; color: white;
}
.emo-row { display:flex; align-items:center; gap:8px; margin:3px 0; }
.emo-label { width:72px; font-size:0.82rem; text-transform:capitalize; }
.emo-bar-bg { flex:1; background:#2d2d2d; border-radius:6px; height:16px; }
.emo-bar { border-radius:6px; height:16px; transition:width 0.5s; }
.emo-pct { width:44px; font-size:0.82rem; text-align:right; }
</style>
""", unsafe_allow_html=True)

# ── Standard Emotion Color Map (Matches HUD and Charts) ───────────────────
EMO_COLORS = {
    "angry": "#e74c3c", "disgust": "#27ae60", "fear": "#9b59b6",
    "happy": "#f1c40f", "neutral": "#95a5a6", "sad": "#3498db",
    "surprise": "#e67e22",
}

# ─────────────────────────────────────────────────────────────────────────
# SESSION STATE INIT & THREAD-SAFE REFERENCES
# ─────────────────────────────────────────────────────────────────────────

if "native_watchdog" not in st.session_state:
    st.session_state.native_watchdog = NativeWatchdog()
if "native_dtn" not in st.session_state:
    st.session_state.native_dtn = NativeDTNOutbox()
if "active_mission" not in st.session_state:
    st.session_state.active_mission = "ISRO Gaganyaan (LEO)"
if "active_crew" not in st.session_state:
    st.session_state.active_crew = "Cdr. A. Sharma (Pilot / CMO)"
if "dossier_md" not in st.session_state:
    st.session_state.dossier_md = None

# Phase 2 session state (lazy initialized, zero Phase 1 performance impact)
if "phase2_mgr" not in st.session_state:
    st.session_state.phase2_mgr = Phase2Manager() if (_PHASE2_AVAILABLE and Phase2Manager) else None
if "phase2_cfg" not in st.session_state:
    st.session_state.phase2_cfg = Phase2Config() if (_PHASE2_AVAILABLE and Phase2Config) else None
if "phase2_chat_history" not in st.session_state:
    st.session_state.phase2_chat_history = []
if "phase2_voice_tap_active" not in st.session_state:
    st.session_state.phase2_voice_tap_active = True

if "live_state"   not in st.session_state:
    st.session_state.live_state   = LiveState()
if "fusion_state" not in st.session_state:
    st.session_state.fusion_state = FusionState()
if "eye_state"    not in st.session_state:
    from modules.eye_module import EyeSessionState
    st.session_state.eye_state    = EyeSessionState()
if "voice_detector" not in st.session_state:
    from modules.voice_module import get_or_create_voice_detector
    st.session_state.voice_detector = get_or_create_voice_detector(st.session_state.live_state)

# Global references safe for background threads (aiortc workers cannot access st.session_state)
_ACTIVE_LIVE_STATE = st.session_state.live_state
_ACTIVE_EYE_STATE  = st.session_state.eye_state
_ACTIVE_VOICE_DETECTOR = st.session_state.voice_detector

# Eagerly pre-warm neural networks on page startup to eliminate the 1.7s initial video freeze
if "models_warmed" not in st.session_state:
    try:
        from modules.face_module import process_unified_frame, _get_onnx_session
        from modules.voice_module import _get_voice_onnx_session
        _get_onnx_session()
        _get_voice_onnx_session()
        _test_img_path = os.path.join(os.path.dirname(__file__), "tests", "test_face.jpg")
        if os.path.isfile(_test_img_path):
            _dummy = cv2.imread(_test_img_path)
        else:
            _dummy = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.rectangle(_dummy, (200, 100), (440, 380), (180, 180, 180), -1)
        process_unified_frame(_dummy, st.session_state.eye_state)
        st.session_state.models_warmed = True
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────────────────
# WEBRTC VIDEO PROCESSOR
# ─────────────────────────────────────────────────────────────────────────
_EYE_EVERY_N_FRAMES = 3   # kept for reference — eye worker throttles internally

class MAITRIVideoProcessor:
    """
    Processes WebRTC video frames with zero pipeline blocking.
    State is passed via constructor (safe for worker threads).

    High-Performance Unified Architecture (<1ms recv latency, ~30 FPS):
    - Unified background worker runs MediaPipe FaceLandmarker ONCE per cycle.
    - MediaPipe extracts both FACS blendshapes (AU12 smile, AU6 cheek squint)
      and 478 face landmarks for EAR and blink tracking simultaneously.
    - Deep EfficientNet ONNX inference runs on centered isotropic square face crops.
    - recv() NEVER blocks on ML: copy frame -> try_enqueue -> draw aerospace HUD -> return.
    - Single-slot queue drops stale frames under heavy system load to prevent any latency buildup.
    """

    def __init__(self, live_state: LiveState, eye_state):
        self.live_state = live_state
        self.eye_state  = eye_state
        self._running   = True

        # Single-slot queue — drops frames when background worker is busy (zero lag)
        self._inference_queue: queue.Queue = queue.Queue(maxsize=1)

        # Smooth reticle tracking filter state
        self._display_box: Optional[dict] = None

        # Unified background worker
        self._worker = threading.Thread(
            target=self._unified_inference_worker, daemon=True, name="maitri-unified-worker"
        )
        self._worker.start()

    def stop(self) -> None:
        self._running = False
        try:
            self._inference_queue.put_nowait(None)
        except Exception:
            pass

    def __del__(self) -> None:
        self.stop()

    # ── Background Unified Worker ─────────────────────────────────────────
    def _unified_inference_worker(self) -> None:
        from modules.face_module import process_unified_frame
        while self._running:
            try:
                bgr = self._inference_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if bgr is None or not self._running:
                break
            t_start = time.perf_counter()
            try:
                face_res, eye_res = process_unified_frame(bgr, self.eye_state)
                ls = self.live_state
                with ls.lock:
                    if face_res is not None:
                        ls.face_emotion    = face_res.dominant_emotion
                        ls.emotion_probs   = {
                            k: float(v) / 100.0 for k, v in face_res.emotion_probs.items()
                        }
                        ls.face_confidence = face_res.face_confidence
                        ls.face_quality    = face_res.face_quality
                        ls.face_error      = face_res.error
                        ls.blur_score      = face_res.blur_score
                        ls.is_blurry       = face_res.is_blurry
                        ls.face_box        = face_res.face_box

                    if eye_res is not None:
                        ls.ear            = eye_res.ear
                        ls.blink_rate     = eye_res.blink_rate
                        ls.fatigue_label  = eye_res.fatigue_label
                        ls.fatigue_strain = eye_res.fatigue_strain
                        ls.eye_quality    = eye_res.eye_quality
                        ls.eye_available  = eye_res.available
            except Exception as exc:
                print(f"[MAITRI] Unified worker error: {exc}")

            # Pace worker at ~30 FPS (yielding CPU if inference was faster than 33ms)
            # This completely prevents CPU thrashing and starves neither aiortc nor WebRTC video encoding
            elapsed = time.perf_counter() - t_start
            remain = 0.033 - elapsed
            if remain > 0.002:
                time.sleep(remain)

    # ── Per-frame recv callback — ZERO blocking (<1ms execution) ──────────
    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        """
        Called for EVERY incoming video frame by streamlit-webrtc.
        Returns immediately — ML inference runs asynchronously in background worker.
        Renders sleek aerospace HUD at locked 30 FPS with pure sub-millisecond execution.
        """
        try:
            bgr = frame.to_ndarray(format="bgr24")
            ls  = self.live_state

            ls.frame_count += 1

            # Dispatch freshest frame to worker without blocking or queue accumulation
            if self._inference_queue.full():
                try:
                    self._inference_queue.get_nowait()
                except queue.Empty:
                    pass
            try:
                self._inference_queue.put_nowait(bgr.copy())
            except queue.Full:
                pass

            # Smooth reticle filtering: eliminates discrete coordinate steps and jumping
            snap = ls.snapshot_face_nonblocking() if hasattr(ls, "snapshot_face_nonblocking") else ls.snapshot_face()
            raw_box = snap.get("face_box")
            display_box = None
            if raw_box is not None:
                rx, ry = float(raw_box["x"]), float(raw_box["y"])
                rw, rh = float(raw_box["w"]), float(raw_box["h"])
                if self._display_box is None:
                    self._display_box = {"x": rx, "y": ry, "w": rw, "h": rh}
                else:
                    dx = rx - self._display_box["x"]
                    dy = ry - self._display_box["y"]
                    dist = math.hypot(dx, dy)
                    # Adaptive alpha: fast tracking on head movement, stabilization on micro-jitter
                    alpha = 0.85 if dist > 25.0 else (0.65 if dist > 6.0 else 0.40)
                    self._display_box["x"] += alpha * dx
                    self._display_box["y"] += alpha * dy
                    self._display_box["w"] += 0.50 * (rw - self._display_box["w"])
                    self._display_box["h"] += 0.50 * (rh - self._display_box["h"])

                display_box = {
                    "x": int(round(self._display_box["x"])),
                    "y": int(round(self._display_box["y"])),
                    "w": int(round(self._display_box["w"])),
                    "h": int(round(self._display_box["h"])),
                }
            else:
                self._display_box = None

            # Draw sleek aerospace glass HUD using latest cached telemetry
            try:
                bgr = _draw_aerospace_hud(bgr, ls, display_box=display_box)
            except Exception:
                pass

            return av.VideoFrame.from_ndarray(bgr, format="bgr24")
        except Exception:
            return frame


def _make_video_processor() -> MAITRIVideoProcessor:
    """
    Thread-safe factory called by aiortc background worker threads.
    Uses module-level references because st.session_state is not accessible in worker threads.
    """
    global _ACTIVE_LIVE_STATE, _ACTIVE_EYE_STATE
    ls = _ACTIVE_LIVE_STATE
    es = _ACTIVE_EYE_STATE
    if ls is None:
        try:
            ls = st.session_state.live_state
        except Exception:
            ls = LiveState()
        _ACTIVE_LIVE_STATE = ls
    if es is None:
        try:
            es = st.session_state.eye_state
        except Exception:
            from modules.eye_module import EyeSessionState
            es = EyeSessionState()
        _ACTIVE_EYE_STATE = es
    return MAITRIVideoProcessor(ls, es)


class MAITRIAudioProcessor:
    """Passes audio frames from WebRTC directly to VoiceModule."""
    def __init__(self, voice_detector):
        self.voice_detector = voice_detector
        self.resampler = av.AudioResampler(format='flt', layout='mono', rate=16000)

    def recv(self, frame):
        if self.voice_detector is not None:
            try:
                # Use PyAV's native resampler which safely handles packed/planar/stereo
                resampled_frames = self.resampler.resample(frame)
                for r_frame in resampled_frames:
                    arr = r_frame.to_ndarray()
                    arr = arr.flatten()
                    # push_audio_chunk internally feeds both SER and the Phase 2 ASR tap once
                    self.voice_detector.push_audio_chunk(arr)
            except Exception:
                pass
        elif _ASR_TAP_AVAILABLE and _asr_buffer is not None and _asr_buffer.enabled:
            # voice_detector absent: still feed ASR tap if it is active
            try:
                resampled_frames = self.resampler.resample(frame)
                for r_frame in resampled_frames:
                    arr = r_frame.to_ndarray().flatten()
                    _asr_buffer.push(arr)
            except Exception:
                pass
        return frame

def _make_audio_processor() -> MAITRIAudioProcessor:
    global _ACTIVE_VOICE_DETECTOR
    vd = _ACTIVE_VOICE_DETECTOR
    if vd is None:
        try:
            vd = st.session_state.voice_detector
        except Exception:
            vd = None
        _ACTIVE_VOICE_DETECTOR = vd
    return MAITRIAudioProcessor(vd)


_HUD_BG_CACHE = {}
def _get_hud_bg_slice(slice_h: int, slice_w: int) -> np.ndarray:
    key = (slice_h, slice_w)
    arr = _HUD_BG_CACHE.get(key)
    if arr is None or arr.shape != (slice_h, slice_w, 3):
        arr = np.full((slice_h, slice_w, 3), (12, 16, 24), dtype=np.uint8)
        _HUD_BG_CACHE[key] = arr
    return arr


def _draw_aerospace_hud(bgr: np.ndarray, ls: LiveState, display_box: Optional[dict] = None) -> np.ndarray:
    snap = ls.snapshot()
    h, w = bgr.shape[:2]
    
    # Calculate responsive scale factor so text is always the same visual size 
    # regardless of WebRTC dynamically changing the webcam resolution.
    sf = h / 480.0
    
    # Emotion Colors (BGR)
    EMO_COLORS = {
        "happy":    (0,   255, 255), # Yellow
        "neutral":  (210, 210, 210), # Gray
        "surprise": (255, 255, 0),   # Cyan
        "sad":      (255, 100, 50),  # Blue
        "fear":     (210, 90,  210), # Purple
        "angry":    (0,   0,   255), # Red
        "disgust":  (0,   200, 0),   # Green
    }
    
    current_emo = snap.get('face_emotion', 'neutral').lower()
    emo_col = EMO_COLORS.get(current_emo, (0, 230, 118))
    
    # 1. Top and Bottom Banners
    top_h = int(38 * sf)
    bot_h = int(30 * sf)
    cv2.rectangle(bgr, (0, 0), (w, top_h), (20, 25, 30), -1)
    cv2.rectangle(bgr, (0, h - bot_h), (w, h), (20, 25, 30), -1)
    
    # 2. Face Box (Corner Brackets Reticle)
    box = display_box if display_box is not None else snap.get("face_box")
    if box:
        bx = int(box.get("x", 0))
        by = int(box.get("y", 0))
        bw = int(box.get("w", 0))
        bh = int(box.get("h", 0))
        if bw > 0 and bh > 0:
            thick = max(1, int(2 * sf))
            # Corner arm length (proportional to face box, minimum 14px)
            c_len = max(int(14 * sf), min(bw, bh) // 4)

            # 4 Corner brackets (Open center, no solid square)
            # Top-Left corner
            cv2.line(bgr, (bx, by), (bx + c_len, by), emo_col, thick)
            cv2.line(bgr, (bx, by), (bx, by + c_len), emo_col, thick)
            # Top-Right corner
            cv2.line(bgr, (bx + bw, by), (bx + bw - c_len, by), emo_col, thick)
            cv2.line(bgr, (bx + bw, by), (bx + bw, by + c_len), emo_col, thick)
            # Bottom-Left corner
            cv2.line(bgr, (bx, by + bh), (bx + c_len, by + bh), emo_col, thick)
            cv2.line(bgr, (bx, by + bh), (bx, by + bh - c_len), emo_col, thick)
            # Bottom-Right corner
            cv2.line(bgr, (bx + bw, by + bh), (bx + bw - c_len, by + bh), emo_col, thick)
            cv2.line(bgr, (bx + bw, by + bh), (bx + bw, by + bh - c_len), emo_col, thick)

            # Draw Face Label (kept exactly same color, font, scale, and positioning)
            lbl = f"{current_emo.upper()} {snap.get('face_confidence', 0)*100:.0f}%"
            lbl_y = max(by - int(8 * sf), top_h + int(16 * sf))
            cv2.putText(bgr, lbl, (bx, lbl_y), cv2.FONT_HERSHEY_SIMPLEX, 0.55 * sf, emo_col, max(1, int(2 * sf)), cv2.LINE_AA)
                        
    # 3. Top Banner Text
    lbl_top = f"● {current_emo.upper()} {snap.get('face_confidence',0)*100:.0f}%"
    cv2.putText(bgr, lbl_top, (int(14 * sf), int(27 * sf)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.62 * sf, emo_col, max(1, int(2 * sf)), cv2.LINE_AA)
    cv2.putText(bgr, f"FRAME #{snap.get('frame_count', 0)}", (w - int(140 * sf), int(26 * sf)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.44 * sf, (0, 165, 255), 1, cv2.LINE_AA)
                
    # 4. Bottom Banner Text
    bot_lbl = f"EAR: {snap.get('ear', 0.0):.2f}  BLINK: {snap.get('blink_rate', 0.0):.0f}/min  FATIGUE: {snap.get('fatigue_label', 'Normal').upper()}"
    cv2.putText(bgr, bot_lbl, (int(14 * sf), h - int(10 * sf)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.44 * sf, (0, 230, 118), 1, cv2.LINE_AA)
    cv2.putText(bgr, "MAITRI 2.0 // ASTRONAUT VISION", (w - int(240 * sf), h - int(10 * sf)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.40 * sf, (150, 165, 180), 1, cv2.LINE_AA)
                
    return bgr




# ─────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='text-align:center;margin-bottom:4px;'>🛰️ Project MAITRI 2.0</h1>"
    "<p style='text-align:center;color:#aaa;margin-top:0;font-size:0.9rem;'>"
    "Live Multimodal AI Astronaut Telemetry &amp; Psychological Monitoring</p>",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────
# GLOBAL ALERTS (Visible on all tabs)
# ─────────────────────────────────────────────────────────────────────────
if "native_watchdog" in st.session_state:
    wd_state = st.session_state.native_watchdog.state
    if wd_state == "CHECK_IN":
        st.warning("⚠️ **ASTRONAUT INACTIVITY DETECTED. SYSTEM CHECK-IN REQUIRED.**")
        if st.button("✅ Acknowledge Watchdog (Manual Override)", type="primary", use_container_width=True):
            st.session_state.native_watchdog.acknowledge()
            st.rerun()
    elif wd_state == "INCAPACITATED":
        st.error("🚨 **SYSTEM INCAPACITATION PROTOCOL ENGAGED.**")
        if st.button("🔄 Override & Reset System", type="primary", use_container_width=True):
            st.session_state.native_watchdog.acknowledge()
            st.rerun()


st.markdown("---")

def _render_dip_status(is_playing: bool):
    if is_playing:
        snap_v = st.session_state.live_state.snapshot()
        blur_status = (
            "<span style='color:#f39c12;'>⚠️ Motion Blur (Fusion Gated)</span>"
            if snap_v["is_blurry"]
            else f"<span style='color:#2ecc71;'>✅ Sharp ({snap_v['blur_score']:.0f})</span>"
        )
        st.markdown(
            f"<div style='background:#1b2838;padding:8px 12px;border-radius:6px;font-size:0.83rem;margin-top:6px;border:1px solid #2a475e;'>"
            f"🛡️ <b>Vision Pipeline:</b> Hybrid FACS (AU12/AU6) + EfficientNet ONNX (Isotropic Square Crop) &nbsp;|&nbsp; "
            f"<b>Clarity:</b> {blur_status}"
            f"</div>",
            unsafe_allow_html=True,
        )


@st.fragment(run_every=1.0)
def _render_live_voice_telemetry(is_playing: bool):
    ls = st.session_state.live_state
    ls_snap = ls.snapshot_voice() if hasattr(ls, "snapshot_voice") else ls.snapshot()
    rms_val = float(ls_snap.get("voice_rms", 0.0))
    is_spk  = bool(ls_snap.get("is_speaking", False))
    v_emo   = str(ls_snap.get("voice_emotion", "neutral")).lower()
    v_conf  = float(ls_snap.get("voice_confidence", 0.0))
    v_probs = dict(ls_snap.get("voice_probs", {}))

    # 1. Instant Voice Emotion Badge (matching face reticle aerospace style)
    if is_spk:
        theme_col = EMO_COLORS.get(v_emo, "#2ecc71")
        st.markdown(
            f"""
            <div style="background:{theme_col}18; border:2px solid {theme_col}; border-radius:10px; padding:10px 14px; display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
              <div>
                <div style="font-size:0.72rem; color:#8b9cb5; font-weight:700; text-transform:uppercase; letter-spacing:1px;">Instant Voice Emotion</div>
                <div style="font-size:1.35rem; font-weight:bold; color:{theme_col}; margin-top:2px;">🎙️ {v_emo.upper()} ({v_conf*100:.0f}%)</div>
              </div>
              <div style="text-align:right;">
                <span style="display:inline-block; padding:4px 10px; border-radius:12px; background:#13381e; color:#00e676; font-size:0.75rem; font-weight:600; border:1px solid #00e67655; box-shadow:0 0 8px #00e67644;">
                  🔊 ACTIVE
                </span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif v_conf > 0.0:
        # User spoke and paused: keep last detected emotion clearly displayed for side-by-side comparison
        theme_col = EMO_COLORS.get(v_emo, "#95a5a6")
        st.markdown(
            f"""
            <div style="background:{theme_col}12; border:2px solid {theme_col}aa; border-radius:10px; padding:10px 14px; display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
              <div>
                <div style="font-size:0.72rem; color:#8b9cb5; font-weight:700; text-transform:uppercase; letter-spacing:1px;">Instant Voice Emotion (Last Captured)</div>
                <div style="font-size:1.35rem; font-weight:bold; color:{theme_col}; margin-top:2px;">🎙️ {v_emo.upper()} ({v_conf*100:.0f}%)</div>
              </div>
              <div style="text-align:right;">
                <span style="display:inline-block; padding:4px 10px; border-radius:12px; background:#1e2638; color:#8b9cb5; font-size:0.75rem; font-weight:600; border:1px solid #33425b;">
                  🔇 STANDBY (GATE: 0%)
                </span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="background:#161d2b; border:2px solid #2a384c; border-radius:10px; padding:10px 14px; display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
              <div>
                <div style="font-size:0.72rem; color:#60718b; font-weight:700; text-transform:uppercase; letter-spacing:1px;">Instant Voice Emotion</div>
                <div style="font-size:1.35rem; font-weight:bold; color:#8b9cb5; margin-top:2px;">🔇 STANDBY (AWAITING SPEECH)</div>
              </div>
              <div style="text-align:right;">
                <span style="display:inline-block; padding:4px 10px; border-radius:12px; background:#1e2638; color:#78889e; font-size:0.75rem; font-weight:600; border:1px solid #33425b;">
                  GATE: 0%
                </span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Voice Emotion Distribution (7-Class SER)
    st.markdown("<div style='font-size:0.83rem;font-weight:600;margin-bottom:4px;'>Voice Emotion Distribution (7-Class SER)</div>", unsafe_allow_html=True)
    sorted_v = sorted(v_probs.items(), key=lambda x: x[1], reverse=True)
    for emo, prob in sorted_v:
        pct = round(prob * 100, 1)
        bar_w = max(pct, 1)
        bar_color = EMO_COLORS.get(emo, "#888")
        marker = " ◀" if (v_conf > 0.0 and emo == v_emo) else ""
        st.markdown(
            f"<div class='emo-row'>"
            f"<span class='emo-label'>{emo}</span>"
            f"<div class='emo-bar-bg'>"
            f"<div class='emo-bar' style='width:{bar_w}%;background:{bar_color};'></div>"
            f"</div>"
            f"<span class='emo-pct'>{pct:.1f}%{marker}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # 3. Live Hardware VU Meter
    if rms_val > 0.0005:
        eff_rms = min(1.0, max(0.0001, rms_val))
        db_val = max(-60.0, min(0.0, 20.0 * np.log10(eff_rms)))
        pct_val = int(max(2, min(100, ((db_val + 48.0) / 48.0) * 100)))
    else:
        db_val = -60.0
        pct_val = 2

    db_text = f"{db_val:.1f} dB" if db_val > -59.5 else "-∞ dB"

    if is_spk:
        badge_bg = "#13381e"
        badge_color = "#00e676"
        badge_dot = "#00e676"
        dot_glow = "0 0 8px #00e676"
        badge_label = "🔊 SPEECH ACTIVE (VAD OPEN)"
    else:
        badge_bg = "#161d2b"
        badge_color = "#8b9cb5"
        badge_dot = "#57677d"
        dot_glow = "none"
        badge_label = "🔇 SILENT / AMBIENT (0% WT)"

    st.progress(
        pct_val / 100.0,
        text=f"🎙️ Hardware Input Level: {db_text} ({pct_val}%)"
    )

    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:2px; font-size:0.75rem;">
          <span style="display:inline-flex; align-items:center; gap:6px; padding:3px 10px; border-radius:12px; background:{badge_bg}; color:{badge_color}; font-weight:600;">
            <span style="width:7px; height:7px; border-radius:50%; background:{badge_dot}; display:inline-block; box-shadow:{dot_glow};"></span>
            <span>{badge_label}</span>
          </span>
          <span style="color:#60718b; font-family:monospace; font-size:0.75rem;">
            RMS: {rms_val:.4f} | PipeWire 16kHz
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.fragment(run_every=1.0)
def _render_eye_panel(is_playing: bool):
    if is_playing:
        ls_snap = st.session_state.live_state.snapshot()
        e1, e2 = st.columns(2)
        e1.metric("EAR", f"{ls_snap['ear']:.3f}")
        e2.metric("Blink Rate", f"{ls_snap['blink_rate']:.1f} /min")
        eye_color = {
            "Normal": "#2ecc71", "Drowsy": "#e74c3c",
            "Stressed Eyes": "#e67e22", "Hyperfocused": "#f1c40f",
        }.get(ls_snap["fatigue_label"], "#aaa")
        st.markdown(
            f"<div style='margin-top:6px;'>"
            f"<span class='stress-badge' style='background:{eye_color};'>"
            f"👁️ {ls_snap['fatigue_label']}</span></div>",
            unsafe_allow_html=True,
        )
        st.caption(f"Frames processed: {ls_snap['frame_count']}")
    else:
        st.info("▶️ Start the camera stream to begin eye tracking.")


@st.fragment(run_every=1.0)
def _render_live_assessment(
    heart_rate: float,
    skin_temp: float,
    spo2: float,
    vitals_strain: float,
    is_playing: bool,
):
    ls_snap = st.session_state.live_state.snapshot()

    # Build fusion inputs from live state
    face_probs   = ls_snap["emotion_probs"] if is_playing else None
    face_quality = ls_snap["face_quality"]  if is_playing else 0.0
    face_emotion = ls_snap["face_emotion"]

    weight_mode = st.session_state.get("fusion_weight_mode_toggle", "🤖 Dynamic Quality-Aware")
    manual_mode = (weight_mode == "🎛️ Manual Override")
    manual_face_pct = st.session_state.get("manual_face_split_slider", 60)
    manual_face_ratio = manual_face_pct / 100.0


    # -- Watchdog Logic (Background Update Only) --
    st.session_state.native_watchdog.update(
        is_speaking=ls_snap.get("is_speaking", False),
        ear=ls_snap.get("ear", 0.0),
        face_quality=ls_snap.get("face_quality", 0.0)
    )
            
    fusion = fuse(

        state             = st.session_state.fusion_state,
        face_probs        = face_probs,
        face_quality      = face_quality,
        vitals_strain     = vitals_strain,
        fatigue_strain    = ls_snap["fatigue_strain"],
        eye_quality       = ls_snap["eye_quality"] if is_playing else 0.0,
        voice_probs       = ls_snap["voice_probs"],
        voice_quality     = ls_snap["voice_quality"],
        is_speaking       = ls_snap["is_speaking"],
        manual_override   = manual_mode,
        manual_face_ratio = manual_face_ratio,
    )

    # ── Metrics strip (5 Modalities & Stress) ─────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Face Weight",    f"{fusion.face_weight*100:.0f}%")
    m2.metric("Voice Weight",   f"{fusion.voice_weight*100:.0f}%")
    m3.metric("Vitals Weight",  f"{fusion.vitals_weight*100:.0f}%")
    m4.metric("Eye Weight",     f"{fusion.eye_weight*100:.0f}%")
    m5.metric("🎯 Stress Index", f"{fusion.stress_pct:.1f}%")

    emo_col, gauge_col = st.columns([1.2, 1.0], gap="large")

    with emo_col:
        st.markdown("**Fused Emotion Distribution**")
        sorted_emos = sorted(fusion.fused_probs.items(), key=lambda x: x[1], reverse=True)
        for emo, prob in sorted_emos:
            pct       = round(prob * 100, 1)
            bar_w     = max(pct, 1)
            bar_color = EMO_COLORS.get(emo, "#888")
            marker    = " ◀" if emo == fusion.dominant_emotion else ""
            st.markdown(
                f"<div class='emo-row'>"
                f"<span class='emo-label'>{emo}</span>"
                f"<div class='emo-bar-bg'>"
                f"<div class='emo-bar' style='width:{bar_w}%;background:{bar_color};'></div>"
                f"</div>"
                f"<span class='emo-pct'>{pct:.1f}%{marker}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    with gauge_col:
        alert = get_alert(fusion.stress_pct, fusion.dominant_emotion, ls_snap.get("fatigue_label", "Normal"))
        st.markdown("**Stress Level**")
        st.markdown(
            f"<div style='text-align:center;padding:12px;border-radius:12px;"
            f"background:{alert.color}22;border:2px solid {alert.color};'>"
            f"<div style='font-size:2.6rem;'>{alert.icon}</div>"
            f"<div class='stress-badge' style='background:{alert.color};font-size:1.1rem;'>"
            f"{alert.stress_level}</div>"
            f"<div style='font-size:2rem;font-weight:bold;margin:6px 0;'>"
            f"{fusion.stress_pct:.1f}%</div>"
            f"<div style='font-size:0.8rem;color:#ccc;'>Combined Stress Index</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        emo_color = EMO_COLORS.get(fusion.dominant_emotion, "#888")
        st.markdown(
            f"<div style='text-align:center;margin-top:8px;'>"
            f"<span class='stress-badge' style='background:{emo_color};'>"
            f"Emotion: {fusion.dominant_emotion.capitalize()}</span></div>",
            unsafe_allow_html=True,
        )

    # ── ROW 3: Support Response ───────────────────────────────────────────
    st.markdown("---")
    st.subheader("🤖 Autonomous Psychological Support")

    resp_col, cbt_col = st.columns([1.0, 1.2], gap="medium")
    alert_style = (
        f"background:{alert.color}18;border-left:4px solid {alert.color};"
        f"padding:14px;border-radius:8px;"
    )
    with resp_col:
        st.markdown(
            f"<div style='{alert_style}'><strong>{alert.icon} {alert.header}</strong>"
            f"<br><br>{alert.body}</div>",
            unsafe_allow_html=True,
        )

    with cbt_col:
        if alert.technique:
            st.markdown(
                f"<div style='background:#1a1a2e;padding:14px;border-radius:8px;"
                f"border:1px solid #444;'>"
                f"{alert.technique.replace(chr(10), '<br>')}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='background:#1a3a1a;padding:14px;border-radius:8px;"
                "border:1px solid #2ecc71;color:#2ecc71;'>"
                "✅ No intervention required. Astronaut is performing optimally.</div>",
                unsafe_allow_html=True,
            )

    # Cache latest fusion for mission logging
    st.session_state["latest_fusion"] = fusion
    st.session_state["latest_alert"] = alert
    st.session_state["latest_face_emotion"] = face_emotion

    if is_playing:
        st.caption("⚡ Real-time Telemetry: Live assessment & support engine updating dynamically (1 Hz).")


# ─────────────────────────────────────────────────────────────────────────
# AUTONOMOUS VOICE WAKEUP & HANDS-FREE TAB SWITCHING DIRECTOR
# ─────────────────────────────────────────────────────────────────────────
@st.fragment(run_every=0.75)
def _autonomous_voice_listener():
    """Lightweight 0.75s polling fragment: wakes up main Streamlit execution when background speech is ready."""
    if _ASR_TAP_AVAILABLE and _asr_buffer is not None:
        if _asr_buffer.has_transcript():
            st.rerun()

_autonomous_voice_listener()

# Global Audio Autoplay: Plays synthesized AI voice response through cabin speakers
# regardless of which tab the astronaut is currently looking at.
if st.session_state.get("pending_global_audio"):
    st.audio(st.session_state["pending_global_audio"], format="audio/wav", autoplay=True)
    st.session_state["pending_global_audio"] = None

# Root-level autonomous speech event consumer: processes voice commands and conversational queries
if _ASR_TAP_AVAILABLE and _asr_buffer is not None:
    auto_event = _asr_buffer.pop_transcript()
    if auto_event:
        if auto_event.get("is_command"):
            t_idx = auto_event.get("tab_index")
            t_name = auto_event.get("tab_name")
            act = auto_event.get("action")
            if t_idx is not None:
                st.session_state.target_tab_idx = t_idx
                st.toast(f"🎙️ Voice Director: Switched to {t_name}", icon="🚀")
                st.rerun()
            elif act == "log_reading":
                snap_log = st.session_state.live_state.snapshot()
                latest_f = st.session_state.get("latest_fusion")
                latest_a = st.session_state.get("latest_alert")
                face_emo = st.session_state.get("latest_face_emotion", snap_log.get("face_emotion", "neutral"))
                fused_emo = latest_f.dominant_emotion if latest_f else face_emo
                stress_sc = latest_f.stress_pct if latest_f else 0.0
                stress_lv = latest_a.stress_level if latest_a else "NOMINAL"
                alert_lbl = latest_a.alert_label if latest_a else "NOMINAL"
                resp_body = latest_a.body if latest_a else "Telemetry nominal."
                cur_probs = latest_f.fused_probs if (latest_f and hasattr(latest_f, "fused_probs")) else snap_log.get("emotion_probs")
                log_event(
                    face_emotion=face_emo,
                    fused_emotion=fused_emo,
                    voice_state=f"{snap_log.get('voice_emotion', 'neutral').capitalize()} ({'Speaking' if snap_log.get('is_speaking') else 'Silent'})",
                    heart_rate=float(st.session_state.get("live_hr_slider", 75)),
                    temperature=float(st.session_state.get("live_temp_slider", 36.6)),
                    spo2=float(st.session_state.get("live_spo2_slider", 98.0)),
                    blink_rate=float(snap_log.get("blink_rate", 14.0)),
                    fatigue_label=snap_log.get("fatigue_label", "Normal"),
                    stress_score=stress_sc,
                    stress_level=stress_lv,
                    alert_triggered=alert_lbl,
                    response_msg=resp_body,
                    emotion_probs=cur_probs,
                )
                st.toast("💾 Voice Command: Mission telemetry logged to database!", icon="✅")
                st.session_state["last_logged_time"] = time.time()
                st.rerun()
        else:
            # Autonomous conversational speech detected: pass to psychological support engine
            spoken_txt = auto_event.get("text")
            if spoken_txt:
                st.session_state["pending_voice_query"] = spoken_txt
                st.toast(f"🗣️ Astronaut Voice Received: \"{spoken_txt}\"", icon="🎙️")

# Astronaut Ergonomics Study: Solutions for Busy-Hands Operation
with st.expander("🛰️ **Astronaut Hands-Free Navigation: Solutions Study & Voice Director** (Click to view)", expanded=False):
    st.markdown("""
### 👨‍🚀 Spaceflight Hands-Free Navigation: Ergonomic Analysis & Architecture

In microgravity operations, astronauts' hands are frequently engaged (gripping handrails during high-g thrust, handling fragile payload experiments, operating secondary physical levers, or wearing bulky pressurized EVA gloves). Traditional manual GUI clicking creates cognitive and motor friction. Below is our complete ergonomic study and 5 integrated solutions:

1. **🎙️ Primary: Autonomous Voice Navigation ("Voice Cockpit Director")**
   - *Technical Mechanism*: Sub-second silence-boundary ASR continuously parses incoming speech for navigation triggers. Phrases like `"switch to logs"`, `"open live feed"`, `"go to psychological support"`, or `"tab 1 / 2 / 3 / 4"` execute tab transitions immediately.
   - *Advantage*: Zero physical touch required; fully operable inside pressurized EVA helmets or while both hands grip handrails.

2. **⚡ Secondary: Autonomous Telemetry-Driven View Focusing (Priority Override)**
   - *Technical Mechanism*: When acute distress is detected (stress index >65% or acute fear/panic), the system automatically shifts focus to Tab 4 (AI Psychological Support) and presents guided grounding audio without waiting for astronaut input.
   - *Advantage*: Rapid crisis intervention during cognitive overload when the astronaut cannot self-advocate.

3. **🖥️ Tertiary: Single-Pane "Heads-Up Cockpit" Mode (Zero Tab Switching)**
   - *Technical Mechanism*: Consolidates real-time webcam FER, eye-tracking PERCLOS, instant psychological status, and mission telemetry into a single non-paginated pane, eliminating the cognitive burden of tab context-switching.

4. **👁️ Quaternary: Ocular Gaze-Dwell & Intentional Blink Navigation**
   - *Technical Mechanism*: Leverages the integrated MediaPipe iris tracking pipeline. Sustained gaze dwell (>1.5s) or intentional triple-blinks cycle views silently.
   - *Advantage*: Operable during high acoustic noise or comms silence.

5. **🦶 Quinary: Foot-Pedal & 1-Key Tactile Hotkeys**
   - *Technical Mechanism*: Single-touch tactile bindings (Keys `1`, `2`, `3`, `4`) mapped via direct DOM keyboard events.
   - *Advantage*: Minimal motor movement, zero cursor tracking required.
""")

# Hotkey and JavaScript Tab Switcher Component with retry resilience
import streamlit.components.v1 as _components

target_tab_js = ""
if "target_tab_idx" in st.session_state and st.session_state.target_tab_idx is not None:
    t_idx = int(st.session_state.target_tab_idx)
    target_tab_js = f"""
    let switchAttempts = 0;
    function executeTabSwitch() {{
        try {{
            const doc = window.parent.document;
            const tabs = doc.querySelectorAll('button[data-baseweb="tab"]');
            if (tabs && tabs[{t_idx}]) {{
                tabs[{t_idx}].click();
            }} else if (switchAttempts < 12) {{
                switchAttempts++;
                setTimeout(executeTabSwitch, 40);
            }}
        }} catch (e) {{}}
    }}
    executeTabSwitch();
    """
    st.session_state.target_tab_idx = None

_components.html(f"""
<script>
function attachTabHandlers() {{
    try {{
        const doc = window.parent.document;
        {target_tab_js}
        // Keyboard Hotkey Listener: Keys 1, 2, 3, 4 switch tabs
        if (!doc._maitri_tab_hotkeys_attached) {{
            doc._maitri_tab_hotkeys_attached = true;
            doc.addEventListener('keydown', (e) => {{
                if (['1', '2', '3', '4'].includes(e.key) && !['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {{
                    const idx = parseInt(e.key) - 1;
                    const tabs = doc.querySelectorAll('button[data-baseweb="tab"]');
                    if (tabs && tabs[idx]) {{
                        tabs[idx].click();
                    }}
                }}
            }});
        }}
    }} catch (err) {{}}
}}
setTimeout(attachTabHandlers, 50);
</script>
""", height=0, width=0)

# Quick Voice & Tactile Navigation Strip
col_nav1, col_nav2, col_nav3, col_nav4 = st.columns(4)
with col_nav1:
    if st.button("🔴 [1] Live Cockpit", use_container_width=True, key="quick_nav_tab_1"):
        st.session_state.target_tab_idx = 0
        st.rerun()
with col_nav2:
    if st.button("📊 [2] Telemetry Logs", use_container_width=True, key="quick_nav_tab_2"):
        st.session_state.target_tab_idx = 1
        st.rerun()
with col_nav3:
    if st.button("🎬 [3] Mission Control", use_container_width=True, key="quick_nav_tab_3"):
        st.session_state.target_tab_idx = 2
        st.rerun()
with col_nav4:
    if st.button("🧠 [4] Psychological Support", use_container_width=True, key="quick_nav_tab_4"):
        st.session_state.target_tab_idx = 3
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────
tab_live, tab_logs, tab_demo, tab_support = st.tabs([
    "🔴 Live Monitoring",
    "📊 Mission Logs & Trends",
    "🎬 Demo & Mission Control",
    "🧠 AI Psychological Support",
])

# ═════════════════════════════════════════════════════════════════════════
# TAB 1 — LIVE MONITORING
# ═════════════════════════════════════════════════════════════════════════
with tab_live:

    if not _WEBRTC_OK:
        st.error(
            "**streamlit-webrtc not installed.** Run:\n"
            "```\n/home/mikey/anaconda3/envs/maitri/bin/pip install streamlit-webrtc aiortc\n```"
        )
        st.stop()

    # ── ROW 1: Side-by-Side Comparison (Live Video + Voice Telemetry) ────
    col_webcam, col_voice = st.columns([1.1, 1.0], gap="medium")

    with col_webcam:
        st.subheader("📹 Live Astronaut Feed & Face FER")
        st.caption("Background ML pipeline · MediaPipe Eye Tracking (~10 FPS)")

        rtc_config = RTCConfiguration(
            {
                "iceServers": [
                    {
                        "urls": [
                            "stun:stun.l.google.com:19302",
                            "stun:stun1.l.google.com:19302",
                            "stun:stun2.l.google.com:19302",
                        ]
                    }
                ]
            }
        )

        # ── Prevent Streamlit fragments from desyncing WebRTC run counters ──
        if "maitri-live" in st.session_state:
            _rtc_ctx = st.session_state["maitri-live"]
            try:
                from streamlit_webrtc.component import (
                    get_this_session_info,
                    get_script_run_count,
                    ComponentValueSnapshot,
                )
                _sinfo = get_this_session_info()
                if _sinfo:
                    _rc = get_script_run_count(_sinfo)
                    if _rc is not None:
                        if _rtc_ctx._last_rendered_run_count is not None:
                            _rtc_ctx._last_rendered_run_count = _rc - 1
                        if getattr(_rtc_ctx, "_component_value_snapshot", None) is not None:
                            _rtc_ctx._component_value_snapshot = ComponentValueSnapshot(
                                component_value=_rtc_ctx._component_value_snapshot.component_value,
                                run_count=_rc - 1,
                            )
            except Exception:
                pass

        # Refresh thread-safe references before WebRTC worker initialization
        _ACTIVE_LIVE_STATE = st.session_state.live_state
        _ACTIVE_EYE_STATE  = st.session_state.eye_state
        _ACTIVE_VOICE_DETECTOR = st.session_state.voice_detector

        use_webrtc_audio = st.checkbox(
            "🎙️ Enable Browser Microphone for WebRTC",
            value=False,
            help="Keep unchecked to prevent hardware mic conflicts. Enable only if your browser microphone is ready."
        )

        # Direct synchronous WebRTC video pipeline (<1ms recv latency, locked 30 FPS, zero queue buffering delay)
        ctx = webrtc_streamer(
            key="maitri-live",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=rtc_config,
            video_processor_factory=_make_video_processor,
            audio_processor_factory=_make_audio_processor if use_webrtc_audio else None,
            media_stream_constraints={
                "video": {
                    "width": {"ideal": 640, "max": 640},
                    "height": {"ideal": 480, "max": 480},
                    "frameRate": {"ideal": 30, "max": 30},
                },
                "audio": use_webrtc_audio,
            },
            async_processing=False,
        )

        _render_dip_status(ctx.state.playing)

    with col_voice:
        st.subheader("🎙️ Voice Emotion & Acoustic Telemetry")
        st.caption("Quantized Wav2Vec2 ONNX (16 kHz) · Hardware Ballistic VU")

        _render_live_voice_telemetry(ctx.state.playing)

        st.markdown("---")
        # Fusion Weighting Control toggle
        weight_mode = st.radio(
            "Fusion Weighting Control",
            ["🤖 Dynamic Quality-Aware", "🎛️ Manual Override"],
            horizontal=True,
            key="fusion_weight_mode_toggle",
        )
        if weight_mode == "🎛️ Manual Override":
            manual_face_pct = st.slider(
                "Behavioral Split (Face vs Voice)",
                min_value=0, max_value=100, value=60, step=5,
                format="%d%% Face",
                key="manual_face_split_slider",
                help="Adjust balance between visual facial expressions and vocal acoustics. Default: 60% Face / 40% Voice."
            )
            st.caption(f"Manual Ratio: **{manual_face_pct}% Face / {100 - manual_face_pct}% Voice** (VAD silence-gated)")
        else:
            st.caption("⚡ **Autonomous Quality-Aware Engine**: Auto-balances 60/40 nominal ratio based on real-time face lighting & microphone VAD.")

        # Microphone Sensitivity & Calibration expander
        with st.expander("🎛️ Microphone Sensitivity & Calibration", expanded=False):
            vd = st.session_state.get("voice_detector")
            current_gain = getattr(vd, "gain", 1.0) if vd else 1.0
            current_thresh = getattr(vd, "silence_threshold", 0.030) if vd else 0.030
            new_gain = st.slider("Mic Digital Pre-Gain", 0.5, 3.0, float(current_gain), 0.1, key="mic_gain_slider")
            new_thresh = st.slider("Silence Gate Threshold", 0.005, 0.080, float(current_thresh), 0.005, format="%.3f", key="mic_thresh_slider")
            if vd:
                vd.gain = new_gain
                vd.silence_threshold = new_thresh

    # ── ROW 2: Biological Telemetry & Eye Tracking ────────────────────────
    st.markdown("---")
    st.subheader("💓 Biological Telemetry & Eye Tracking")

    col_vitals, col_eye = st.columns([1.1, 1.0], gap="medium")
    with col_vitals:
        st.markdown("**Physiological Sensors**")
        st.caption("Adjust sliders to reflect sensor readings")

        heart_rate = st.slider("❤️  Heart Rate (BPM)",      50,  160, 75, key="live_hr_slider")
        skin_temp  = st.slider("🌡️  Skin Temperature (°C)", 35.0, 40.0, 36.6, step=0.1, key="live_temp_slider")
        spo2       = st.slider("🫁  Blood Oxygen (SpO₂ %)", 85,  100, 98, key="live_spo2_slider")

        vitals = compute_vitals_strain(heart_rate, skin_temp, float(spo2))

        v1, v2, v3 = st.columns(3)
        v1.metric("HR Strain",   f"{vitals.hr_strain*100:.0f}%")
        v2.metric("Temp Strain", f"{vitals.temp_strain*100:.0f}%")
        v3.metric("SpO₂ Strain", f"{vitals.spo2_strain*100:.0f}%")

        vitals_color = {"Normal": "#2ecc71", "Elevated": "#e67e22", "Critical": "#e74c3c"}.get(
            vitals.status, "#aaa"
        )
        st.markdown(
            f"<div style='margin-top:6px;'>"
            f"<span class='stress-badge' style='background:{vitals_color};'>"
            f"Vitals: {vitals.status}</span></div>",
            unsafe_allow_html=True,
        )

    with col_eye:
        st.markdown("**Eye Tracking & Fatigue**")
        st.caption("MediaPipe 478-Landmark Eye Geometry")
        _render_eye_panel(ctx.state.playing)

    # ── ROW 3: Live Multimodal Stress Assessment & Psychological Support ──
    st.markdown("---")
    st.subheader("🧠 Live Multimodal Stress Assessment & Psychological Support")

    _render_live_assessment(
        heart_rate=heart_rate,
        skin_temp=skin_temp,
        spo2=spo2,
        vitals_strain=vitals.vitals_strain,
        is_playing=ctx.state.playing,
    )

    # ── Mission Telemetry Logging (Manual & Cadence Auto-Logger) ────────────
    st.markdown("---")
    log_col1, log_col2 = st.columns([1.2, 2.0])
    with log_col1:
        if st.button("💾 Log Reading to Mission Database", width="stretch"):
            snap_log = st.session_state.live_state.snapshot()
            latest_f = st.session_state.get("latest_fusion")
            latest_a = st.session_state.get("latest_alert")
            face_emo = st.session_state.get("latest_face_emotion", snap_log["face_emotion"])
            fused_emo = latest_f.dominant_emotion if latest_f else face_emo
            stress_sc = latest_f.stress_pct if latest_f else 0.0
            stress_lv = latest_a.stress_level if latest_a else "NORMAL"
            alert_lbl = latest_a.alert_label if latest_a else "NOMINAL"
            resp_body = latest_a.body if latest_a else "Telemetry nominal."
            cur_probs = latest_f.fused_probs if (latest_f and hasattr(latest_f, "fused_probs")) else snap_log.get("emotion_probs")

            log_event(
                face_emotion    = face_emo,
                fused_emotion   = fused_emo,
                voice_state     = f"{snap_log['voice_emotion'].capitalize()} ({'Speaking' if snap_log['is_speaking'] else 'Silent'})",
                heart_rate      = float(heart_rate),
                temperature     = float(skin_temp),
                spo2            = float(spo2),
                blink_rate      = snap_log["blink_rate"],
                fatigue_label   = snap_log["fatigue_label"],
                stress_score    = stress_sc,
                stress_level    = stress_lv,
                alert_triggered = alert_lbl,
                response_msg    = resp_body,
                emotion_probs   = cur_probs,
            )
            st.session_state["last_logged_time"] = time.time()
            st.success("✅ Mission telemetry logged to database.")

    with log_col2:
        auto_log_enabled = st.checkbox(
            "🔄 Auto-Log Telemetry to Database (Every 6s while active)",
            value=st.session_state.get("auto_log_active", True),
            key="autolog_cadence_toggle",
            help="Continuously saves 7-emotion affect distribution and biological vitals into SQLite for hands-free mission logging."
        )
        st.session_state.auto_log_active = auto_log_enabled
        if auto_log_enabled and ctx.state.playing:
            now_t = time.time()
            if now_t - st.session_state.get("_last_autolog_time", 0) >= 6.0:
                st.session_state["_last_autolog_time"] = now_t
                snap_log = st.session_state.live_state.snapshot()
                latest_f = st.session_state.get("latest_fusion")
                latest_a = st.session_state.get("latest_alert")
                face_emo = st.session_state.get("latest_face_emotion", snap_log.get("face_emotion", "neutral"))
                fused_emo = latest_f.dominant_emotion if latest_f else face_emo
                stress_sc = latest_f.stress_pct if latest_f else 0.0
                stress_lv = latest_a.stress_level if latest_a else "NOMINAL"
                alert_lbl = latest_a.alert_label if latest_a else "NOMINAL"
                resp_body = latest_a.body if latest_a else "Telemetry nominal."
                cur_probs = latest_f.fused_probs if (latest_f and hasattr(latest_f, "fused_probs")) else snap_log.get("emotion_probs")
                log_event(
                    face_emotion    = face_emo,
                    fused_emotion   = fused_emo,
                    voice_state     = f"{snap_log.get('voice_emotion', 'neutral').capitalize()} ({'Speaking' if snap_log.get('is_speaking') else 'Silent'})",
                    heart_rate      = float(heart_rate),
                    temperature     = float(skin_temp),
                    spo2            = float(spo2),
                    blink_rate      = snap_log.get("blink_rate", 14.0),
                    fatigue_label   = snap_log.get("fatigue_label", "Normal"),
                    stress_score    = stress_sc,
                    stress_level    = stress_lv,
                    alert_triggered = alert_lbl,
                    response_msg    = resp_body,
                    emotion_probs   = cur_probs,
                )

# ═════════════════════════════════════════════════════════════════════════
# TAB 2 — MISSION LOGS
# ═════════════════════════════════════════════════════════════════════════
with tab_logs:
    st.subheader("📋 Mission Telemetry History")

    log_df = get_logs()
    if log_df.empty:
        st.info("No telemetry logs yet. Start the camera stream or click '💾 Log Reading' in the Live tab.")
    else:
        trend_df = get_recent_trend(60)
        if not trend_df.empty:
            st.markdown("### 📈 Multi-Dimensional Emotion Confidence Trajectory (7 Affect Dimensions)")
            st.caption("Continuous line graph tracking all 7 emotion probabilities over time. Colors strictly match webcam HUD color codes.")

            # Reshape for Altair
            emo_keys = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
            col_map = {f"prob_{e}": e for e in emo_keys}
            available_cols = [c for c in col_map if c in trend_df.columns]

            if available_cols and len(trend_df) > 0:
                plot_df = trend_df[["timestamp"] + available_cols].copy()
                plot_df = plot_df.rename(columns=col_map)
                time_series = pd.to_datetime(plot_df["timestamp"], errors="coerce")
                plot_df["Time"] = time_series.dt.strftime("%H:%M:%S").fillna(plot_df["timestamp"].astype(str))
                melted = plot_df.melt(id_vars=["timestamp", "Time"], var_name="Emotion", value_name="Confidence")
                melted["Confidence (%)"] = (melted["Confidence"] * 100.0).round(1)

                domain = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
                range_colors = [EMO_COLORS.get(e, "#888") for e in domain]

                try:
                    import altair as alt
                    chart = (
                        alt.Chart(melted)
                        .mark_line(strokeWidth=2.4, point=alt.OverlayMarkDef(size=28, filled=True))
                        .encode(
                            x=alt.X("Time:N", title="Mission Time (HH:MM:SS)", axis=alt.Axis(labelAngle=-30, labelOverlap="parity")),
                            y=alt.Y("Confidence (%):Q", title="Probability / Confidence (%)", scale=alt.Scale(domain=[0, 100])),
                            color=alt.Color(
                                "Emotion:N",
                                scale=alt.Scale(domain=domain, range=range_colors),
                                legend=alt.Legend(title="Affect Dimension", orient="top", columns=4)
                            ),
                            tooltip=["Time:N", "Emotion:N", "Confidence (%):Q", "timestamp:N"]
                        )
                        .properties(height=340)
                        .interactive()
                    )
                    st.altair_chart(chart, use_container_width=True)
                except Exception as chart_err:
                    st.line_chart(plot_df.set_index("Time")[domain])

                # Emotion switching & confidence metrics
                met_c1, met_c2, met_c3, met_c4 = st.columns(4)
                if "fused_emotion" in trend_df.columns:
                    dom_series = trend_df["fused_emotion"].astype(str).str.lower()
                    switches = max(0, int((dom_series != dom_series.shift()).sum() - 1))
                    cur_dom = str(trend_df["fused_emotion"].iloc[-1]).lower()
                else:
                    switches = 0
                    cur_dom = "neutral"

                met_c1.metric("Dominant Affect", cur_dom.upper())
                met_c2.metric("Affect Switches", f"{switches} events", help="Frequency of dominant emotion transitions across logged readings.")
                peak_conf = melted["Confidence (%)"].max() if not melted.empty else 0.0
                met_c3.metric("Peak Confidence", f"{peak_conf:.1f}%")
                avg_stress = trend_df["stress_score"].mean() if "stress_score" in trend_df.columns else 0.0
                met_c4.metric("Mean Stress", f"{avg_stress:.1f}%")

        if not trend_df.empty and "stress_score" in trend_df.columns:
            st.markdown("**Combined Stress Index Trend (last 60 readings)**")
            st.line_chart(trend_df.set_index("timestamp")["stress_score"], color="#e74c3c")

        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Readings", len(log_df))
        c2.metric("Avg Stress",     f"{log_df['stress_score'].mean():.1f}%")
        c3.metric("Peak Stress",    f"{log_df['stress_score'].max():.1f}%")
        c4.metric("Critical Alerts",
                  len(log_df[log_df["stress_level"] == "CRITICAL"])
                  if "stress_level" in log_df.columns else "–")

        st.markdown("---")
        st.markdown("**Full Telemetry Log**")
        st.dataframe(log_df, width="stretch", height=380)

        if "fused_emotion" in log_df.columns:
            st.markdown("**Emotion Distribution**")
            st.bar_chart(log_df["fused_emotion"].value_counts())

        # ── Psychological Support Session History ──
        st.markdown("---")
        st.markdown("**🧠 In-Flight AI Psychological Support Dialogue History**")
        try:
            from modules.database_module import get_psych_logs
            psych_df = get_psych_logs(50)
            if psych_df.empty:
                st.caption("No psychological dialogues recorded yet. Interactions from Tab 4 will appear here.")
            else:
                st.dataframe(psych_df, width="stretch", height=240)
        except Exception as e:
            st.caption(f"Psychological session table status: {e}")

# ═════════════════════════════════════════════════════════════════════════
# TAB 3 — DEMO & MISSION CONTROL
# ═════════════════════════════════════════════════════════════════════════
with tab_demo:
    st.subheader("🎬 Presentation Demo Scenarios")
    st.info("Trigger these during presentations to demonstrate autonomous safety systems without waiting 45 seconds.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⚡ Simulate Watchdog Check-In", use_container_width=True):
            st.session_state.native_watchdog.trigger_simulation()
            st.rerun()
            st.success("Watchdog manually triggered. Switch to Live Telemetry to view.")
            
        if st.button("📄 Force Compile Medical Dossier", use_container_width=True):
            f_state = st.session_state.fusion_state
            stress = f_state.last_stress if f_state else 0.0
            st.session_state.dossier_md = compile_native_dossier(
                st.session_state.active_crew, st.session_state.active_mission,
                float(st.session_state.get("live_hr_slider", 75)), float(st.session_state.get("live_spo2_slider", 98)), stress
            )
            st.session_state.native_dtn.dispatch("AUDIT-101", "PRIORITY-1", "Manual Flight Surgeon Audit")
            st.success("Dossier compiled successfully.")
            
    with col2:
        missions = list(MISSION_CATALOG.keys())
        idx = missions.index(st.session_state.active_mission)
        sel_m = st.selectbox("🚀 Select Mission Profile", missions, index=idx)
        if sel_m != st.session_state.active_mission:
            st.session_state.active_mission = sel_m
            st.session_state.native_dtn.set_mission(sel_m, MISSION_CATALOG[sel_m])
            st.rerun()
            
        st.session_state.active_crew = st.selectbox("👨‍🚀 Active Astronaut", [
            "Cdr. A. Sharma (Pilot / CMO)", "Lt. Cdr. P. Nair (Flight Engineer)", "Dr. V. Rao (Mission Specialist)"
        ])
        
    st.markdown("---")
    st.subheader("📡 Ground DTN Outbox")
    st.markdown(f"**Current Propagation Delay:** {st.session_state.native_dtn.format_latency()}")
    for pkt in st.session_state.native_dtn.packets:
        st.warning(f"**{pkt.packet_id}** | {pkt.priority} | {pkt.status}\n\n{pkt.summary}")
        
    if st.session_state.dossier_md:
        st.markdown("### 📄 Compiled Clinical Dossier")
        st.download_button("📥 Download Dossier (.md)", st.session_state.dossier_md, "Medical_Dossier.md", "text/markdown")
        with st.expander("Preview Dossier", expanded=True):
            st.markdown(st.session_state.dossier_md)


# ═════════════════════════════════════════════════════════════════════════
# TAB 4 — AI PSYCHOLOGICAL SUPPORT (PHASE 2)
# ═════════════════════════════════════════════════════════════════════════
with tab_support:
    st.subheader("🧠 Autonomous In-Flight Psychological Support")
    st.caption("Offline Multimodal Conversational Intervention · Phi-3-Mini (3.8B) · Whisper ASR · Piper ONNX TTS")

    if not _PHASE2_AVAILABLE:
        st.error("Phase 2 backend module (`modules/phase2_core.py`) is unavailable. Please verify dependencies.")
    else:
        mgr = st.session_state.phase2_mgr
        cfg = st.session_state.phase2_cfg

        # ── Model Engine Status & Lazy Loader ────────────────────────────────
        st.markdown("---")
        c_status, c_ctrl = st.columns([2, 1])
        with c_status:
            if mgr and mgr.is_loaded:
                st.success("🟢 AI Support Engine Online — Whisper ASR, Phi-3 LLM, & Piper TTS Ready", icon="✅")
            else:
                st.info("💤 Models are currently idle to conserve CPU/RAM during telemetry monitoring.", icon="ℹ️")

        with c_ctrl:
            if mgr and not mgr.is_loaded:
                if st.button("⚡ Initialize Support Engine", type="primary", use_container_width=True):
                    with st.spinner("Loading offline neural models (Whisper, Phi-3-Mini, Piper)..."):
                        mgr.load_models(cfg)
                    st.rerun()
            elif mgr and mgr.is_loaded:
                st.caption("⚡ Offline Neural Engine Loaded")

        # ── Real-Time Affective Context Pill ─────────────────────────────────
        snap_p2 = st.session_state.live_state.snapshot()
        latest_f = st.session_state.get("latest_fusion")
        cur_emo = latest_f.dominant_emotion if latest_f else snap_p2.get("face_emotion", "neutral")
        cur_stress = latest_f.stress_pct if latest_f else getattr(st.session_state.fusion_state, "last_stress", 0.0)

        st.markdown(
            f"<div style='background:#131c2e;padding:10px 16px;border-radius:8px;border:1px solid #1f3354;margin:12px 0;font-size:0.9rem;'>"
            f"🛰️ <b>Telemetry Stream Injected to Clinical AI:</b> &nbsp; "
            f"Affect: <b style='color:#00e676;'>{str(cur_emo).upper()}</b> &nbsp;|&nbsp; "
            f"Stress Index: <b style='color:#ffab00;'>{float(cur_stress):.1f}%</b> &nbsp;|&nbsp; "
            f"Astronaut: <b>{st.session_state.active_crew}</b> &nbsp;|&nbsp; "
            f"Mission: <b>{st.session_state.active_mission}</b>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # ── Proactive Grounding Intervention Alert Banner ────────────────────
        if float(cur_stress) >= 65.0 or str(cur_emo).lower() in ("fear", "angry", "sad"):
            st.warning(
                f"🚨 **ELEVATED STRESS TELEMETRY DETECTED ({float(cur_stress):.1f}% · {str(cur_emo).upper()})** — "
                "Onboard clinical protocols recommend immediate grounding or cognitive defusion.",
                icon="⚠️"
            )
            col_em1, _ = st.columns([1.5, 1.0])
            with col_em1:
                if st.button("🧘 Launch Immediate 4-7-8 Guided Grounding Audio Protocol", type="primary", use_container_width=True):
                    if not mgr.is_loaded:
                        with st.spinner("Initializing neural engine..."):
                            mgr.load_models(cfg)
                    g_script = mgr.generate_grounding_protocol(st.session_state.active_crew, float(cur_stress))
                    with st.spinner("Synthesizing audio countermeasure (Piper ONNX)..."):
                        g_wav = mgr.speak(g_script)
                    if g_wav:
                        st.session_state["pending_global_audio"] = g_wav
                    st.session_state.phase2_chat_history.append({"role": "user", "content": "Requesting immediate grounding countermeasure."})
                    st.session_state.phase2_chat_history.append({
                        "role": "assistant",
                        "content": g_script,
                        "audio": g_wav if g_wav else None,
                        "autoplay": True if g_wav else False,
                    })
                    try:
                        from modules.database_module import log_psych_event
                        log_psych_event(
                            crew_member=st.session_state.active_crew,
                            mission_phase=st.session_state.active_mission,
                            input_channel="preset:grounding",
                            astronaut_query="Requesting immediate grounding countermeasure.",
                            detected_emotion=str(cur_emo),
                            stress_pct=float(cur_stress),
                            ai_response=g_script,
                            has_audio=bool(g_wav),
                        )
                    except Exception:
                        pass
                    st.rerun()

        st.markdown("---")

        # ── 1. Voice Interaction (Astronaut Talks) ───────────────────────────
        st.markdown("### 🎙️ Astronaut Voice Channel (Primary)")
        st.caption("Live hands-free speech recognition with ultra-sensitive acoustic detection (picks up distant / quiet murmurs) and silence-boundary auto-trigger.")

        user_query = None
        input_channel = "voice"

        # Check for autonomous spoken queries dispatched from top-level listener
        if st.session_state.get("pending_voice_query"):
            user_query = st.session_state.pop("pending_voice_query")
            input_channel = "voice (autonomous_live_vad)"
            st.success(f"🗣️ Autonomous Live Voice: *\"{user_query}\"*")

        # Live Acoustic Sensitivity & VAD Telemetry Badge
        if _ASR_TAP_AVAILABLE and _asr_buffer is not None:
            tel = _asr_buffer.get_telemetry()
            spk_badge = "🟢 SPEECH DETECTED (VAD ACTIVE)" if tel.get("in_speech") else "⚪ STANDBY / LISTENING"
            st.markdown(
                f"<div style='background:#101a2d;border:1px solid #1f3050;border-radius:6px;padding:6px 14px;margin:8px 0;font-size:0.8rem;display:flex;justify-content:space-between;align-items:center;'>"
                f"<span>🎙️ <b>Acoustic Sensitivity:</b> <span style='color:#00e676;'>HIGH</span> (Distant / Low-Volume Mode)</span>"
                f"<span><b>VAD State:</b> <b>{spk_badge}</b></span>"
                f"<span><b>Signal RMS:</b> <code>{tel.get('rms', 0.0):.4f}</code> (Floor: <code>{tel.get('noise_floor', 0.0):.4f}</code>)</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        col_vrec, col_vbuf = st.columns([1.1, 1.0], gap="medium")
        with col_vrec:
            st.markdown("##### 🎤 Direct Voice Dispatch")
            audio_rec = st.audio_input("Record voice dispatch", key="astronaut_voice_recorder", label_visibility="collapsed")
            if audio_rec is not None:
                rec_bytes = audio_rec.getvalue()
                curr_bytes_hash = hash(rec_bytes)
                last_bytes_hash = st.session_state.get("_last_audio_rec_hash")
                if curr_bytes_hash != last_bytes_hash:
                    st.session_state["_last_audio_rec_hash"] = curr_bytes_hash
                    if not (mgr and mgr.is_loaded):
                        with st.spinner("Initializing models..."):
                            mgr.load_models(cfg)
                    with st.spinner("Whisper transcribing recorded voice..."):
                        t_text = mgr.transcribe(rec_bytes)
                    if t_text.strip():
                        user_query = t_text.strip()
                        input_channel = "voice (audio_input)"
                        st.success(f"🗣️ Transcribed Voice: *\"{user_query}\"*")
                    else:
                        st.warning("No intelligible speech recognized in audio clip.")

        with col_vbuf:
            st.markdown("##### 📻 Live Telemetry Mic Stream Tap")
            tap_enabled = st.checkbox(
                "🎙️ Enable Continuous Stream Tap (Live Autonomous VAD)",
                value=st.session_state.get("phase2_voice_tap_active", True),
                help="When active, microphone frames from Tab 1 are routed to the Whisper speech buffer with silence-boundary detection."
            )
            st.session_state.phase2_voice_tap_active = tap_enabled
            if _ASR_TAP_AVAILABLE and _asr_buffer is not None:
                _asr_buffer.set_enabled(tap_enabled)
                pending_s = _asr_buffer.pending_samples / 16000.0
                st.markdown(f"**Queued Buffer:** `{pending_s:.1f}s` &nbsp; *(Autonomous VAD active · no button click needed)*")

            is_ready = bool(mgr and mgr.is_loaded)
            if st.button("🗣️ Transcribe Live Mic Buffer (Manual Override)", use_container_width=True, disabled=not is_ready):
                if _ASR_TAP_AVAILABLE and _asr_buffer is not None:
                    batch = _asr_buffer.drain()
                    if batch is not None and len(batch) >= 12000:
                        with st.spinner("Whisper transcribing buffer..."):
                            transcribed_text = mgr.transcribe(batch)
                        if transcribed_text.strip():
                            user_query = transcribed_text.strip()
                            input_channel = "voice (continuous_tap)"
                            st.success(f"🗣️ Transcribed Voice: *\"{user_query}\"*")
                        else:
                            st.warning("No words detected in audio buffer.")
                    else:
                        st.warning("Microphone buffer has insufficient speech audio. Speak into the mic first.")

        # ── 2. Text Input (Astronaut Types Option) ───────────────────────────
        typed_msg = st.chat_input("💬 Or type your message to MAITRI if not speaking...")
        if typed_msg:
            user_query = typed_msg
            input_channel = "text"

        # ── 3. Chat History & Conversation Stream ────────────────────────────
        st.markdown("---")
        c_head, c_clear = st.columns([3, 1])
        with c_head:
            st.markdown("### 💬 Clinical Dialogue")
        with c_clear:
            if st.session_state.phase2_chat_history:
                if st.button("🗑️ Clear History", use_container_width=True):
                    st.session_state.phase2_chat_history = []
                    st.rerun()

        if not st.session_state.phase2_chat_history:
            st.info("No conversation logged yet. Speak into the mic or type a message to begin.")

        for msg in st.session_state.phase2_chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("audio"):
                    is_new = msg.get("autoplay", False)
                    st.audio(msg["audio"], format="audio/wav", autoplay=is_new)
                    msg["autoplay"] = False

        # ── 4. Process Incoming Query (LLM Reasoning + Piper TTS) ────────────
        if user_query and mgr:
            if not mgr.is_loaded:
                with st.spinner("Initializing models..."):
                    mgr.load_models(cfg)

            # Record and display user message
            st.session_state.phase2_chat_history.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)

            # Generate empathetic response using Phi-3 with live clinical context
            with st.chat_message("assistant"):
                with st.spinner("MAITRI clinical reasoning in progress..."):
                    vitals_str = f"HR: {float(st.session_state.get('live_hr_slider', 75)):.0f} BPM, SpO2: {float(st.session_state.get('live_spo2_slider', 98)):.0f}%, Fatigue: {snap_p2.get('fatigue_label', 'Normal')}"
                    ai_reply = mgr.generate_response(
                        user_text=user_query,
                        emotion=str(cur_emo),
                        stress_pct=float(cur_stress),
                        astronaut_name=st.session_state.active_crew,
                        mission_phase=st.session_state.active_mission,
                        vitals_summary=vitals_str,
                        chat_history=st.session_state.phase2_chat_history,
                    )
                    if not ai_reply:
                        ai_reply = f"{st.session_state.active_crew}, telemetry acknowledged. I am monitoring your physiological state. Please take a slow, deep breath."
                    st.markdown(ai_reply)

                # Synthesize calm voice response via Piper TTS
                with st.spinner("Synthesizing voice response (Piper ONNX)..."):
                    wav_data = mgr.speak(ai_reply)

            # Save assistant response to state with autoplay flag and global audio cue
            if wav_data:
                st.session_state["pending_global_audio"] = wav_data
            st.session_state.phase2_chat_history.append({
                "role": "assistant",
                "content": ai_reply,
                "audio": wav_data if wav_data else None,
                "autoplay": True if wav_data else False,
            })

            # Log to SQLite database
            try:
                from modules.database_module import log_psych_event
                log_psych_event(
                    crew_member=st.session_state.active_crew,
                    mission_phase=st.session_state.active_mission,
                    input_channel=input_channel,
                    astronaut_query=user_query,
                    detected_emotion=str(cur_emo),
                    stress_pct=float(cur_stress),
                    ai_response=ai_reply,
                    has_audio=bool(wav_data),
                )
            except Exception:
                pass

            st.rerun()

        # ── 5. Quick Clinical Interventions Presets (Dynamically Evolving) ───
        st.markdown("---")
        st.markdown("###### ⚡ Clinical Guidance Presets (Contextually Evolving)")
        st.caption("Core grounding & assessment presets are permanently anchored; dynamic slots evolve according to conversational responses and affective telemetry.")

        try:
            from modules.phase2_core import get_evolved_presets
            evolved_presets = get_evolved_presets(
                chat_history=st.session_state.phase2_chat_history,
                cur_emotion=str(cur_emo),
                stress_pct=float(cur_stress),
                mission_phase=st.session_state.active_mission,
            )
        except Exception:
            evolved_presets = [
                ("🧘 4-7-8 Grounding", "Guide me through a 4-7-8 sensory grounding exercise."),
                ("📊 Full Assessment", "Assess my current fatigue and stress telemetry across all sensors."),
                ("🚀 Docking Stress", "I'm feeling high anxiety during this docking phase."),
                ("💤 Sleep Reset", "Provide sleep and circadian rest guidance for spaceflight insomnia."),
            ]

        pr_cols = st.columns(3)
        for p_idx, (p_label, p_text) in enumerate(evolved_presets):
            with pr_cols[p_idx % 3]:
                if st.button(p_label, key=f"quick_preset_{p_idx}_{hash(p_label)}", use_container_width=True):
                    if not (mgr and mgr.is_loaded):
                        with st.spinner("Initializing models..."):
                            mgr.load_models(cfg)
                    st.session_state.phase2_chat_history.append({"role": "user", "content": p_text})
                    with st.spinner("MAITRI clinical reasoning..."):
                        vitals_str = f"HR: {float(st.session_state.get('live_hr_slider', 75)):.0f} BPM, SpO2: {float(st.session_state.get('live_spo2_slider', 98)):.0f}%, Fatigue: {snap_p2.get('fatigue_label', 'Normal')}"
                        p_rep = mgr.generate_response(
                            p_text,
                            emotion=str(cur_emo),
                            stress_pct=float(cur_stress),
                            astronaut_name=st.session_state.active_crew,
                            mission_phase=st.session_state.active_mission,
                            vitals_summary=vitals_str,
                            chat_history=st.session_state.phase2_chat_history,
                        )
                        p_wav = mgr.speak(p_rep)
                    if p_wav:
                        st.session_state["pending_global_audio"] = p_wav
                    st.session_state.phase2_chat_history.append({
                        "role": "assistant",
                        "content": p_rep,
                        "audio": p_wav if p_wav else None,
                        "autoplay": True if p_wav else False,
                    })
                    try:
                        from modules.database_module import log_psych_event
                        log_psych_event(
                            crew_member=st.session_state.active_crew,
                            mission_phase=st.session_state.active_mission,
                            input_channel=f"preset:{p_label}",
                            astronaut_query=p_text,
                            detected_emotion=str(cur_emo),
                            stress_pct=float(cur_stress),
                            ai_response=p_rep,
                            has_audio=bool(p_wav),
                        )
                    except Exception:
                        pass
                    st.rerun()
