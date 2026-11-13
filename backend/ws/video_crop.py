"""
MAITRI 2.0 — Video Crop WebSocket Handler
/ws/video-crop

One-way (mostly):
  Client → Server: Binary JPEG bytes of cropped face patch (at 6 FPS)
  Server → Client: JSON emotion inference result
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.state import get_state
from backend.services.vision_service import process_face_crop

logger = logging.getLogger("maitri.ws.video")
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/video-crop")
async def video_crop_ws(websocket: WebSocket):
    """
    WebSocket endpoint for receiving cropped face JPEG patches from the browser.
    Runs EfficientNet ONNX inference and returns emotion results.
    Updates LiveState so the telemetry broadcast loop picks up results.
    """
    await websocket.accept()
    state = get_state()
    logger.info("Video-crop WS connected")

    await websocket.send_text(json.dumps({
        "type": "video_crop_ws_ready",
        "face_model_ready": state.face_model_ready,
    }))

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message and message["bytes"] is not None:
                jpeg_bytes = message["bytes"]

                # Retrieve active FACS blendshape signals under lock
                with state.live.face_lock:
                    is_smiling = getattr(state.live, "is_smiling", False)
                    smile_score = getattr(state.live, "smile_score", 0.0)
                    blendshapes = getattr(state.live, "blendshapes", None)

                # Run EfficientNet ONNX inference with FACS action unit fusion
                result = process_face_crop(
                    jpeg_bytes,
                    is_smiling=is_smiling,
                    smile_score=smile_score,
                    blendshapes=blendshapes,
                )

                if result:
                    # Update shared LiveState with inference results
                    with state.live.face_lock:
                        state.live.face_emotion = result["emotion"]
                        state.live.emotion_probs = result["probs"]
                        state.live.face_confidence = result["confidence"]
                        state.live.face_quality = result["quality"]
                        state.live.frame_count += 1

                    # Return result to client (support both type names for client compatibility)
                    await websocket.send_text(json.dumps({
                        "type": "face_inference",
                        "face_inference_result": True,
                        **result,
                    }))

            elif "text" in message and message["text"]:
                # JSON messages: EAR/eye data from browser MediaPipe
                try:
                    data = json.loads(message["text"])
                    await _handle_eye_data(data, state)
                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        logger.info("Video-crop WS disconnected")
        # Reset face quality on disconnect (no camera)
        with state.live.face_lock:
            state.live.face_quality = 0.0
            state.live.eye_available = False
    except Exception as exc:
        logger.warning("Video-crop WS error: %s", exc)


async def _handle_eye_data(data: dict, state) -> None:
    """
    Handle eye tracking JSON sent from the browser MediaPipe pipeline.
    Browser sends EAR, blink_rate, fatigue_label, blur_score, face_box.
    """
    msg_type = data.get("type", "")

    if msg_type == "eye_metrics":
        with state.live.face_lock:
            if "ear" in data:
                state.live.ear = float(data["ear"])
            if "blink_rate" in data:
                state.live.blink_rate = float(data["blink_rate"])
            if "fatigue_label" in data:
                state.live.fatigue_label = data["fatigue_label"]
            if "fatigue_strain" in data:
                state.live.fatigue_strain = float(data["fatigue_strain"])
            if "blur_score" in data:
                state.live.blur_score = float(data["blur_score"])
            if "is_blurry" in data:
                state.live.is_blurry = bool(data["is_blurry"])
            if "face_box" in data:
                state.live.face_box = data["face_box"]
            if "eye_available" in data:
                state.live.eye_available = bool(data["eye_available"])
            if "dip_active" in data:
                state.live.dip_active = bool(data["dip_active"])
            if "is_smiling" in data:
                state.live.is_smiling = bool(data["is_smiling"])
            if "smile_score" in data:
                state.live.smile_score = float(data["smile_score"])
            if "blendshapes" in data and isinstance(data["blendshapes"], dict):
                state.live.blendshapes = data["blendshapes"]

    elif msg_type == "blendshapes":
        with state.live.face_lock:
            state.live.is_smiling = bool(data.get("is_smiling", False))
            state.live.smile_score = float(data.get("smile_score", 0.0))
            if "blendshapes" in data and isinstance(data["blendshapes"], dict):
                state.live.blendshapes = data["blendshapes"]

    elif msg_type == "camera_status":
        with state.live.face_lock:
            available = bool(data.get("available", False))
            state.live.eye_available = available
            if not available:
                state.live.face_quality = 0.0
                state.live.ear = 0.30
