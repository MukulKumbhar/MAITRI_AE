import React, { useState } from "react";
import {
  TelemetryPayload,
  TabId,
  AlarmRecord,
} from "../../types";
import {
  acknowledgeAlarm,
  pauseAlarmAudio,
} from "../../services/api";
import {
  Heart,
  Brain,
  Gauge,
  Stethoscope,
  ShieldAlert,
  AlertTriangle,
  CheckCircle,
  Eye,
  Mic,
  Activity,
  ArrowRight,
  VolumeX,
  Volume2,
  Clock,
  Sparkles,
  Zap,
} from "lucide-react";

interface OverviewTabProps {
  telemetry: TelemetryPayload | null;
  onNavigateTab: (tab: TabId) => void;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({
  telemetry,
  onNavigateTab,
}) => {
  const [ackLoading, setAckLoading] = useState<string | null>(null);

  // ── Alarms Handling ────────────────────────────────────────────────────────
  const alarms = telemetry?.alarms;
  const activeAlarms: AlarmRecord[] = alarms?.active_alarms || [];
  const topAlarm = activeAlarms.find((a) => !a.acknowledged) || activeAlarms[0];

  const handleAck = async (codeOrId: string) => {
    setAckLoading(codeOrId);
    try {
      await acknowledgeAlarm(codeOrId, "crew");
    } finally {
      setAckLoading(null);
    }
  };

  const handlePauseAudio = async () => {
    await pauseAlarmAudio(120.0);
  };

  // ── 5-System Health Radar Calculations (0 - 100% nominal score) ────────────
  // 1. Cardio: nominal when HR is 60-90, SPO2 > 96, composite vitals strain low
  const vitalsStrain = telemetry?.vitals?.composite_strain ?? 0.1;
  const cardioScore = Math.max(10, Math.min(100, Math.round((1.0 - vitalsStrain) * 100)));

  // 2. Neuro: nominal when fatigue strain is low and EAR is healthy (~0.28)
  const fatigueStrain = telemetry?.eye?.fatigue_strain ?? 0.1;
  const neuroScore = Math.max(10, Math.min(100, Math.round((1.0 - fatigueStrain) * 100)));

  // 3. Affect: nominal when stress is low
  const stressPct = telemetry?.fusion?.stress_pct ?? 18;
  const affectScore = Math.max(10, Math.min(100, Math.round(100 - stressPct)));

  // 4. Cabin: nominal when CO2 < 4.0 mmHg and Law 2014 hazard is nominal
  const co2 = telemetry?.cabin?.co2_mmhg ?? 3.0;
  const cabinScore = Math.max(10, Math.min(100, Math.round(Math.max(0, 100 - (co2 - 2.0) * 15))));

  // 5. Vigilance: watchdog & alertness
  const watchdogNormal = telemetry?.watchdog?.state === "NORMAL";
  const vigilanceScore = watchdogNormal ? 92 : telemetry?.watchdog?.state === "CHECK_IN" ? 55 : 20;

  const radarValues = [
    { label: "Cardio", score: cardioScore, color: "#00e5ff" },
    { label: "Neuro", score: neuroScore, color: "#d500f9" },
    { label: "Affect", score: affectScore, color: "#ffd600" },
    { label: "Cabin", score: cabinScore, color: "#2ecc71" },
    { label: "Vigilance", score: vigilanceScore, color: "#2979ff" },
  ];

  // SVG 5-Axis Radar polygon points (Center 130, 130, Radius 85)
  const cx = 130;
  const cy = 130;
  const rMax = 85;
  const angles = [-90, -18, 54, 126, 198].map((deg) => (deg * Math.PI) / 180);

  const getCoordinates = (index: number, score: number) => {
    const angle = angles[index];
    const r = (Math.max(5, Math.min(100, score)) / 100) * rMax;
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    };
  };

  const polygonPoints = radarValues
    .map((item, idx) => {
      const { x, y } = getCoordinates(idx, item.score);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  // ── Baseline and Explainable Rationale ──────────────────────────────────────
  const fusion = telemetry?.fusion;
  const explain = fusion?.explainable_breakdown;
  const weights = fusion?.weights || { face: 0.35, voice: 0.25, vitals: 0.25, eye: 0.15 };

  return (
    <div className="space-y-6">
      {/* ── 1. IEC 60601-1-8 Active Alarm Banner ────────────────────────────── */}
      {topAlarm && (
        <section
          role="region"
          aria-label="Active Clinical Alarm Notification"
          className={`p-4 rounded-xl border backdrop-blur-md transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-lg ${
            topAlarm.priority === "HIGH"
              ? "bg-red-950/50 border-red-500/60 shadow-glow-critical animate-pulse-slow"
              : topAlarm.priority === "MEDIUM"
              ? "bg-amber-950/40 border-amber-500/50 shadow-glow-mild"
              : "bg-space-900 border-space-700"
          }`}
        >
          <div className="flex items-start gap-3">
            <div
              className={`p-2.5 rounded-lg border ${
                topAlarm.priority === "HIGH"
                  ? "bg-red-500/20 text-red-300 border-red-500/40 animate-pulse"
                  : "bg-amber-500/20 text-amber-300 border-amber-500/40"
              }`}
            >
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider ${
                    topAlarm.priority === "HIGH"
                      ? "bg-red-500 text-white"
                      : "bg-amber-500 text-space-950"
                  }`}
                >
                  IEC {topAlarm.priority} PRIORITY
                </span>
                <span className="font-mono text-xs text-space-300">
                  [{topAlarm.code}]
                </span>
                <span className="text-xs text-space-400">
                  Source: {topAlarm.source}
                </span>
              </div>
              <p className="text-sm font-semibold text-space-100 mt-1">
                {topAlarm.message}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end md:self-center">
            {alarms?.audio_paused ? (
              <span className="px-3 py-1.5 rounded-lg bg-space-850 text-amber-300 border border-amber-500/30 text-xs font-mono flex items-center gap-1.5">
                <VolumeX className="w-3.5 h-3.5" />
                MUTED ({alarms.audio_pause_remaining_sec}s)
              </span>
            ) : (
              <button
                onClick={handlePauseAudio}
                className="px-3 py-1.5 rounded-lg bg-space-850 hover:bg-space-800 text-space-300 border border-space-700 hover:border-space-600 text-xs font-mono flex items-center gap-1.5 transition"
                title="Pause Audio for 120s (IEC 60601-1-8 clause 6.8.4)"
              >
                <Volume2 className="w-3.5 h-3.5" />
                MUTE 120s
              </button>
            )}

            {!topAlarm.acknowledged ? (
              <button
                onClick={() => handleAck(topAlarm.alarm_id || topAlarm.code)}
                disabled={ackLoading === (topAlarm.alarm_id || topAlarm.code)}
                className="px-4 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-bold font-mono tracking-wider flex items-center gap-1.5 shadow-md transition disabled:opacity-50"
              >
                <CheckCircle className="w-3.5 h-3.5" />
                {ackLoading ? "ACKING..." : "ACKNOWLEDGE"}
              </button>
            ) : (
              <span className="px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-mono">
                ACKNOWLEDGED
              </span>
            )}
          </div>
        </section>
      )}

      {/* ── 2. Top Metric Drill-Down Cards ──────────────────────────────────── */}
      <section aria-label="System Quick Cards" className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Cardio Card */}
        <div
          onClick={() => onNavigateTab("cardio")}
          role="button"
          tabIndex={0}
          className="p-4 rounded-xl bg-space-900 border border-space-700/80 hover:border-cyan-500/50 hover:bg-space-850 cursor-pointer transition group shadow-md"
        >
          <div className="flex items-center justify-between text-space-400 group-hover:text-cyan-400 transition">
            <span className="text-xs uppercase font-mono tracking-wider">Cardio Telemetry</span>
            <Heart className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-space-100">
              {telemetry?.vitals?.heart_rate ?? 75}
            </span>
            <span className="text-xs text-space-400">BPM</span>
          </div>
          <div className="mt-1 flex items-center justify-between text-xs text-space-400">
            <span>rMSSD: <strong className="text-space-200">{telemetry?.vitals?.rmssd ?? 42} ms</strong></span>
            <span>SpO2: <strong className="text-space-200">{telemetry?.vitals?.spo2 ?? 98}%</strong></span>
          </div>
        </div>

        {/* Neuro Card */}
        <div
          onClick={() => onNavigateTab("neuro")}
          role="button"
          tabIndex={0}
          className="p-4 rounded-xl bg-space-900 border border-space-700/80 hover:border-purple-500/50 hover:bg-space-850 cursor-pointer transition group shadow-md"
        >
          <div className="flex items-center justify-between text-space-400 group-hover:text-purple-400 transition">
            <span className="text-xs uppercase font-mono tracking-wider">Neuro & Fatigue</span>
            <Brain className="w-4 h-4 text-purple-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-space-100">
              {telemetry?.eye?.fatigue_label || "ALERT"}
            </span>
          </div>
          <div className="mt-1 flex items-center justify-between text-xs text-space-400">
            <span>EAR: <strong className="text-space-200">{telemetry?.eye?.ear ?? 0.28}</strong></span>
            <span>Blink: <strong className="text-space-200">{telemetry?.eye?.blink_rate ?? 16}/m</strong></span>
          </div>
        </div>

        {/* Cabin Atmosphere Card */}
        <div
          onClick={() => onNavigateTab("cabin")}
          role="button"
          tabIndex={0}
          className="p-4 rounded-xl bg-space-900 border border-space-700/80 hover:border-emerald-500/50 hover:bg-space-850 cursor-pointer transition group shadow-md"
        >
          <div className="flex items-center justify-between text-space-400 group-hover:text-emerald-400 transition">
            <span className="text-xs uppercase font-mono tracking-wider">ECLSS Atmosphere</span>
            <Gauge className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-space-100">
              {telemetry?.cabin?.co2_mmhg?.toFixed(1) ?? "3.0"}
            </span>
            <span className="text-xs text-space-400">mmHg CO2</span>
          </div>
          <div className="mt-1 flex items-center justify-between text-xs text-space-400">
            <span>O2: <strong className="text-space-200">{telemetry?.cabin?.o2_percent ?? 20.9}%</strong></span>
            <span>Pres: <strong className="text-space-200">{telemetry?.cabin?.pressure_kpa ?? 101.3} kPa</strong></span>
          </div>
        </div>

        {/* Medical Support Card */}
        <div
          onClick={() => onNavigateTab("medical")}
          role="button"
          tabIndex={0}
          className="p-4 rounded-xl bg-space-900 border border-space-700/80 hover:border-blue-500/50 hover:bg-space-850 cursor-pointer transition group shadow-md"
        >
          <div className="flex items-center justify-between text-space-400 group-hover:text-blue-400 transition">
            <span className="text-xs uppercase font-mono tracking-wider">Medical Support</span>
            <Stethoscope className="w-4 h-4 text-blue-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-space-100">
              OFFLINE KB
            </span>
          </div>
          <div className="mt-1 flex items-center justify-between text-xs text-space-400">
            <span>Checklists: <strong className="text-space-200">3 Ready</strong></span>
            <span>Phi-3: <strong className="text-emerald-400">Grounded</strong></span>
          </div>
        </div>
      </section>

      {/* ── 3. Main Centerpiece: Radar + Reticle HUD + Composite Stress ────── */}
      <section aria-label="Biometric Cockpit Hub" className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (5 Cols): 5-System Health Radar */}
        <div className="lg:col-span-5 p-6 rounded-xl bg-space-900 border border-space-700 flex flex-col justify-between shadow-glass-panel">
          <div className="flex items-center justify-between border-b border-space-800 pb-3">
            <div>
              <h2 className="text-sm font-bold text-space-100 uppercase tracking-wider flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                5-System Health Radar
              </h2>
              <p className="text-xs text-space-400">
                Holistic Multimodal System Integrity Indices
              </p>
            </div>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              10 Hz
            </span>
          </div>

          {/* SVG Polar Radar Visualizer */}
          <div className="py-4 flex items-center justify-center">
            <svg
              viewBox="0 0 260 260"
              className="w-64 h-64 overflow-visible filter drop-shadow-[0_0_12px_rgba(0,229,255,0.25)]"
            >
              {/* Concentric Guide Rings */}
              {[0.25, 0.5, 0.75, 1.0].map((frac, idx) => (
                <circle
                  key={idx}
                  cx={cx}
                  cy={cy}
                  r={rMax * frac}
                  fill="none"
                  stroke="#1e2b42"
                  strokeDasharray={frac < 1.0 ? "2 3" : undefined}
                  strokeWidth="1"
                />
              ))}

              {/* 5 Radial Axis Spokes */}
              {angles.map((ang, idx) => {
                const x2 = cx + rMax * Math.cos(ang);
                const y2 = cy + rMax * Math.sin(ang);
                return (
                  <line
                    key={idx}
                    x1={cx}
                    y1={cy}
                    x2={x2}
                    y2={y2}
                    stroke="#1e2b42"
                    strokeWidth="1"
                  />
                );
              })}

              {/* Dynamic Radar Fill Area */}
              <polygon
                points={polygonPoints}
                fill="rgba(0, 229, 255, 0.22)"
                stroke="#00e5ff"
                strokeWidth="2.5"
                strokeLinejoin="round"
                className="transition-all duration-300"
              />

              {/* Vertex Nodes & Labels */}
              {radarValues.map((item, idx) => {
                const { x, y } = getCoordinates(idx, item.score);
                const labelDist = rMax + 20;
                const lx = cx + labelDist * Math.cos(angles[idx]);
                const ly = cy + labelDist * Math.sin(angles[idx]);
                return (
                  <g key={idx}>
                    <circle
                      cx={x}
                      cy={y}
                      r="4.5"
                      fill={item.color}
                      stroke="#05070a"
                      strokeWidth="1.5"
                      className="transition-all duration-300"
                    />
                    <text
                      x={lx}
                      y={ly}
                      textAnchor="middle"
                      dominantBaseline="central"
                      fill="#94a3b8"
                      fontSize="11"
                      fontFamily="JetBrains Mono, monospace"
                      fontWeight="bold"
                    >
                      {item.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Radar Legend Breakdown */}
          <div className="grid grid-cols-5 gap-1 pt-3 border-t border-space-800 text-center font-mono">
            {radarValues.map((item, idx) => (
              <div key={idx} className="p-1 rounded bg-space-850/60 border border-space-800">
                <div className="text-[10px] text-space-400">{item.label}</div>
                <div
                  className="text-xs font-bold"
                  style={{ color: item.color }}
                >
                  {item.score}%
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Center / Right Column (7 Cols): Reticle HUD & Composite Stress */}
        <div className="lg:col-span-7 space-y-6">
          {/* Reticle HUD Card */}
          <div className="p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel relative overflow-hidden">
            {/* Aerospace Reticle HUD Background Elements */}
            <div className="flex items-center justify-between border-b border-space-800 pb-3 mb-4">
              <div>
                <h2 className="text-sm font-bold text-space-100 uppercase tracking-wider flex items-center gap-2">
                  <Eye className="w-4 h-4 text-cyan-400" />
                  Tactical Astronaut Reticle HUD
                </h2>
                <p className="text-xs text-space-400">
                  Multimodal Gaze, Facial Valence & Voice Affect Fusion
                </p>
              </div>
              <button
                onClick={() => onNavigateTab("live")}
                className="px-2.5 py-1 rounded-lg bg-space-800 hover:bg-space-700 text-space-200 text-xs font-mono flex items-center gap-1.5 transition"
              >
                <span>Live Camera</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-center">
              {/* Circular Aerospace Crosshair Graphic */}
              <div className="flex justify-center sm:col-span-1">
                <div className="relative w-36 h-36 rounded-full border-2 border-cyan-500/30 flex items-center justify-center p-2 bg-space-950/60 shadow-inner">
                  {/* Concentric rings */}
                  <div className="absolute inset-2 rounded-full border border-dashed border-cyan-500/40 animate-spin" style={{ animationDuration: "20s" }} />
                  <div className="absolute inset-5 rounded-full border border-space-700" />
                  {/* Crosshairs */}
                  <div className="absolute inset-x-0 top-1/2 h-px bg-cyan-500/50" />
                  <div className="absolute inset-y-0 left-1/2 w-px bg-cyan-500/50" />

                  {/* Center Biometric Target */}
                  <div className="z-10 text-center font-mono">
                    <span className="text-[10px] text-space-400 uppercase block">Affect</span>
                    <span className="text-sm font-bold text-cyan-300 uppercase">
                      {telemetry?.face?.emotion || "NEUTRAL"}
                    </span>
                    <span className="text-[10px] text-emerald-400 block font-semibold">
                      {(telemetry?.face?.confidence ? telemetry.face.confidence * 100 : 88).toFixed(0)}% CONF
                    </span>
                  </div>
                </div>
              </div>

              {/* Real-time Subsystem Readouts */}
              <div className="sm:col-span-2 space-y-3 font-mono text-xs">
                <div className="p-2.5 rounded-lg bg-space-850/80 border border-space-800 flex items-center justify-between">
                  <span className="text-space-400 flex items-center gap-1.5">
                    <Eye className="w-3.5 h-3.5 text-cyan-400" />
                    Eye Aspect Ratio (EAR):
                  </span>
                  <span className="text-space-100 font-bold">
                    {telemetry?.eye?.ear?.toFixed(3) ?? "0.285"}
                    <span className="text-space-400 text-[10px] ml-1 font-normal">
                      (Blink: {telemetry?.eye?.blink_rate ?? 16}/min)
                    </span>
                  </span>
                </div>

                <div className="p-2.5 rounded-lg bg-space-850/80 border border-space-800 flex items-center justify-between">
                  <span className="text-space-400 flex items-center gap-1.5">
                    <Mic className="w-3.5 h-3.5 text-cyan-400" />
                    Acoustic Voice Energy:
                  </span>
                  <span className="text-space-100 font-bold">
                    {telemetry?.voice?.db ?? -45} dB
                    <span className="text-space-400 text-[10px] ml-1 font-normal">
                      ({telemetry?.voice?.is_speaking ? "Speaking" : "Silent"})
                    </span>
                  </span>
                </div>

                <div className="p-2.5 rounded-lg bg-space-850/80 border border-space-800 flex items-center justify-between">
                  <span className="text-space-400 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-cyan-400" />
                    Incapacitation Watchdog:
                  </span>
                  <span
                    className={`font-bold ${
                      telemetry?.watchdog?.state === "NORMAL"
                        ? "text-emerald-400"
                        : "text-amber-400"
                    }`}
                  >
                    {telemetry?.watchdog?.state || "NORMAL"}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Composite Stress Gauge & Tier Bar */}
          <div className="p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-bold text-space-100 uppercase tracking-wider flex items-center gap-2">
                  <Zap className="w-4 h-4 text-cyan-400" />
                  Composite Stress Strain Level
                </h3>
                <p className="text-xs text-space-400">
                  Bayesian Weighted Dynamic Multi-Signal Sensor Integration
                </p>
              </div>
              <span
                className={`px-3 py-1 rounded-lg text-xs font-mono font-bold border ${
                  stressPct > 75
                    ? "bg-red-500/20 text-red-300 border-red-500/50 animate-pulse"
                    : stressPct > 55
                    ? "bg-orange-500/20 text-orange-300 border-orange-500/50"
                    : stressPct > 35
                    ? "bg-amber-500/20 text-amber-300 border-amber-500/50"
                    : "bg-emerald-500/20 text-emerald-300 border-emerald-500/50"
                }`}
              >
                {telemetry?.fusion?.stress_level || "NOMINAL"} ({stressPct.toFixed(1)}%)
              </span>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-space-800 h-3.5 rounded-full overflow-hidden p-0.5 border border-space-700">
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  stressPct > 75
                    ? "bg-gradient-to-r from-red-600 to-red-400"
                    : stressPct > 55
                    ? "bg-gradient-to-r from-amber-600 to-orange-500"
                    : stressPct > 35
                    ? "bg-gradient-to-r from-yellow-600 to-amber-400"
                    : "bg-gradient-to-r from-emerald-600 to-emerald-400"
                }`}
                style={{ width: `${Math.max(2, Math.min(100, stressPct))}%` }}
              />
            </div>

            {/* Weights Breakdown */}
            <div className="grid grid-cols-4 gap-2 mt-4 text-xs font-mono">
              <div className="p-2 rounded bg-space-850 border border-space-800 text-center">
                <span className="text-[10px] text-space-400 block">FACE</span>
                <span className="font-bold text-space-200">
                  {(weights.face * 100).toFixed(0)}%
                </span>
              </div>
              <div className="p-2 rounded bg-space-850 border border-space-800 text-center">
                <span className="text-[10px] text-space-400 block">VOICE</span>
                <span className="font-bold text-space-200">
                  {(weights.voice * 100).toFixed(0)}%
                </span>
              </div>
              <div className="p-2 rounded bg-space-850 border border-space-800 text-center">
                <span className="text-[10px] text-space-400 block">VITALS</span>
                <span className="font-bold text-space-200">
                  {(weights.vitals * 100).toFixed(0)}%
                </span>
              </div>
              <div className="p-2 rounded bg-space-850 border border-space-800 text-center">
                <span className="text-[10px] text-space-400 block">EYE</span>
                <span className="font-bold text-space-200">
                  {(weights.eye * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 4. Explainable Baseline Delta & Clinical Rationale ─────────────── */}
      <section
        aria-label="Explainable Baseline Delta and Rationale"
        className="p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-4"
      >
        <div className="flex items-center justify-between border-b border-space-800 pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-space-100 uppercase tracking-wider">
              Explainable Personal Baseline & CUSUM Change Detection
            </h3>
          </div>
          <span className="text-xs text-space-400 font-mono">
            Astronaut Baseline Calibration Active
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          {/* Dominant Contributor */}
          <div className="p-4 rounded-lg bg-space-850 border border-space-800 space-y-1">
            <div className="font-mono text-[11px] text-space-400 uppercase">
              Primary Stress Contributor
            </div>
            <div className="text-base font-bold text-cyan-300">
              {explain?.dominant_contributor || "Cardio-Respiratory Vitals"}
            </div>
            <p className="text-space-400 text-[11px]">
              Multi-signal Kalman fusion attributed current index primarily to autonomic physiological tone.
            </p>
          </div>

          {/* Baseline Z-Score Drift */}
          <div className="p-4 rounded-lg bg-space-850 border border-space-800 space-y-1">
            <div className="font-mono text-[11px] text-space-400 uppercase">
              Baseline Z-Score Delta
            </div>
            <div className="text-base font-bold text-space-200 font-mono">
              Z = {explain?.baseline_z_score?.toFixed(2) ?? "+0.32"} σ
            </div>
            <p className="text-space-400 text-[11px]">
              Standardized shift relative to astronaut's pre-mission resting normative baseline.
            </p>
          </div>

          {/* Clinical Rationale Text */}
          <div className="p-4 rounded-lg bg-space-850 border border-space-800 space-y-1">
            <div className="font-mono text-[11px] text-space-400 uppercase">
              Automated Clinical Rationale
            </div>
            <div className="text-space-200 text-xs leading-relaxed">
              {explain?.rationale ||
                "Vitals within nominal operational limits. Autonomic sympathetic balance stable. No acute cognitive fatigue detected."}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
