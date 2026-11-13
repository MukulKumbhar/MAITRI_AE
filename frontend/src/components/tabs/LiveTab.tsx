import React, { useEffect, useRef, useState } from "react";
import { TelemetryPayload, EmotionProbs } from "../../types";
import { visionPipeline, VisionMetrics } from "../../services/visionPipeline";
import { telemetrySocketService } from "../../services/telemetrySocket";
import { audioService } from "../../services/audioSocket";
import { postLog, updateSettings } from "../../services/api";
import {
  Camera,
  Mic,
  Sliders,
  Heart,
  Thermometer,
  Wind,
  Eye,
  CheckCircle,
  AlertTriangle,
  Brain,
  Shield,
  Save,
  Volume2,
  RefreshCw,
  Sparkles,
} from "lucide-react";

interface LiveTabProps {
  telemetry: TelemetryPayload | null;
  onNavigateTab: (tab: any) => void;
}

const EMOTION_COLORS: Record<string, string> = {
  happy: "#ffd600",
  neutral: "#94a3b8",
  surprise: "#00e5ff",
  sad: "#2979ff",
  fear: "#d500f9",
  angry: "#e74c3c",
  disgust: "#2ecc71",
};

export const LiveTab: React.FC<LiveTabProps> = ({ telemetry }) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Stream state
  const [cameraActive, setCameraActive] = useState<boolean>(false);
  const [micActive, setMicActive] = useState<boolean>(false);
  const [pipelineMetrics, setPipelineMetrics] = useState<VisionMetrics>(visionPipeline.metrics);
  const [logSuccess, setLogSuccess] = useState<boolean>(false);
  const [autoLog, setAutoLog] = useState<boolean>(false);

  // Fusion mode controls
  const [isDynamicMode, setIsDynamicMode] = useState<boolean>(true);
  const [manualSplit, setManualSplit] = useState<number>(60); // 60% face, 40% voice
  const [showMicCalibration, setShowMicCalibration] = useState<boolean>(false);
  const [micGain, setMicGain] = useState<number>(1.0);
  const [silenceThreshold, setSilenceThreshold] = useState<number>(0.03);

  // Local vitals sliders
  const [hr, setHr] = useState<number>(75);
  const [temp, setTemp] = useState<number>(36.6);
  const [spo2, setSpo2] = useState<number>(98);

  // Sync incoming telemetry vitals if not currently sliding
  useEffect(() => {
    if (telemetry?.vitals) {
      setHr(telemetry.vitals.heart_rate);
      setTemp(telemetry.vitals.temperature);
      setSpo2(telemetry.vitals.spo2);
    }
  }, [telemetry?.timestamp]);

  // Start webcam
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, frameRate: 30 },
        audio: false,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setCameraActive(true);
        await visionPipeline.init();
      }
    } catch (err) {
      console.warn("Camera start failed:", err);
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach((track) => track.stop());
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
  };

  // Video processing loop at 60 FPS
  useEffect(() => {
    let animId: number;

    const renderLoop = () => {
      if (videoRef.current && canvasRef.current && cameraActive) {
        const directEmotion = visionPipeline.metrics.emotion_tag?.toLowerCase();
        const domEmotion = (directEmotion && directEmotion !== "neutral") ? directEmotion : (telemetry?.face?.emotion || directEmotion || "neutral");
        const domConf = visionPipeline.metrics.confidence || telemetry?.face?.confidence || 0.85;
        const col = EMOTION_COLORS[domEmotion.toLowerCase()] || "#2ecc71";

        const mets = visionPipeline.processVideoFrame(
          videoRef.current,
          canvasRef.current,
          domEmotion,
          domConf,
          col
        );
        setPipelineMetrics({ ...mets });
      }
      animId = requestAnimationFrame(renderLoop);
    };

    animId = requestAnimationFrame(renderLoop);
    return () => cancelAnimationFrame(animId);
  }, [cameraActive, telemetry]);

  // Toggle mic
  const handleToggleMic = async () => {
    if (!micActive) {
      const ok = await audioService.startMicrophoneCapture();
      setMicActive(ok);
    } else {
      audioService.stopMicrophoneCapture();
      setMicActive(false);
    }
  };

  // Vitals update
  const handleVitalsChange = (newHr: number, newTemp: number, newSpo2: number) => {
    setHr(newHr);
    setTemp(newTemp);
    setSpo2(newSpo2);
    telemetrySocketService.sendVitalsUpdate(newHr, newTemp, newSpo2);
  };

  // Settings update
  const handleFusionModeChange = (dynamic: boolean) => {
    setIsDynamicMode(dynamic);
    updateSettings({
      manual_override: !dynamic,
      manual_face_ratio: manualSplit / 100.0,
    });
  };

  const handleManualSplitChange = (val: number) => {
    setManualSplit(val);
    updateSettings({
      manual_override: true,
      manual_face_ratio: val / 100.0,
    });
  };

  const handleMicCalibration = (newGain: number, newThresh: number) => {
    setMicGain(newGain);
    setSilenceThreshold(newThresh);
    audioService.sendControl({ type: "set_gain", gain: newGain });
    audioService.sendControl({ type: "set_threshold", threshold: newThresh });
    updateSettings({ mic_gain: newGain, silence_threshold: newThresh });
  };

  // Manual Log
  const handleManualLog = async () => {
    if (!telemetry) return;
    try {
      await postLog({
        face_emotion: telemetry.face.emotion,
        fused_emotion: telemetry.fusion.dominant_emotion,
        voice_state: telemetry.voice.is_speaking ? "speaking" : "silent",
        heart_rate: hr,
        temperature: temp,
        spo2: spo2,
        blink_rate: telemetry.eye.blink_rate,
        fatigue_label: telemetry.eye.fatigue_label,
        stress_score: telemetry.fusion.stress_pct,
        stress_level: telemetry.fusion.stress_level,
        alert_triggered: telemetry.alert.header,
        response_msg: telemetry.alert.body,
        prob_angry: telemetry.fusion.fused_probs.angry,
        prob_disgust: telemetry.fusion.fused_probs.disgust,
        prob_fear: telemetry.fusion.fused_probs.fear,
        prob_happy: telemetry.fusion.fused_probs.happy,
        prob_neutral: telemetry.fusion.fused_probs.neutral,
        prob_sad: telemetry.fusion.fused_probs.sad,
        prob_surprise: telemetry.fusion.fused_probs.surprise,
        emotion_probs: telemetry.fusion.fused_probs,
      });
      setLogSuccess(true);
      setTimeout(() => setLogSuccess(false), 2500);
    } catch (e) {
      console.error(e);
    }
  };

  // Auto-log cadence effect
  useEffect(() => {
    if (!autoLog) return;
    const interval = setInterval(() => {
      handleManualLog();
    }, 6000);
    return () => clearInterval(interval);
  }, [autoLog, telemetry, hr, temp, spo2]);

  // Derived display values
  const stressPct = telemetry?.fusion?.stress_pct ?? 22.4;
  const stressLevel = telemetry?.fusion?.stress_level ?? "NOMINAL";
  const dominantEmotion = telemetry?.fusion?.dominant_emotion ?? "neutral";
  const alertInfo = telemetry?.alert ?? {
    level: "NOMINAL",
    icon: "✅",
    color: "#2ecc71",
    header: "All Systems Nominal",
    body: "Vitals and emotional state are within optimal parameters.",
    technique: "Box Breathing: 4s Inhale, 4s Hold, 4s Exhale, 4s Hold.",
  };

  const fusedProbs: EmotionProbs = telemetry?.fusion?.fused_probs ?? {
    angry: 0.02,
    disgust: 0.01,
    fear: 0.02,
    happy: 0.74,
    neutral: 0.15,
    sad: 0.03,
    surprise: 0.03,
  };

  const voiceProbs: EmotionProbs = telemetry?.voice?.probs ?? {
    angry: 0.02,
    disgust: 0.01,
    fear: 0.03,
    happy: 0.05,
    neutral: 0.82,
    sad: 0.04,
    surprise: 0.03,
  };

  const faceProbs: EmotionProbs = telemetry?.face?.probs ?? {
    angry: 0.02,
    disgust: 0.01,
    fear: 0.02,
    happy: 0.15,
    neutral: 0.74,
    sad: 0.03,
    surprise: 0.03,
  };

  const liveFaceEmotion = pipelineMetrics.emotion_tag || telemetry?.face?.emotion || "neutral";
  const liveFaceConf = pipelineMetrics.confidence || telemetry?.face?.confidence || 0.85;

  const voiceDb = telemetry?.voice?.db ?? -48.2;
  const clampedDb = Math.max(-60, Math.min(0, voiceDb));
  const vuPct = Math.round(((clampedDb + 60) / 60) * 100);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12 font-sans">
      {/* ──────────────────────────────────────────────────────────────────────── */}
      {/* ROW 1: Side-by-Side Live Feeds (Webcam Vision & Acoustic Telemetry)      */}
      {/* ──────────────────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Vision & Face FER */}
        <div className="bg-space-900 border border-space-700 rounded-xl p-5 shadow-glass-panel flex flex-col justify-between">
          <div>
            {/* L-01: Webcam Feed Subheader */}
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold uppercase tracking-wider text-space-100 flex items-center gap-2">
                <Camera className="w-4 h-4 text-cyan-400" />
                📹 Live Astronaut Feed &amp; Face FER
              </h2>
              {/* L-03: WebRTC / Browser Microphone Toggle Checkbox */}
              <label className="flex items-center gap-1.5 cursor-pointer text-xs text-space-300">
                <input
                  type="checkbox"
                  checked={micActive}
                  onChange={handleToggleMic}
                  className="rounded bg-space-800 border-space-700 text-cyan-500 focus:ring-0 cursor-pointer"
                />
                <span>🎙️ Mic Stream</span>
              </label>
            </div>

            {/* L-02: Webcam Subtitle Caption */}
            <p className="text-[11px] text-space-400 mt-1">
              Background ML pipeline: MediaPipe 478-point 3D iris mesh &amp; ONNX AffectNet-7 FER.
            </p>

            {/* L-04 to L-10: Live Video Streamer with Canvas HUD */}
            <div className="relative mt-3 rounded-lg overflow-hidden border border-space-700 bg-space-950 aspect-[4/3] flex items-center justify-center scanline-bg">
              <video
                ref={videoRef}
                playsInline
                muted
                className={`w-full h-full object-cover ${cameraActive ? "block" : "hidden"}`}
              />
              <canvas
                ref={canvasRef}
                width={640}
                height={480}
                className="absolute inset-0 w-full h-full pointer-events-none"
              />

              {!cameraActive && (
                <div className="text-center p-6 space-y-3 z-10">
                  <div className="w-12 h-12 rounded-full bg-space-800 border border-space-700 flex items-center justify-center mx-auto text-space-400">
                    <Camera className="w-6 h-6" />
                  </div>
                  <p className="text-xs text-space-400">Astronaut camera stream offline</p>
                  <button
                    onClick={startCamera}
                    className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs uppercase tracking-wider shadow-lg transition-all"
                  >
                    ▶️ Start Camera Stream
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* L-11: DIP Image Clarity Status Card */}
          <div className="mt-3 p-2.5 rounded bg-space-850 border border-space-800 flex items-center justify-between text-xs font-mono">
            <span className="text-space-400">DIP Optical Clarity:</span>
            {telemetry?.face?.is_blurry ? (
              <span className="text-amber-400 font-bold flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" /> ⚠️ Motion Blur (Fusion Gated)
              </span>
            ) : (
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <CheckCircle className="w-3.5 h-3.5" /> ✅ Sharp (Score: {telemetry?.face?.blur_score?.toFixed(1) || "124.0"})
              </span>
            )}
          </div>

          {/* Facial Affect Classifier Badge & 7-Class Distribution */}
          <div className="mt-3 p-3.5 rounded-lg bg-space-850 border border-space-800 space-y-2.5">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[10px] text-space-400 uppercase tracking-wider block">
                  Facial Affect Classifier (AffectNet ONNX + MediaPipe FACS)
                </span>
                <span className="text-base font-bold text-space-100 uppercase tracking-wide flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: EMOTION_COLORS[liveFaceEmotion.toLowerCase()] || "#2ecc71" }}
                  />
                  {liveFaceEmotion} ({Math.round(liveFaceConf * 100)}%)
                </span>
              </div>
              <span
                className={`font-mono text-xs px-2.5 py-1 rounded font-bold uppercase tracking-wider ${
                  cameraActive
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                    : "bg-space-800 text-space-400 border border-space-700"
                }`}
              >
                {cameraActive ? "ACTIVE" : "AWAITING CAMERA"}
              </span>
            </div>

            {/* Face Emotion 7-Class Bars */}
            <div className="space-y-1.5 font-mono text-[11px] pt-1">
              {(["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"] as (keyof EmotionProbs)[]).map((emo) => {
                const prob = faceProbs[emo] || 0.0;
                const isDom = liveFaceEmotion.toLowerCase() === emo;
                return (
                  <div key={emo} className="flex items-center gap-2">
                    <span className="w-16 uppercase text-space-400 text-[10px]">{emo}</span>
                    <div className="flex-1 h-2 bg-space-950 rounded-full overflow-hidden border border-space-800">
                      <div
                        className="h-full rounded-full transition-all duration-150"
                        style={{
                          width: `${Math.round(prob * 100)}%`,
                          backgroundColor: EMOTION_COLORS[emo] || "#2ecc71",
                        }}
                      />
                    </div>
                    <span className="w-9 text-right text-space-300 text-[10px]">
                      {Math.round(prob * 100)}%
                    </span>
                    <span className="w-3 text-cyan-400 text-[10px]">{isDom ? "◀" : ""}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Voice Emotion & Acoustic Telemetry */}
        <div className="bg-space-900 border border-space-700 rounded-xl p-5 shadow-glass-panel flex flex-col justify-between">
          <div>
            {/* L-12: Voice Telemetry Subheader */}
            <h2 className="text-sm font-bold uppercase tracking-wider text-space-100 flex items-center gap-2">
              <Mic className="w-4 h-4 text-cyan-400" />
              🎙️ Voice Emotion &amp; Acoustic Telemetry
            </h2>
            {/* L-13: Voice Telemetry Caption */}
            <p className="text-[11px] text-space-400 mt-1">
              Quantized Wav2Vec2 ONNX acoustic prosody &amp; ballistic hardware VU meter.
            </p>

            {/* L-14: Instant Voice Emotion Badge */}
            <div className="mt-3 p-3.5 rounded-lg bg-space-850 border border-space-800 flex items-center justify-between">
              <div>
                <span className="text-[10px] text-space-400 uppercase tracking-wider block">
                  Acoustic Speech Classifier
                </span>
                <span className="text-base font-bold text-space-100 uppercase tracking-wide">
                  {telemetry?.voice?.is_speaking
                    ? `🔊 ${telemetry.voice.emotion} (${Math.round((telemetry.voice.confidence || 0.8) * 100)}%)`
                    : "🔇 STANDBY (GATE: 0%)"}
                </span>
              </div>
              <span
                className={`font-mono text-xs px-2.5 py-1 rounded font-bold uppercase tracking-wider ${
                  telemetry?.voice?.is_speaking
                    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 animate-pulse"
                    : "bg-space-800 text-space-400 border border-space-700"
                }`}
              >
                {telemetry?.voice?.is_speaking ? "ACTIVE" : "AWAITING SPEECH"}
              </span>
            </div>

            {/* L-15: Voice Emotion 7-Class Bars */}
            <div className="mt-3 space-y-1.5 font-mono text-[11px]">
              {(["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"] as (keyof EmotionProbs)[]).map((emo) => {
                const prob = voiceProbs[emo] || 0.0;
                const isDom = telemetry?.voice?.emotion?.toLowerCase() === emo;
                return (
                  <div key={emo} className="flex items-center gap-2">
                    <span className="w-16 uppercase text-space-400 text-[10px]">{emo}</span>
                    <div className="flex-1 h-2 bg-space-950 rounded-full overflow-hidden border border-space-800">
                      <div
                        className="h-full rounded-full transition-all duration-150"
                        style={{
                          width: `${Math.round(prob * 100)}%`,
                          backgroundColor: EMOTION_COLORS[emo] || "#2ecc71",
                        }}
                      />
                    </div>
                    <span className="w-9 text-right text-space-300 text-[10px]">
                      {Math.round(prob * 100)}%
                    </span>
                    <span className="w-3 text-cyan-400 text-[10px]">{isDom ? "◀" : ""}</span>
                  </div>
                );
              })}
            </div>

            {/* L-16: Hardware Ballistic VU Meter */}
            <div className="mt-4 p-3 rounded-lg bg-space-850 border border-space-800 space-y-1.5">
              <div className="flex justify-between items-center text-[11px] font-mono text-space-400">
                <span className="flex items-center gap-1.5">
                  <Volume2 className="w-3.5 h-3.5 text-cyan-400" />
                  Hardware Input Level
                </span>
                <span className="text-cyan-300">
                  {voiceDb.toFixed(1)} dB ({vuPct}%)
                </span>
              </div>
              <div className="h-2 bg-space-950 rounded-full overflow-hidden border border-space-700">
                <div
                  className={`h-full rounded-full transition-all duration-75 ${
                    vuPct > 80
                      ? "bg-gradient-to-r from-emerald-500 via-amber-500 to-red-500"
                      : "bg-emerald-500"
                  }`}
                  style={{ width: `${vuPct}%` }}
                />
              </div>
            </div>

            {/* L-17: Audio Status Strip */}
            <div className="mt-2.5 flex items-center justify-between text-[11px] font-mono text-space-400 px-1">
              <span>
                {telemetry?.voice?.is_speaking ? "🔊 SPEECH ACTIVE" : "🔇 SILENT / AMBIENT"}
              </span>
              <span>RMS: {telemetry?.voice?.rms?.toFixed(4) || "0.0032"} | PipeWire 16kHz</span>
            </div>
          </div>

          {/* L-18 to L-23: Fusion Weighting Mode Toggle & Calibration */}
          <div className="mt-4 pt-3 border-t border-space-800 space-y-3">
            <div className="flex items-center justify-between">
              {/* L-18: Fusion Weighting Mode Toggle */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleFusionModeChange(true)}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                    isDynamicMode
                      ? "bg-cyan-600/30 text-cyan-300 border border-cyan-500/50"
                      : "bg-space-850 text-space-400 hover:text-space-200"
                  }`}
                >
                  🤖 Dynamic Quality-Aware
                </button>
                <button
                  onClick={() => handleFusionModeChange(false)}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                    !isDynamicMode
                      ? "bg-cyan-600/30 text-cyan-300 border border-cyan-500/50"
                      : "bg-space-850 text-space-400 hover:text-space-200"
                  }`}
                >
                  🎛️ Manual Override
                </button>
              </div>

              {/* L-21: Microphone Calibration Expander Toggle */}
              <button
                onClick={() => setShowMicCalibration(!showMicCalibration)}
                className="text-space-400 hover:text-space-200 p-1 text-xs flex items-center gap-1"
              >
                <Sliders className="w-3.5 h-3.5" />
                <span>Calibration</span>
              </button>
            </div>

            {/* L-19: Manual Behavioral Split Slider (visible only in manual mode) */}
            {!isDynamicMode && (
              <div className="p-2.5 rounded bg-space-850 border border-space-800 space-y-1">
                <div className="flex justify-between text-[11px] font-mono text-space-300">
                  <span>Behavioral Split (Face vs Voice)</span>
                  <span className="text-cyan-400">
                    {manualSplit}% Face / {100 - manualSplit}% Voice
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={manualSplit}
                  onChange={(e) => handleManualSplitChange(parseInt(e.target.value))}
                  className="w-full h-1.5 bg-space-950 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                />
              </div>
            )}

            {/* L-20: Fusion Weight Mode Caption */}
            <p className="text-[10px] text-space-400">
              {isDynamicMode
                ? "Adaptive Bayesian EMA dynamically discounts blurred frames and silent audio."
                : "Manual ratio locks sensory weights regardless of environmental SNR or lighting."}
            </p>

            {/* L-22 & L-23: Microphone Calibration Expander Details */}
            {showMicCalibration && (
              <div className="p-3 rounded bg-space-850 border border-space-800 space-y-2.5 font-mono text-xs">
                <div className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-space-400">Mic Digital Pre-Gain (0.5–3.0)</span>
                    <span className="text-cyan-300">{micGain.toFixed(1)}x</span>
                  </div>
                  <input
                    type="range"
                    min="0.5"
                    max="3.0"
                    step="0.1"
                    value={micGain}
                    onChange={(e) => handleMicCalibration(parseFloat(e.target.value), silenceThreshold)}
                    className="w-full h-1 bg-space-950 rounded appearance-none cursor-pointer accent-cyan-400"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-space-400">Silence Gate Threshold (0.005–0.080)</span>
                    <span className="text-cyan-300">{silenceThreshold.toFixed(3)}</span>
                  </div>
                  <input
                    type="range"
                    min="0.005"
                    max="0.080"
                    step="0.005"
                    value={silenceThreshold}
                    onChange={(e) => handleMicCalibration(micGain, parseFloat(e.target.value))}
                    className="w-full h-1 bg-space-950 rounded appearance-none cursor-pointer accent-cyan-400"
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────────────────── */}
      {/* ROW 2: Biological Telemetry & Eye Tracking                               */}
      {/* ──────────────────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Physiological Sensors (L-24 to L-31) */}
        <div className="bg-space-900 border border-space-700 rounded-xl p-5 shadow-glass-panel">
          {/* L-24: Vitals Header & Caption */}
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wider text-space-100 flex items-center gap-2">
              <Heart className="w-4 h-4 text-red-400" />
              Physiological Sensors
            </h3>
            {/* L-31: Vitals Composite Status Badge */}
            <span
              className={`px-2.5 py-0.5 rounded text-[11px] font-mono font-bold uppercase ${
                telemetry?.vitals?.status === "Critical"
                  ? "bg-red-500/20 text-red-400 border border-red-500/40"
                  : telemetry?.vitals?.status === "Elevated"
                  ? "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                  : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
              }`}
            >
              Vitals: {telemetry?.vitals?.status || "Normal"}
            </span>
          </div>
          <p className="text-[11px] text-space-400 mt-1">
            Real-time biometric biosensors: ECG cardiac rhythm, thermal probe &amp; pulse oximetry.
          </p>

          {/* Sliders (L-25, L-26, L-27) */}
          <div className="mt-4 space-y-3.5 font-mono text-xs">
            {/* L-25: Heart Rate Slider */}
            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-space-300 flex items-center gap-1.5">
                  <Heart className="w-3.5 h-3.5 text-red-400" /> Heart Rate (BPM)
                </span>
                <span className="text-cyan-300 font-bold">{hr} BPM</span>
              </div>
              <input
                type="range"
                min="50"
                max="160"
                value={hr}
                onChange={(e) => handleVitalsChange(parseInt(e.target.value), temp, spo2)}
                className="w-full h-1.5 bg-space-950 rounded-lg appearance-none cursor-pointer accent-red-400"
              />
            </div>

            {/* L-26: Skin Temperature Slider */}
            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-space-300 flex items-center gap-1.5">
                  <Thermometer className="w-3.5 h-3.5 text-amber-400" /> Skin Temperature (°C)
                </span>
                <span className="text-cyan-300 font-bold">{temp.toFixed(1)} °C</span>
              </div>
              <input
                type="range"
                min="35.0"
                max="40.0"
                step="0.1"
                value={temp}
                onChange={(e) => handleVitalsChange(hr, parseFloat(e.target.value), spo2)}
                className="w-full h-1.5 bg-space-950 rounded-lg appearance-none cursor-pointer accent-amber-400"
              />
            </div>

            {/* L-27: Blood Oxygen (SpO2) Slider */}
            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-space-300 flex items-center gap-1.5">
                  <Wind className="w-3.5 h-3.5 text-cyan-400" /> Blood Oxygen (SpO₂ %)
                </span>
                <span className="text-cyan-300 font-bold">{spo2}%</span>
              </div>
              <input
                type="range"
                min="85"
                max="100"
                value={spo2}
                onChange={(e) => handleVitalsChange(hr, temp, parseInt(e.target.value))}
                className="w-full h-1.5 bg-space-950 rounded-lg appearance-none cursor-pointer accent-cyan-400"
              />
            </div>
          </div>

          {/* Strain Metric Cards (L-28, L-29, L-30) */}
          <div className="mt-4 grid grid-cols-3 gap-2 text-center font-mono">
            <div className="p-2 rounded bg-space-850 border border-space-800">
              <span className="text-[10px] text-space-400 block">HR STRAIN</span>
              <span className="text-xs font-bold text-red-400">
                {Math.round((telemetry?.vitals?.hr_strain || 0.08) * 100)}%
              </span>
            </div>
            <div className="p-2 rounded bg-space-850 border border-space-800">
              <span className="text-[10px] text-space-400 block">TEMP STRAIN</span>
              <span className="text-xs font-bold text-amber-400">
                {Math.round((telemetry?.vitals?.temp_strain || 0.0) * 100)}%
              </span>
            </div>
            <div className="p-2 rounded bg-space-850 border border-space-800">
              <span className="text-[10px] text-space-400 block">SpO₂ STRAIN</span>
              <span className="text-xs font-bold text-cyan-400">
                {Math.round((telemetry?.vitals?.spo2_strain || 0.0) * 100)}%
              </span>
            </div>
          </div>
        </div>

        {/* Right: Eye Tracking & Fatigue (L-32 to L-37) */}
        <div className="bg-space-900 border border-space-700 rounded-xl p-5 shadow-glass-panel flex flex-col justify-between">
          <div>
            {/* L-32: Eye Tracking Header & Caption */}
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold uppercase tracking-wider text-space-100 flex items-center gap-2">
                <Eye className="w-4 h-4 text-purple-400" />
                Eye Tracking &amp; Fatigue
              </h3>
              {/* L-35: Ocular Fatigue Status Badge */}
              <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-bold uppercase bg-purple-500/20 text-purple-300 border border-purple-500/30">
                👁️ {cameraActive ? pipelineMetrics.fatigue_label : telemetry?.eye?.fatigue_label || "Normal"}
              </span>
            </div>
            <p className="text-[11px] text-space-400 mt-1">
              PERCLOS analysis via 6-point eye aspect ratio (EAR) &amp; rolling blink dynamics.
            </p>

            {/* Metrics Grid (L-33, L-34) */}
            <div className="mt-4 grid grid-cols-2 gap-3 font-mono">
              {/* L-33: Eye Aspect Ratio (EAR) */}
              <div className="p-3.5 rounded bg-space-850 border border-space-800 text-center">
                <span className="text-[10px] text-space-400 uppercase tracking-wide block">
                  Eye Aspect Ratio (EAR)
                </span>
                <span className="text-xl font-bold text-cyan-300 mt-1 block">
                  {(cameraActive ? pipelineMetrics.ear : telemetry?.eye?.ear || 0.285).toFixed(3)}
                </span>
                <span className="text-[10px] text-space-400 mt-0.5 block">Threshold: &lt; 0.20</span>
              </div>

              {/* L-34: 60-Sec Rolling Blink Rate */}
              <div className="p-3.5 rounded bg-space-850 border border-space-800 text-center">
                <span className="text-[10px] text-space-400 uppercase tracking-wide block">
                  Rolling Blink Rate
                </span>
                <span className="text-xl font-bold text-purple-300 mt-1 block">
                  {cameraActive ? pipelineMetrics.blink_rate : telemetry?.eye?.blink_rate || 14.0} /min
                </span>
                <span className="text-[10px] text-space-400 mt-0.5 block">Nominal: 12–20 /min</span>
              </div>
            </div>

            {/* L-37: Inactive Eye Tracking Notice if camera off */}
            {!cameraActive && (
              <div className="mt-4 p-3 rounded bg-cyan-950/40 border border-cyan-800/60 text-cyan-200 text-xs flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-cyan-400 shrink-0" />
                <span>▶️ Start the camera stream to engage in-browser 60 FPS eye-tracking.</span>
              </div>
            )}
          </div>

          {/* L-36: Frames Processed Caption */}
          <div className="mt-4 pt-3 border-t border-space-800 flex justify-between items-center text-[11px] font-mono text-space-400">
            <span>Vision Engine: MediaPipe WASM</span>
            <span>Frames processed: {cameraActive ? pipelineMetrics.frame_count : telemetry?.eye?.frame_count || 1240}</span>
          </div>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────────────────── */}
      {/* ROW 3: Multimodal Assessment, Psychological Support & Database Logging   */}
      {/* ──────────────────────────────────────────────────────────────────────── */}
      <div className="bg-space-900 border border-space-700 rounded-xl p-5 shadow-glass-panel space-y-5">
        {/* L-38: Live Assessment Subheader */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-space-800 pb-3">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-space-100 flex items-center gap-2">
              <Brain className="w-4 h-4 text-cyan-400" />
              🧠 Live Multimodal Stress Assessment &amp; Clinical Countermeasures
            </h2>
            <p className="text-[11px] text-space-400 mt-0.5">
              Bayesian fusion combining Facial Affect, Voice Prosody, Biometrics &amp; Eye Fatigue.
            </p>
          </div>

          {/* L-53: Telemetry Cadence Caption */}
          <span className="text-[11px] font-mono text-space-400 px-2.5 py-1 rounded bg-space-850 border border-space-800">
            ⚡ Real-time Telemetry: (10 Hz Active)
          </span>
        </div>

        {/* Sensory Weights (L-39, L-40, L-41, L-42, L-43) */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 font-mono text-center">
          <div className="p-3 rounded bg-space-850 border border-space-800">
            <span className="text-[10px] text-space-400 block">FACE WEIGHT</span>
            <span className="text-sm font-bold text-cyan-300">
              {Math.round((telemetry?.fusion?.weights?.face || 0.36) * 100)}%
            </span>
          </div>
          <div className="p-3 rounded bg-space-850 border border-space-800">
            <span className="text-[10px] text-space-400 block">VOICE WEIGHT</span>
            <span className="text-sm font-bold text-cyan-300">
              {Math.round((telemetry?.fusion?.weights?.voice || 0.0) * 100)}%
            </span>
          </div>
          <div className="p-3 rounded bg-space-850 border border-space-800">
            <span className="text-[10px] text-space-400 block">VITALS WEIGHT</span>
            <span className="text-sm font-bold text-cyan-300">
              {Math.round((telemetry?.fusion?.weights?.vitals || 0.25) * 100)}%
            </span>
          </div>
          <div className="p-3 rounded bg-space-850 border border-space-800">
            <span className="text-[10px] text-space-400 block">EYE WEIGHT</span>
            <span className="text-sm font-bold text-cyan-300">
              {Math.round((telemetry?.fusion?.weights?.eye || 0.15) * 100)}%
            </span>
          </div>
          <div className="col-span-2 sm:col-span-1 p-3 rounded bg-cyan-950/30 border border-cyan-800/50">
            <span className="text-[10px] text-cyan-300 block">🎯 STRESS INDEX</span>
            <span className="text-sm font-bold text-cyan-400">{stressPct.toFixed(1)}%</span>
          </div>
        </div>

        {/* Fused Emotion Bars & Stress Hero Card (L-44 to L-49) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-2">
          {/* L-44: Fused Emotion 7-Class Bars */}
          <div className="lg:col-span-2 p-4 rounded-lg bg-space-850 border border-space-800 space-y-2">
            <span className="text-xs font-semibold text-space-300 uppercase tracking-wide block">
              Fused Emotion Distribution (7-Class Smooth)
            </span>
            <div className="space-y-1.5 font-mono text-[11px]">
              {(["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"] as (keyof EmotionProbs)[]).map((emo) => {
                const prob = fusedProbs[emo] || 0.0;
                const isDom = dominantEmotion.toLowerCase() === emo;
                return (
                  <div key={emo} className="flex items-center gap-2">
                    <span className="w-16 uppercase text-space-400 text-[10px]">{emo}</span>
                    <div className="flex-1 h-2 bg-space-950 rounded-full overflow-hidden border border-space-800">
                      <div
                        className="h-full rounded-full transition-all duration-150"
                        style={{
                          width: `${Math.round(prob * 100)}%`,
                          backgroundColor: EMOTION_COLORS[emo] || "#2ecc71",
                        }}
                      />
                    </div>
                    <span className="w-9 text-right text-space-300 text-[10px]">
                      {Math.round(prob * 100)}%
                    </span>
                    <span className="w-3 text-cyan-400 text-[10px]">{isDom ? "◀" : ""}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* L-45 to L-49: Stress Hero Card */}
          <div
            className={`p-5 rounded-lg border flex flex-col justify-between items-center text-center transition-all ${
              stressLevel === "CRITICAL"
                ? "bg-red-950/40 border-red-500/80 shadow-glow-critical"
                : stressLevel === "ELEVATED"
                ? "bg-orange-950/40 border-orange-500/80 shadow-glow-elevated"
                : stressLevel === "MILD"
                ? "bg-amber-950/40 border-amber-500/80 shadow-glow-mild"
                : "bg-emerald-950/30 border-emerald-500/60 shadow-glow-nominal"
            }`}
          >
            {/* L-45: Icon & L-46: Badge */}
            <div className="flex flex-col items-center gap-1.5">
              <span className="text-3xl">{alertInfo.icon}</span>
              <span className="font-bold text-xs uppercase tracking-wider px-3 py-0.5 rounded-full bg-space-900 border border-space-700">
                {stressLevel}
              </span>
            </div>

            {/* L-47: Percentage readout & L-48: Subtitle */}
            <div className="my-2">
              <span className="text-4xl font-extrabold font-mono text-space-100 tracking-tight">
                {stressPct.toFixed(1)}%
              </span>
              <span className="text-[10px] text-space-400 uppercase tracking-widest block mt-0.5">
                Combined Stress Index
              </span>
            </div>

            {/* L-49: Fused Dominant Emotion Badge */}
            <span
              className="text-xs font-mono font-bold px-3 py-1 rounded-full uppercase"
              style={{
                backgroundColor: `${EMOTION_COLORS[dominantEmotion.toLowerCase()] || "#2ecc71"}25`,
                color: EMOTION_COLORS[dominantEmotion.toLowerCase()] || "#2ecc71",
                border: `1px solid ${EMOTION_COLORS[dominantEmotion.toLowerCase()] || "#2ecc71"}50`,
              }}
            >
              Emotion: {dominantEmotion}
            </span>
          </div>
        </div>

        {/* Clinical Response & CBT Grounding Exercise (L-50, L-51, L-52) */}
        <div className="p-4 rounded-lg bg-space-850 border border-space-800 space-y-3">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-space-200">
              🤖 Autonomous Psychological Support
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            {/* L-51: Alert Clinical Response Box */}
            <div
              className="p-3.5 rounded bg-space-900 border-l-4 space-y-1"
              style={{ borderColor: alertInfo.color || "#2ecc71" }}
            >
              <h4 className="font-bold text-space-100">{alertInfo.header}</h4>
              <p className="text-space-300 leading-relaxed">{alertInfo.body}</p>
            </div>

            {/* L-52: CBT & Grounding Exercise Box */}
            <div className="p-3.5 rounded bg-space-900 border border-space-800 space-y-1">
              <h4 className="font-bold text-cyan-400 uppercase tracking-wide text-[11px]">
                Recommended Countermeasure
              </h4>
              <p className="text-space-300 leading-relaxed font-mono text-[11px]">
                {alertInfo.technique || "All parameters optimal. Maintain current flight operations."}
              </p>
            </div>
          </div>
        </div>

        {/* Database Logging Controls (L-54, L-55) */}
        <div className="pt-2 border-t border-space-800 flex flex-col sm:flex-row items-center justify-between gap-3">
          {/* L-54: Manual Mission Log Button */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleManualLog}
              className="px-4 py-2 rounded-lg bg-cyan-700 hover:bg-cyan-600 text-white font-bold text-xs uppercase tracking-wider flex items-center gap-2 shadow-lg transition-all"
            >
              <Save className="w-4 h-4" />
              💾 Log Reading to Mission Database
            </button>
            {logSuccess && (
              <span className="text-xs font-mono text-emerald-400 flex items-center gap-1 animate-fade-in">
                <CheckCircle className="w-3.5 h-3.5" /> Snapshot logged!
              </span>
            )}
          </div>

          {/* L-55: Auto-Log Cadence Checkbox */}
          <label className="flex items-center gap-2 cursor-pointer text-xs text-space-300">
            <input
              type="checkbox"
              checked={autoLog}
              onChange={(e) => setAutoLog(e.target.checked)}
              className="rounded bg-space-800 border-space-700 text-cyan-500 focus:ring-0 cursor-pointer"
            />
            <span>🔄 Auto-Log Telemetry to Database (Every 6s)</span>
          </label>
        </div>
      </div>
    </div>
  );
};
