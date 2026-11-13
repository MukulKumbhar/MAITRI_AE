import { FilesetResolver, FaceLandmarker } from "@mediapipe/tasks-vision";

// Canonical MediaPipe 478 mesh indices for EAR calculation
const LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380];
const RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144];

export interface VisionMetrics {
  ear: number;
  blink_rate: number;
  fatigue_label: string;
  frame_count: number;
  face_detected: boolean;
  box: { x: number; y: number; width: number; height: number } | null;
  emotion_tag: string;
  confidence: number;
}

export class VisionPipeline {
  private landmarker: FaceLandmarker | null = null;
  private isLoaded: boolean = false;
  private cropSocket: WebSocket | null = null;
  private frameCount: number = 0;
  private lastCropTime: number = 0;
  private blinkTimes: number[] = [];
  private eyeClosed: boolean = false;

  public metrics: VisionMetrics = {
    ear: 0.28,
    blink_rate: 14.0,
    fatigue_label: "Normal",
    frame_count: 0,
    face_detected: false,
    box: null,
    emotion_tag: "NEUTRAL",
    confidence: 0.85,
  };

  public async init(): Promise<boolean> {
    try {
      this.initCropSocket();
      const vision = await FilesetResolver.forVisionTasks("/wasm");
      this.landmarker = await FaceLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: "/face_landmarker.task",
          delegate: "GPU",
        },
        outputFaceBlendshapes: true,
        runningMode: "VIDEO",
        numFaces: 1,
      });
      this.isLoaded = true;
      console.log("👁️ In-browser MediaPipe FaceLandmarker WASM initialized");
      return true;
    } catch (err) {
      console.warn("⚠️ MediaPipe GPU failed, trying CPU fallback:", err);
      try {
        const vision = await FilesetResolver.forVisionTasks("/wasm");
        this.landmarker = await FaceLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: "/face_landmarker.task",
            delegate: "CPU",
          },
          outputFaceBlendshapes: true,
          runningMode: "VIDEO",
          numFaces: 1,
        });
        this.isLoaded = true;
        return true;
      } catch (cpuErr) {
        console.error("❌ Failed to initialize MediaPipe FaceLandmarker:", cpuErr);
        return false;
      }
    }
  }

  private initCropSocket(): void {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    try {
      if (this.cropSocket && (this.cropSocket.readyState === WebSocket.OPEN || this.cropSocket.readyState === WebSocket.CONNECTING)) {
        return;
      }
      this.cropSocket = new WebSocket(`${protocol}//${host}/ws/video-crop`);
      this.cropSocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if ((data.type === "face_inference" || data.type === "face_inference_result") && data.emotion) {
            this.metrics.emotion_tag = data.emotion.toUpperCase();
            this.metrics.confidence = data.confidence || 0.85;
          }
        } catch (e) {}
      };
      this.cropSocket.onclose = () => {
        setTimeout(() => this.initCropSocket(), 3000);
      };
    } catch (e) {
      console.error("Crop WS error", e);
    }
  }

  public processVideoFrame(
    video: HTMLVideoElement,
    canvas: HTMLCanvasElement,
    currentEmotion = "NEUTRAL",
    currentConfidence = 0.85,
    emotionColor = "#2ecc71"
  ): VisionMetrics {
    this.frameCount++;
    this.metrics.frame_count = this.frameCount;
    this.metrics.emotion_tag = currentEmotion.toUpperCase();
    this.metrics.confidence = currentConfidence;

    const ctx = canvas.getContext("2d");
    if (!ctx) return this.metrics;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!this.isLoaded || !this.landmarker || video.readyState < 2) {
      // Draw minimal standby overlay
      this.drawStandbyHUD(ctx, canvas, emotionColor);
      return this.metrics;
    }

    try {
      const now = performance.now();
      const results = this.landmarker.detectForVideo(video, now);

      if (results.faceLandmarks && results.faceLandmarks.length > 0) {
        const landmarks = results.faceLandmarks[0];
        this.metrics.face_detected = true;

        // 1. Calculate EAR
        const leftEar = this.computeEAR(landmarks, LEFT_EYE_INDICES, canvas.width, canvas.height);
        const rightEar = this.computeEAR(landmarks, RIGHT_EYE_INDICES, canvas.width, canvas.height);
        const ear = (leftEar + rightEar) / 2.0;
        this.metrics.ear = Math.round(ear * 1000) / 1000;

        // 2. Blink Detection & Rate
        const tSec = Date.now() / 1000;
        if (ear < 0.20 && !this.eyeClosed) {
          this.eyeClosed = true;
          this.blinkTimes.push(tSec);
        } else if (ear >= 0.23) {
          this.eyeClosed = false;
        }

        // Keep blinks within 60s
        this.blinkTimes = this.blinkTimes.filter((t) => tSec - t <= 60.0);
        this.metrics.blink_rate = this.blinkTimes.length;

        // 3. Fatigue Label & FACS Blendshapes
        if (this.metrics.blink_rate < 8.0 && ear < 0.22) {
          this.metrics.fatigue_label = "Drowsy";
        } else if (this.metrics.blink_rate > 28.0) {
          this.metrics.fatigue_label = "Stressed Eyes";
        } else {
          this.metrics.fatigue_label = "Normal";
        }

        // Extract FACS blendshapes dictionary from MediaPipe
        const blendshapes: Record<string, number> = {};
        let smileScore = 0.0;
        if (results.faceBlendshapes && results.faceBlendshapes.length > 0) {
          const shapes = results.faceBlendshapes[0].categories;
          for (const s of shapes) {
            blendshapes[s.categoryName] = s.score;
            if (s.categoryName === "mouthSmileLeft" || s.categoryName === "mouthSmileRight") {
              if (s.score > smileScore) smileScore = s.score;
            }
          }
        }
        const isSmiling = smileScore >= 0.30;

        // 4. Calculate Face Bounding Box
        let minX = 1.0, minY = 1.0, maxX = 0.0, maxY = 0.0;
        for (const lm of landmarks) {
          if (lm.x < minX) minX = lm.x;
          if (lm.x > maxX) maxX = lm.x;
          if (lm.y < minY) minY = lm.y;
          if (lm.y > maxY) maxY = lm.y;
        }

        // Add padding
        const padX = (maxX - minX) * 0.20;
        const padY = (maxY - minY) * 0.20;
        const box = {
          x: Math.max(0, (minX - padX) * canvas.width),
          y: Math.max(0, (minY - padY) * canvas.height),
          width: Math.min(canvas.width - Math.max(0, (minX - padX) * canvas.width), (maxX - minX + padX * 2) * canvas.width),
          height: Math.min(canvas.height - Math.max(0, (minY - padY) * canvas.height), (maxY - minY + padY * 2) * canvas.height),
        };
        this.metrics.box = box;

        // 5. Send cropped patch & eye/blendshape metrics to Python @ 6 FPS
        if (now - this.lastCropTime > 160 && this.cropSocket && this.cropSocket.readyState === WebSocket.OPEN) {
          this.lastCropTime = now;

          // Send eye & smile blendshape metrics
          try {
            this.cropSocket.send(
              JSON.stringify({
                type: "eye_metrics",
                ear: this.metrics.ear,
                blink_rate: this.metrics.blink_rate,
                fatigue_label: this.metrics.fatigue_label,
                fatigue_strain: this.metrics.fatigue_label === "Drowsy" ? 0.8 : (this.metrics.fatigue_label === "Stressed Eyes" ? 0.6 : 0.1),
                eye_available: true,
                is_smiling: isSmiling,
                smile_score: smileScore,
                blendshapes: blendshapes,
              })
            );
          } catch (e) {}

          this.sendFaceCrop(video, minX, minY, maxX, maxY, padX, padY);
        }

        // 6. Draw Aerospace HUD
        this.drawHUD(ctx, canvas, box, emotionColor);
      } else {
        this.metrics.face_detected = false;
        this.metrics.box = null;
        this.drawStandbyHUD(ctx, canvas, emotionColor);
      }
    } catch (e) {
      console.debug("Video detection error:", e);
    }

    return this.metrics;
  }

  private computeEAR(landmarks: any[], indices: number[], w: number, h: number): number {
    const p1 = { x: landmarks[indices[0]].x * w, y: landmarks[indices[0]].y * h };
    const p2 = { x: landmarks[indices[1]].x * w, y: landmarks[indices[1]].y * h };
    const p3 = { x: landmarks[indices[2]].x * w, y: landmarks[indices[2]].y * h };
    const p4 = { x: landmarks[indices[3]].x * w, y: landmarks[indices[3]].y * h };
    const p5 = { x: landmarks[indices[4]].x * w, y: landmarks[indices[4]].y * h };
    const p6 = { x: landmarks[indices[5]].x * w, y: landmarks[indices[5]].y * h };

    const dist = (a: { x: number; y: number }, b: { x: number; y: number }) =>
      Math.hypot(a.x - b.x, a.y - b.y);

    const verticalA = dist(p2, p6);
    const verticalB = dist(p3, p5);
    const horizontal = dist(p1, p4);

    return horizontal > 0 ? (verticalA + verticalB) / (2.0 * horizontal) : 0.28;
  }

  private sendFaceCrop(
    video: HTMLVideoElement,
    minX: number,
    minY: number,
    maxX: number,
    maxY: number,
    padX: number,
    padY: number
  ): void {
    try {
      const vw = video.videoWidth || 640;
      const vh = video.videoHeight || 480;
      if (vw <= 0 || vh <= 0) return;

      const cropX = Math.max(0, (minX - padX) * vw);
      const cropY = Math.max(0, (minY - padY) * vh);
      const cropW = Math.min(vw - cropX, (maxX - minX + padX * 2) * vw);
      const cropH = Math.min(vh - cropY, (maxY - minY + padY * 2) * vh);

      if (cropW < 20 || cropH < 20) return;

      const offCanvas = document.createElement("canvas");
      offCanvas.width = 224;
      offCanvas.height = 224;
      const offCtx = offCanvas.getContext("2d");
      if (!offCtx) return;

      offCtx.drawImage(
        video,
        cropX, cropY, cropW, cropH,
        0, 0, 224, 224
      );

      offCanvas.toBlob((blob) => {
        if (blob && this.cropSocket && this.cropSocket.readyState === WebSocket.OPEN) {
          blob.arrayBuffer().then((buf) => {
            this.cropSocket?.send(buf);
          });
        }
      }, "image/jpeg", 0.85);
    } catch (e) {}
  }

  private drawHUD(
    ctx: CanvasRenderingContext2D,
    canvas: HTMLCanvasElement,
    box: { x: number; y: number; width: number; height: number },
    color: string
  ): void {
    const w = canvas.width;
    const h = canvas.height;

    // L-05: HUD Top Banner: Emotion Tag
    ctx.font = "bold 13px 'JetBrains Mono', monospace";
    ctx.fillStyle = color;
    ctx.fillText(`● ${this.metrics.emotion_tag} ${Math.round(this.metrics.confidence * 100)}%`, 14, 22);

    // L-06: HUD Top Banner: Frame Counter
    ctx.fillStyle = "#ff6d00"; // Aerospace orange
    ctx.fillText(`FRAME #${this.frameCount}`, w - 120, 22);

    // L-07: HUD Reticle: Face Corner Brackets
    const { x, y, width, height } = box;
    const bracketLen = Math.min(24, width * 0.25);
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.5;

    // Top-left
    ctx.beginPath();
    ctx.moveTo(x, y + bracketLen);
    ctx.lineTo(x, y);
    ctx.lineTo(x + bracketLen, y);
    ctx.stroke();

    // Top-right
    ctx.beginPath();
    ctx.moveTo(x + width - bracketLen, y);
    ctx.lineTo(x + width, y);
    ctx.lineTo(x + width, y + bracketLen);
    ctx.stroke();

    // Bottom-left
    ctx.beginPath();
    ctx.moveTo(x, y + height - bracketLen);
    ctx.lineTo(x, y + height);
    ctx.lineTo(x + bracketLen, y + height);
    ctx.stroke();

    // Bottom-right
    ctx.beginPath();
    ctx.moveTo(x + width - bracketLen, y + height);
    ctx.lineTo(x + width, y + height);
    ctx.lineTo(x + width, y + height - bracketLen);
    ctx.stroke();

    // L-08: HUD Reticle: Floating Emotion Tag
    ctx.fillStyle = "rgba(9, 13, 20, 0.75)";
    ctx.fillRect(x, Math.max(0, y - 22), 105, 18);
    ctx.fillStyle = color;
    ctx.font = "bold 11px 'JetBrains Mono', monospace";
    ctx.fillText(`${this.metrics.emotion_tag} ${Math.round(this.metrics.confidence * 100)}%`, x + 6, Math.max(12, y - 9));

    // L-09: HUD Bottom Banner: Eye Metrics
    ctx.fillStyle = "#2ecc71";
    ctx.font = "bold 11px 'JetBrains Mono', monospace";
    ctx.fillText(
      `EAR: ${this.metrics.ear.toFixed(3)}  BLINK: ${this.metrics.blink_rate}/min  FATIGUE: ${this.metrics.fatigue_label.toUpperCase()}`,
      14,
      h - 14
    );

    // L-10: HUD Bottom Banner: Mission Callout
    ctx.fillStyle = "#64748b";
    ctx.font = "10px 'JetBrains Mono', monospace";
    ctx.fillText("MAITRI 2.0 // ASTRONAUT VISION", w - 190, h - 14);
  }

  private drawStandbyHUD(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, color: string): void {
    const w = canvas.width;
    const h = canvas.height;

    ctx.fillStyle = color;
    ctx.font = "bold 13px 'JetBrains Mono', monospace";
    ctx.fillText(`● ${this.metrics.emotion_tag} ${Math.round(this.metrics.confidence * 100)}%`, 14, 22);

    ctx.fillStyle = "#ff6d00";
    ctx.fillText(`FRAME #${this.frameCount}`, w - 120, 22);

    ctx.fillStyle = "#64748b";
    ctx.font = "10px 'JetBrains Mono', monospace";
    ctx.fillText("MAITRI 2.0 // ASTRONAUT VISION", w - 190, h - 14);
  }
}

export const visionPipeline = new VisionPipeline();
