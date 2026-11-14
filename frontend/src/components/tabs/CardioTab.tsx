import React, { useEffect, useRef, useState } from "react";
import { TelemetryPayload, SensorAdapterStatus } from "../../types";
import {
  fetchSensors,
  setSensorMode,
  setSensorScenario,
} from "../../services/api";
import { telemetrySocketService } from "../../services/telemetrySocket";
import {
  Heart,
  Activity,
  Sliders,
  Play,
  CheckCircle,
  AlertTriangle,
  RotateCcw,
  Gauge,
  Thermometer,
  Wind,
  Shield,
  Info,
} from "lucide-react";

interface CardioTabProps {
  telemetry: TelemetryPayload | null;
}

export const CardioTab: React.FC<CardioTabProps> = ({ telemetry }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Sensor Adapter status
  const [adapterStatus, setAdapterStatus] = useState<SensorAdapterStatus | null>(
    telemetry?.sensor_adapter || null
  );
  const [currentMode, setCurrentMode] = useState<"live" | "manual" | "replay">(
    telemetry?.sensor_adapter?.mode || "replay"
  );
  const [currentScenario, setCurrentScenario] = useState<string>("nominal_flight");
  const [replaySpeed, setReplaySpeed] = useState<number>(1.0);
  const [isUpdatingAdapter, setIsUpdatingAdapter] = useState<boolean>(false);

  // Manual adjustment state
  const [manualHr, setManualHr] = useState<number>(
    telemetry?.vitals?.heart_rate ?? 75
  );
  const [manualSpo2, setManualSpo2] = useState<number>(
    telemetry?.vitals?.spo2 ?? 98
  );
  const [manualTemp, setManualTemp] = useState<number>(
    telemetry?.vitals?.temperature ?? 36.6
  );
  const [manualResp, setManualResp] = useState<number>(
    telemetry?.vitals?.respiratory_rate ?? 14
  );
  const [manualRmssd, setManualRmssd] = useState<number>(
    telemetry?.vitals?.rmssd ?? 42
  );

  // Fetch adapter status on mount
  useEffect(() => {
    fetchSensors()
      .then((data) => {
        setAdapterStatus(data);
        if (data.mode) setCurrentMode(data.mode);
        if (data.scenario) setCurrentScenario(data.scenario);
        if (data.replay_speed) setReplaySpeed(data.replay_speed);
      })
      .catch(() => {});
  }, []);

  // Sync incoming telemetry
  useEffect(() => {
    if (telemetry?.sensor_adapter) {
      setAdapterStatus(telemetry.sensor_adapter);
    }
  }, [telemetry?.sensor_adapter]);

  // Handle mode change
  const handleModeChange = async (mode: "live" | "manual" | "replay") => {
    setIsUpdatingAdapter(true);
    try {
      await setSensorMode(mode);
      setCurrentMode(mode);
    } finally {
      setIsUpdatingAdapter(false);
    }
  };

  // Handle scenario change
  const handleScenarioChange = async (scenario: string, speed = replaySpeed) => {
    setIsUpdatingAdapter(true);
    try {
      await setSensorScenario(scenario, speed);
      setCurrentScenario(scenario);
    } finally {
      setIsUpdatingAdapter(false);
    }
  };

  // ── Continuous Lead-II ECG Waveform Canvas Render Loop ─────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let sweepX = 0;
    const hrVal = telemetry?.vitals?.heart_rate ?? manualHr ?? 75;
    // Calculate cardiac period in seconds (e.g. 75 bpm -> 0.8s)
    const bps = Math.max(0.5, hrVal / 60.0);

    const width = canvas.width;
    const height = canvas.height;
    const midY = height / 2;

    // Buffer of points to render sweep
    const points: number[] = new Array(width).fill(midY);
    let sampleCounter = 0;

    const render = () => {
      // Advance sweep
      const samplesPerFrame = 3;
      for (let s = 0; s < samplesPerFrame; s++) {
        sampleCounter++;
        // Lead-II synthetic waveform generator (P-Q-R-S-T)
        // Cycle phase from 0 to 1
        const cycleProgress = (sampleCounter % Math.round(180 / bps)) / (180 / bps);
        let amp = 0;

        if (cycleProgress >= 0.12 && cycleProgress <= 0.20) {
          // P Wave (atrial depolarization)
          amp = 8 * Math.sin(((cycleProgress - 0.12) / 0.08) * Math.PI);
        } else if (cycleProgress >= 0.26 && cycleProgress < 0.28) {
          // Q Wave (septal depolarization)
          amp = -6;
        } else if (cycleProgress >= 0.28 && cycleProgress <= 0.33) {
          // R Wave (ventricular depolarization peak)
          amp = 48 * Math.sin(((cycleProgress - 0.28) / 0.05) * Math.PI);
        } else if (cycleProgress > 0.33 && cycleProgress <= 0.36) {
          // S Wave (late ventricular)
          amp = -14 * Math.sin(((cycleProgress - 0.33) / 0.03) * Math.PI);
        } else if (cycleProgress >= 0.44 && cycleProgress <= 0.58) {
          // T Wave (ventricular repolarization)
          amp = 14 * Math.sin(((cycleProgress - 0.44) / 0.14) * Math.PI);
        }

        points[sweepX] = midY - amp;
        sweepX = (sweepX + 1) % width;
      }

      // Draw background grid
      ctx.fillStyle = "#070c14";
      ctx.fillRect(0, 0, width, height);

      // Medical ECG Grid (5mm & 1mm style)
      ctx.strokeStyle = "rgba(14, 30, 48, 0.7)";
      ctx.lineWidth = 0.5;
      for (let x = 0; x < width; x += 15) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += 15) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Major grid (75px)
      ctx.strokeStyle = "rgba(0, 229, 255, 0.08)";
      ctx.lineWidth = 1;
      for (let x = 0; x < width; x += 75) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += 75) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Erase bar ahead of sweep
      const eraseWidth = 20;
      ctx.fillStyle = "#070c14";
      ctx.fillRect(sweepX, 0, eraseWidth, height);

      // Render ECG Waveform trace
      ctx.beginPath();
      ctx.strokeStyle = hrVal > 110 ? "#f87171" : hrVal < 50 ? "#facc15" : "#00e5ff";
      ctx.lineWidth = 2;
      ctx.shadowColor = ctx.strokeStyle;
      ctx.shadowBlur = 8;

      let first = true;
      for (let i = 0; i < width; i++) {
        if (i >= sweepX && i < sweepX + eraseWidth) {
          first = true;
          continue;
        }
        if (first) {
          ctx.moveTo(i, points[i]);
          first = false;
        } else {
          ctx.lineTo(i, points[i]);
        }
      }
      ctx.stroke();
      ctx.shadowBlur = 0;

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animId);
  }, [telemetry?.vitals?.heart_rate, manualHr]);

  // Derived metrics
  const hr = telemetry?.vitals?.heart_rate ?? manualHr;
  const spo2 = telemetry?.vitals?.spo2 ?? manualSpo2;
  const temp = telemetry?.vitals?.temperature ?? manualTemp;
  const rmssd = telemetry?.vitals?.rmssd ?? manualRmssd;
  const sdnn = telemetry?.vitals?.sdnn ?? Math.round(rmssd * 1.3);
  const resp = telemetry?.vitals?.respiratory_rate ?? manualResp;
  const baevsky = telemetry?.vitals?.baevsky_index ?? 95.0;

  const baevskyCategory =
    baevsky < 50
      ? "Vagotonic Predominance"
      : baevsky <= 150
      ? "Nominal Autonomic Balance"
      : baevsky <= 300
      ? "Moderate Sympathetic Strain"
      : "Severe Autonomic Exhaustion";

  const baevskyColor =
    baevsky <= 150 ? "text-emerald-400" : baevsky <= 300 ? "text-amber-400" : "text-red-400";

  return (
    <div className="space-y-6">
      {/* ── 1. Top Section: Live ECG Waveform Monitor ──────────────────────── */}
      <section
        aria-label="Lead-II Electrocardiogram"
        className="p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel relative overflow-hidden"
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-space-800 pb-3 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-cyan-400 animate-pulse" />
              <h2 className="text-sm font-bold text-space-100 uppercase tracking-wider">
                Continuous Lead-II Electrocardiogram (ECG) & Rhythm Monitor
              </h2>
            </div>
            <p className="text-xs text-space-400">
              Calibrated 25 mm/s Sweep Velocity • Standard 10 mm/mV Sensitivity • Air-Gapped
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              LEAD II NOMINAL
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              FILTER: 0.05 - 150 Hz
            </span>
          </div>
        </div>

        {/* ECG Waveform Canvas */}
        <div className="w-full h-48 md:h-56 rounded-lg overflow-hidden border border-space-800 bg-[#070c14] relative">
          <canvas
            ref={canvasRef}
            width={900}
            height={220}
            className="w-full h-full block"
          />
          {/* HUD Overlay Stats inside Canvas */}
          <div className="absolute top-3 left-3 flex items-center gap-4 bg-space-950/80 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-space-800 font-mono text-xs">
            <div className="flex items-center gap-1.5">
              <Heart className="w-3.5 h-3.5 text-red-400" />
              <span className="text-space-300">HR:</span>
              <span className="text-space-100 font-bold">{hr} BPM</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Gauge className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-space-300">SpO2:</span>
              <span className="text-space-100 font-bold">{spo2}%</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Thermometer className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-space-300">TEMP:</span>
              <span className="text-space-100 font-bold">{temp.toFixed(1)}°C</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── 2. HRV Spectrum & Baevsky Stress Index Panel ──────────────────── */}
      <section
        aria-label="Heart Rate Variability and Autonomic Metrics"
        className="grid grid-cols-1 lg:grid-cols-12 gap-6"
      >
        {/* Left Column (7 Cols): HRV Spectrum Indices */}
        <div className="lg:col-span-7 p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-4">
          <div className="flex items-center justify-between border-b border-space-800 pb-3">
            <div>
              <h3 className="text-sm font-bold text-space-100 uppercase tracking-wider flex items-center gap-2">
                <Gauge className="w-4 h-4 text-cyan-400" />
                Autonomic HRV Spectrum & Time-Domain Metrics
              </h3>
              <p className="text-xs text-space-400">
                Parasympathetic Tone & Sympathetic Autonomic Balance
              </p>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-space-800 text-space-300 border border-space-700">
              NASA-STD-3001
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {/* rMSSD */}
            <div className="p-3.5 rounded-lg bg-space-850 border border-space-800 space-y-1">
              <div className="text-[10px] font-mono text-space-400 uppercase">
                rMSSD (Vagal Tone)
              </div>
              <div className="text-xl font-bold font-mono text-cyan-300">
                {rmssd.toFixed(1)} <span className="text-xs text-space-400 font-normal">ms</span>
              </div>
              <p className="text-[10px] text-space-400">
                Successive RR differences. Higher values signify robust parasympathetic reserve.
              </p>
            </div>

            {/* SDNN */}
            <div className="p-3.5 rounded-lg bg-space-850 border border-space-800 space-y-1">
              <div className="text-[10px] font-mono text-space-400 uppercase">
                SDNN (Total Variability)
              </div>
              <div className="text-xl font-bold font-mono text-purple-300">
                {sdnn.toFixed(1)} <span className="text-xs text-space-400 font-normal">ms</span>
              </div>
              <p className="text-[10px] text-space-400">
                Standard deviation of NN intervals. Reflects total circadian autonomic variability.
              </p>
            </div>

            {/* Respiratory Rate */}
            <div className="p-3.5 rounded-lg bg-space-850 border border-space-800 space-y-1">
              <div className="text-[10px] font-mono text-space-400 uppercase">
                Respiratory Rate
              </div>
              <div className="text-xl font-bold font-mono text-emerald-300">
                {resp.toFixed(1)} <span className="text-xs text-space-400 font-normal">brpm</span>
              </div>
              <p className="text-[10px] text-space-400">
                Respiratory sinus arrhythmia coupling. Eupneic resting baseline (12–18).
              </p>
            </div>
          </div>

          {/* Autonomic Balance Explanation Notice */}
          <div className="p-3.5 rounded-lg bg-space-950 border border-space-800 flex items-start gap-3 text-xs text-space-300">
            <Info className="w-4 h-4 text-cyan-400 mt-0.5 shrink-0" />
            <p>
              In microgravity, cephalad fluid shift elevates cardiac filling pressures and suppresses rMSSD
              during initial adaptation. Prolonged suppression below 20 ms warrants countermeasure review.
            </p>
          </div>
        </div>

        {/* Right Column (5 Cols): Baevsky Stress Index Gauge */}
        <div className="lg:col-span-5 p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel flex flex-col justify-between">
          <div className="border-b border-space-800 pb-3">
            <h3 className="text-sm font-bold text-space-100 uppercase tracking-wider flex items-center gap-2">
              <Shield className="w-4 h-4 text-amber-400" />
              Baevsky Stress Index Gauge (SI)
            </h3>
            <p className="text-xs text-space-400">
              Russian Spaceflight Biomedical Standard (Mir / ISS Standard)
            </p>
          </div>

          <div className="py-4 flex flex-col items-center justify-center text-center space-y-2">
            <div className="text-4xl font-extrabold font-mono text-space-100">
              {baevsky.toFixed(0)}
              <span className="text-xs font-normal text-space-400 ml-1">SI units</span>
            </div>
            <div className={`text-xs font-bold uppercase tracking-wider font-mono ${baevskyColor}`}>
              {baevskyCategory}
            </div>

            {/* Gauge Indicator Bar */}
            <div className="w-full max-w-xs mt-3">
              <div className="h-3 rounded-full bg-space-800 overflow-hidden flex border border-space-700">
                <div className="w-1/3 bg-emerald-500/80 h-full" title="Nominal (50-150)" />
                <div className="w-1/3 bg-amber-500/80 h-full" title="Moderate (150-300)" />
                <div className="w-1/3 bg-red-500/80 h-full" title="Severe (>300)" />
              </div>
              <div className="flex justify-between text-[10px] font-mono text-space-400 mt-1">
                <span>0</span>
                <span>150</span>
                <span>300</span>
                <span>500+</span>
              </div>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-space-850/80 border border-space-800 text-[11px] text-space-400 font-mono">
            Formula: SI = AMo / (2 • Mo • MxDMn) • Evaluates sympathetic regulatory strain.
          </div>
        </div>
      </section>

      {/* ── 3. Sensor Adapter Controls (Live / Manual / Replay) ───────────── */}
      <section
        aria-label="Hardware Sensor Adapter Controls"
        className="p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-6"
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-space-800 pb-3">
          <div>
            <h3 className="text-sm font-bold text-space-100 uppercase tracking-wider flex items-center gap-2">
              <Sliders className="w-4 h-4 text-cyan-400" />
              Hardware Sensor Adapter &amp; Scenario Simulator Controls
            </h3>
            <p className="text-xs text-space-400">
              Documented Spaceflight Sensor Interface • Switch Between Real Hardware, Manual Testing, and Deterministic Scenarios
            </p>
          </div>

          {/* Mode Selector Radio Pills */}
          <div className="flex items-center gap-1 bg-space-950 p-1 rounded-lg border border-space-800">
            {(["live", "manual", "replay"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => handleModeChange(mode)}
                disabled={isUpdatingAdapter}
                className={`px-3 py-1 rounded text-xs font-mono font-bold uppercase transition ${
                  currentMode === mode
                    ? "bg-cyan-600 text-white shadow-sm"
                    : "text-space-400 hover:text-space-200"
                }`}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>

        {/* Mode Dependent Panels */}
        {currentMode === "replay" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-space-300 font-mono uppercase tracking-wider">
                Select Deterministic Spaceflight Scenario:
              </span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-space-400 font-mono">
                  Speed: {replaySpeed.toFixed(1)}x
                </span>
                <input
                  type="range"
                  min="0.5"
                  max="5.0"
                  step="0.5"
                  value={replaySpeed}
                  onChange={(e) => {
                    const sp = parseFloat(e.target.value);
                    setReplaySpeed(sp);
                    handleScenarioChange(currentScenario, sp);
                  }}
                  className="w-24 accent-cyan-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                {
                  id: "nominal_flight",
                  title: "Nominal Flight",
                  desc: "Resting astronaut physiology, baseline HRV, nominal cabin atmosphere.",
                  tag: "BASELINE",
                },
                {
                  id: "co2_retention",
                  title: "CO2 Retention Hazard",
                  desc: "ECLSS scrubber anomaly, progressive hypercapnia, Law 2014 cephalalgia.",
                  tag: "ECLSS HAZARD",
                },
                {
                  id: "eva_strain",
                  title: "EVA Heavy Exertion",
                  desc: "Spacewalk metabolic expenditure, tachycardia, tachypnea, sympathetic surge.",
                  tag: "METABOLIC",
                },
                {
                  id: "solar_flare",
                  title: "Solar Particle Event",
                  desc: "SPE radiation storm warning, crew shelter protocols, acute stress response.",
                  tag: "SPACE HAZARD",
                },
              ].map((sc) => (
                <button
                  key={sc.id}
                  onClick={() => handleScenarioChange(sc.id)}
                  disabled={isUpdatingAdapter}
                  className={`p-4 rounded-lg border text-left transition space-y-1.5 ${
                    currentScenario === sc.id
                      ? "bg-cyan-950/40 border-cyan-500 shadow-glow-nominal"
                      : "bg-space-850 border-space-800 hover:border-space-700"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs text-space-100">{sc.title}</span>
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-space-950 text-cyan-400 border border-space-800">
                      {sc.tag}
                    </span>
                  </div>
                  <p className="text-[11px] text-space-400 leading-snug">{sc.desc}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {currentMode === "manual" && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Heart Rate Slider */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-space-300">Heart Rate (BPM):</span>
                <span className="text-cyan-400 font-bold">{manualHr} BPM</span>
              </div>
              <input
                type="range"
                min="40"
                max="180"
                value={manualHr}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  setManualHr(val);
                  telemetrySocketService.sendVitalsUpdate(val, manualTemp, manualSpo2, manualResp, manualRmssd);
                }}
                className="w-full accent-cyan-500"
              />
            </div>

            {/* SpO2 Slider */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-space-300">SpO2 Oxygen Saturation:</span>
                <span className="text-cyan-400 font-bold">{manualSpo2}%</span>
              </div>
              <input
                type="range"
                min="80"
                max="100"
                value={manualSpo2}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  setManualSpo2(val);
                  telemetrySocketService.sendVitalsUpdate(manualHr, manualTemp, val, manualResp, manualRmssd);
                }}
                className="w-full accent-cyan-500"
              />
            </div>

            {/* rMSSD Slider */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-space-300">rMSSD Vagal Index:</span>
                <span className="text-cyan-400 font-bold">{manualRmssd} ms</span>
              </div>
              <input
                type="range"
                min="10"
                max="120"
                value={manualRmssd}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  setManualRmssd(val);
                  telemetrySocketService.sendVitalsUpdate(manualHr, manualTemp, manualSpo2, manualResp, val);
                }}
                className="w-full accent-cyan-500"
              />
            </div>
          </div>
        )}

        {currentMode === "live" && (
          <div className="p-4 rounded-lg bg-space-950 border border-space-800 flex items-center gap-3 text-xs text-space-300">
            <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />
            <div>
              <p className="font-semibold text-space-100">Live Hardware Adapter Active</p>
              <p className="text-space-400 text-[11px]">
                Streaming raw biometric frames from connected USB pulse oximeter or optical rPPG video channel.
              </p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
};
