import React, { useState, useEffect } from "react";
import { TelemetryPayload, Law2014Hazard, CabinTelemetry } from "../../types";
import {
  fetchCabinEnvironment,
  updateCabinEnvironment,
  fetchCo2HazardModel,
} from "../../services/api";
import {
  Gauge,
  Thermometer,
  Wind,
  Volume2,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  Sliders,
  Send,
  Sparkles,
  RefreshCw,
  Activity,
  HeartPulse,
} from "lucide-react";

interface CabinTabProps {
  telemetry: TelemetryPayload | null;
}

export const CabinTab: React.FC<CabinTabProps> = ({ telemetry }) => {
  const [cabinCo2, setCabinCo2] = useState<number>(
    telemetry?.cabin?.co2_mmhg ?? 3.0
  );
  const [cabinO2, setCabinO2] = useState<number>(
    telemetry?.cabin?.o2_percent ?? 20.9
  );
  const [cabinPressure, setCabinPressure] = useState<number>(
    telemetry?.cabin?.pressure_kpa ?? 101.3
  );
  const [cabinTemp, setCabinTemp] = useState<number>(
    telemetry?.cabin?.ambient_temp_c ?? 22.0
  );
  const [cabinNoise, setCabinNoise] = useState<number>(
    telemetry?.cabin?.noise_dba ?? 58.0
  );

  const [hazardModel, setHazardModel] = useState<Law2014Hazard | null>(null);
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [selectedSymptom, setSelectedSymptom] = useState<string>("headache");

  // Sync telemetry
  useEffect(() => {
    if (telemetry?.cabin) {
      setCabinCo2(telemetry.cabin.co2_mmhg);
      setCabinO2(telemetry.cabin.o2_percent);
      setCabinPressure(telemetry.cabin.pressure_kpa);
      setCabinTemp(telemetry.cabin.ambient_temp_c);
      setCabinNoise(telemetry.cabin.noise_dba);
      if (telemetry.cabin.co2_headache_hazard) {
        setHazardModel(telemetry.cabin.co2_headache_hazard);
      }
    }
  }, [telemetry?.cabin]);

  // Compute hazard model when CO2 changes
  useEffect(() => {
    fetchCo2HazardModel(cabinCo2)
      .then((data) => setHazardModel(data))
      .catch(() => {});
  }, [cabinCo2]);

  // Submit manual update
  const handleUpdateEnvironment = async () => {
    setIsUpdating(true);
    try {
      const res = await updateCabinEnvironment({
        cabin_co2: cabinCo2,
        cabin_o2: cabinO2,
        cabin_pressure: cabinPressure,
        cabin_temp: cabinTemp,
        cabin_noise: cabinNoise,
      });
      if (res.co2_headache_hazard) {
        setHazardModel(res.co2_headache_hazard);
      }
    } finally {
      setIsUpdating(false);
    }
  };

  // PPM conversion approx: 1 mmHg ~ 1315 ppm at standard pressure
  const co2Ppm = Math.round(cabinCo2 * 1315.8);

  // ── Spaceflight Symptoms Triage Data ─────────────────────────────────────────
  const SYMPTOMS: Record<
    string,
    {
      title: string;
      severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
      causes: string[];
      mitigations: string[];
      medicalKit: string;
    }
  > = {
    headache: {
      title: "Cephalalgia & Frontal Headaches",
      severity: cabinCo2 >= 4.5 ? "HIGH" : "MEDIUM",
      causes: [
        `Cabin PCO2 elevation (${cabinCo2.toFixed(1)} mmHg vs 2.0 baseline; 2x odds per 1 mmHg per Law 2014).`,
        "Localized expired CO2 bubble accumulation in poorly ventilated crew quarters.",
        "Cephalad venous engorgement causing elevated intracranial venous pressure.",
      ],
      mitigations: [
        "Inspect and increase bunk personal airflow fan velocity (>25 ft/min).",
        "Switch CDRA / METOX ECLSS scrubbers to maximum regeneration mode.",
        "Ensure oral hydration (500 mL water with electrolytes).",
      ],
      medicalKit: "Acetaminophen 650-1000 mg PO or Ibuprofen 400-600 mg PO.",
    },
    sms: {
      title: "Space Motion Sickness (SMS) & Nausea",
      severity: "HIGH",
      causes: [
        "Sensory conflict between otolith organs (no gravity vector) and semicircular canals.",
        "Visual-vestibular mismatch during early flight days 1–4.",
      ],
      mitigations: [
        "Restrict rapid pitch and yaw head angular motions.",
        "Anchor visual gaze to fixed high-contrast cabin horizon reference.",
        "Suspend non-critical microgravity EVA operations.",
      ],
      medicalKit: "Promethazine 25-50 mg IM or PO; Scopolamine transdermal patch.",
    },
    sans: {
      title: "Visual Acuity Degradation & SANS Blur",
      severity: "HIGH",
      causes: [
        "Cephalad fluid shift altering translaminar cribrosa pressure gradient.",
        "Optic disc edema (papilledema), choroidal folds, and globe flattening.",
        "Microgravity hyperopic refractive shift.",
      ],
      mitigations: [
        "Perform fundoscopy and optical coherence tomography (OCT) scan.",
        "Deploy adjustable focal 'Space Anticipation Glasses'.",
        "Schedule Lower Body Negative Pressure (LBNP) session (20-30 mmHg).",
      ],
      medicalKit: "Document Snellen log; notify Flight Surgeon for telemedicine review.",
    },
    lethargy: {
      title: "Cognitive Fatigue, Somnolence & Lethargy",
      severity: "MEDIUM",
      causes: [
        "Cumulative circadian sleep debt (> 5 hours deficit).",
        "Elevated cabin PCO2 producing sedative hypercapnic narcosis.",
        "Melatonin suppression from high melanopic blue light in work modules.",
      ],
      mitigations: [
        "Execute 3-minute PVT-B self-test to benchmark lapse frequency.",
        "Enforce 620 nm low-melatonin circadian lighting mode 2h before sleep.",
        "Schedule 30-minute nap countermeasure if off-duty.",
      ],
      medicalKit: "Caffeine 100-200 mg PO (avoid within 6h of sleep window).",
    },
    irritation: {
      title: "Mucosal Dryness & Respiratory Irritation",
      severity: "LOW",
      causes: [
        "Low cabin relative humidity (< 30% during high ECLSS condensing).",
        "Free-floating particulate matter (skin flakes, lint, aerosolized crumbs).",
      ],
      mitigations: [
        "Inspect HEPA filter intake grilles for debris clogging.",
        "Apply saline nasal spray and ocular lubricating drops.",
        "Wear particulate eye shield if performing equipment maintenance.",
      ],
      medicalKit: "Artificial tears eye drops; normal saline nasal spray.",
    },
  };

  // SVG Law 2014 Odds Ratio Curve
  // Curve from CO2 = 1.0 to 8.0 mmHg
  // OR = 2.0^(CO2 - 2.0)
  const curvePoints: { x: number; y: number }[] = [];
  const svgW = 360;
  const svgH = 140;
  for (let c = 1.0; c <= 8.0; c += 0.25) {
    const delta = Math.max(0, c - 2.0);
    const orVal = Math.pow(2.0, delta);
    const x = ((c - 1.0) / 7.0) * (svgW - 40) + 20;
    const y = svgH - 20 - (Math.min(16, orVal) / 16) * (svgH - 40);
    curvePoints.push({ x, y });
  }
  const pathD = curvePoints.reduce(
    (acc, pt, idx) => (idx === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`),
    ""
  );

  // Astronaut current point
  const currentDelta = Math.max(0, cabinCo2 - 2.0);
  const currentOr = Math.pow(2.0, currentDelta);
  const currentX = ((Math.min(8.0, Math.max(1.0, cabinCo2)) - 1.0) / 7.0) * (svgW - 40) + 20;
  const currentY = svgH - 20 - (Math.min(16, currentOr) / 16) * (svgH - 40);

  return (
    <div className="space-y-6">
      {/* ── 1. Top Section: ECLSS Atmospheric Life-Support Gauges ──────────── */}
      <section
        aria-label="ECLSS Atmospheric Telemetry"
        className="p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-6"
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-space-800 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <Gauge className="w-5 h-5 text-emerald-400" />
              <h2 className="text-sm font-bold text-space-100 uppercase tracking-wider">
                ECLSS Life-Support Atmospheric Telemetry
              </h2>
            </div>
            <p className="text-xs text-space-400">
              NASA-STD-3001 Vol 2 Environmental Limits • Continuous Environmental Sensor Bus
            </p>
          </div>

          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            ECLSS AUTONOMOUS NOMINAL
          </span>
        </div>

        {/* 5 Environmental Metric Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {/* CO2 */}
          <div
            className={`p-4 rounded-xl border space-y-1 transition ${
              cabinCo2 >= 4.5
                ? "bg-red-950/40 border-red-500/60 shadow-glow-critical animate-pulse"
                : cabinCo2 >= 3.5
                ? "bg-amber-950/30 border-amber-500/50 shadow-glow-mild"
                : "bg-space-850 border-space-800"
            }`}
          >
            <div className="flex items-center justify-between text-space-400">
              <span className="text-[10px] uppercase font-mono tracking-wider">CO2 Level</span>
              <Wind className="w-3.5 h-3.5 text-cyan-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-space-100">
              {cabinCo2.toFixed(1)} <span className="text-xs text-space-400 font-normal">mmHg</span>
            </div>
            <div className="text-[10px] font-mono text-space-400">
              {co2Ppm} ppm • ISS limit &lt;4.0
            </div>
          </div>

          {/* O2 */}
          <div className="p-4 rounded-xl bg-space-850 border border-space-800 space-y-1">
            <div className="flex items-center justify-between text-space-400">
              <span className="text-[10px] uppercase font-mono tracking-wider">O2 Percent</span>
              <Activity className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-emerald-300">
              {cabinO2.toFixed(1)} <span className="text-xs text-space-400 font-normal">%</span>
            </div>
            <div className="text-[10px] font-mono text-space-400">
              Norm: 19.5% – 23.1%
            </div>
          </div>

          {/* Pressure */}
          <div className="p-4 rounded-xl bg-space-850 border border-space-800 space-y-1">
            <div className="flex items-center justify-between text-space-400">
              <span className="text-[10px] uppercase font-mono tracking-wider">Total Pressure</span>
              <Gauge className="w-3.5 h-3.5 text-purple-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-purple-300">
              {cabinPressure.toFixed(1)} <span className="text-xs text-space-400 font-normal">kPa</span>
            </div>
            <div className="text-[10px] font-mono text-space-400">
              1.00 atm (101.3 kPa)
            </div>
          </div>

          {/* Temperature */}
          <div className="p-4 rounded-xl bg-space-850 border border-space-800 space-y-1">
            <div className="flex items-center justify-between text-space-400">
              <span className="text-[10px] uppercase font-mono tracking-wider">Ambient Temp</span>
              <Thermometer className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-amber-300">
              {cabinTemp.toFixed(1)} <span className="text-xs text-space-400 font-normal">°C</span>
            </div>
            <div className="text-[10px] font-mono text-space-400">
              Comfort: 18.0 – 24.0°C
            </div>
          </div>

          {/* Noise Level */}
          <div className="p-4 rounded-xl bg-space-850 border border-space-800 space-y-1">
            <div className="flex items-center justify-between text-space-400">
              <span className="text-[10px] uppercase font-mono tracking-wider">Acoustic Noise</span>
              <Volume2 className="w-3.5 h-3.5 text-blue-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-blue-300">
              {cabinNoise.toFixed(1)} <span className="text-xs text-space-400 font-normal">dBA</span>
            </div>
            <div className="text-[10px] font-mono text-space-400">
              Target: &lt; 60 dBA (NC-40)
            </div>
          </div>
        </div>

        {/* Environmental Control Slider Bar */}
        <div className="p-4 rounded-lg bg-space-950 border border-space-800 space-y-3">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-space-300 font-semibold flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-cyan-400" />
              Simulate / Adjust Cabin Parameters:
            </span>
            <button
              onClick={handleUpdateEnvironment}
              disabled={isUpdating}
              className="px-3 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs flex items-center gap-1.5 transition"
            >
              <Send className="w-3 h-3" />
              {isUpdating ? "Applying..." : "Apply to ECLSS Bus"}
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
            <div>
              <div className="flex justify-between text-space-400 mb-1">
                <span>Cabin CO2 (mmHg):</span>
                <span className="text-cyan-400 font-bold">{cabinCo2.toFixed(1)} mmHg</span>
              </div>
              <input
                type="range"
                min="0.5"
                max="8.0"
                step="0.1"
                value={cabinCo2}
                onChange={(e) => setCabinCo2(parseFloat(e.target.value))}
                className="w-full accent-cyan-500"
              />
            </div>

            <div>
              <div className="flex justify-between text-space-400 mb-1">
                <span>Cabin O2 (%):</span>
                <span className="text-cyan-400 font-bold">{cabinO2.toFixed(1)}%</span>
              </div>
              <input
                type="range"
                min="18.0"
                max="24.0"
                step="0.1"
                value={cabinO2}
                onChange={(e) => setCabinO2(parseFloat(e.target.value))}
                className="w-full accent-cyan-500"
              />
            </div>

            <div>
              <div className="flex justify-between text-space-400 mb-1">
                <span>Pressure (kPa):</span>
                <span className="text-cyan-400 font-bold">{cabinPressure.toFixed(1)} kPa</span>
              </div>
              <input
                type="range"
                min="90.0"
                max="105.0"
                step="0.5"
                value={cabinPressure}
                onChange={(e) => setCabinPressure(parseFloat(e.target.value))}
                className="w-full accent-cyan-500"
              />
            </div>
          </div>
        </div>
      </section>

      {/* ── 2. Dr. Law (2014) Headache Risk Hazard Model ─────────────────── */}
      <section
        aria-label="Dr. Law 2014 Headache Risk Hazard Model"
        className="grid grid-cols-1 lg:grid-cols-12 gap-6"
      >
        {/* Left Column (6 Cols): Law 2014 Odds Curve */}
        <div className="lg:col-span-6 p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-4">
          <div className="flex items-center justify-between border-b border-space-800 pb-3">
            <div>
              <h3 className="text-sm font-bold text-space-100 uppercase tracking-wider flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Dr. Law (2014) Microgravity CO2 Headache Hazard Curve
              </h3>
              <p className="text-xs text-space-400">
                Law J, Watkins S, Alexander D. J Occup Environ Med. 2014;56(5):477-483
              </p>
            </div>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-space-800 text-amber-300 border border-space-700">
              OR = 2.0 / mmHg
            </span>
          </div>

          {/* SVG Exponential Curve Graphic */}
          <div className="p-2 rounded-lg bg-[#070c14] border border-space-800">
            <svg
              viewBox={`0 0 ${svgW} ${svgH}`}
              className="w-full h-36 overflow-visible"
            >
              {/* Grid Lines */}
              <line x1="20" y1="120" x2={svgW - 20} y2="120" stroke="#1e2b42" strokeWidth="1" />
              <line x1="20" y1="20" x2="20" y2="120" stroke="#1e2b42" strokeWidth="1" />

              {/* Threshold indicator at 3.0 mmHg and 4.5 mmHg */}
              <line
                x1={((3.0 - 1.0) / 7.0) * (svgW - 40) + 20}
                y1="20"
                x2={((3.0 - 1.0) / 7.0) * (svgW - 40) + 20}
                y2="120"
                stroke="rgba(46, 204, 113, 0.4)"
                strokeDasharray="2 2"
              />
              <line
                x1={((4.5 - 1.0) / 7.0) * (svgW - 40) + 20}
                y1="20"
                x2={((4.5 - 1.0) / 7.0) * (svgW - 40) + 20}
                y2="120"
                stroke="rgba(231, 76, 60, 0.4)"
                strokeDasharray="2 2"
              />

              {/* Theoretical Exponential Curve */}
              <path
                d={pathD}
                fill="none"
                stroke="#f59e0b"
                strokeWidth="2.5"
                strokeLinecap="round"
              />

              {/* Astronaut Operating Point Node */}
              <circle
                cx={currentX}
                cy={currentY}
                r="6"
                fill="#ef4444"
                stroke="#ffffff"
                strokeWidth="2"
                className="animate-pulse"
              />

              {/* Text Axis Labels */}
              <text x="20" y="135" fill="#64748b" fontSize="10" fontFamily="monospace">1.0 mmHg</text>
              <text x="120" y="135" fill="#64748b" fontSize="10" fontFamily="monospace">3.0 (ISS Nom)</text>
              <text x="220" y="135" fill="#64748b" fontSize="10" fontFamily="monospace">5.0 (Hazard)</text>
              <text x={svgW - 30} y="135" fill="#64748b" fontSize="10" fontFamily="monospace">8.0</text>
            </svg>
          </div>

          <div className="text-[11px] text-space-400 font-mono leading-relaxed">
            Law et al. (2014) demonstrated that in microgravity, absent convective buoyancy, crew members experience
            doubled odds of cephalalgia for each 1 mm Hg increase in ambient PCO2.
          </div>
        </div>

        {/* Right Column (6 Cols): Hazard Metrics & Recommendations */}
        <div className="lg:col-span-6 p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel flex flex-col justify-between">
          <div className="border-b border-space-800 pb-3">
            <h3 className="text-sm font-bold text-space-100 uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              Astronaut Headache Hazard Assessment
            </h3>
            <p className="text-xs text-space-400">
              Current Microgravity Hypercapnia Risk Tier
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 py-3 font-mono text-xs">
            <div className="p-3.5 rounded-lg bg-space-850 border border-space-800 space-y-1">
              <span className="text-[10px] text-space-400 uppercase">Odds Ratio (OR)</span>
              <div className="text-2xl font-bold text-amber-300">
                {currentOr.toFixed(2)}x
              </div>
              <p className="text-[10px] text-space-400">
                Relative to 2.0 mmHg reference baseline.
              </p>
            </div>

            <div className="p-3.5 rounded-lg bg-space-850 border border-space-800 space-y-1">
              <span className="text-[10px] text-space-400 uppercase">Risk Tier</span>
              <div
                className={`text-xl font-bold uppercase ${
                  cabinCo2 >= 4.5
                    ? "text-red-400"
                    : cabinCo2 >= 3.5
                    ? "text-amber-400"
                    : "text-emerald-400"
                }`}
              >
                {hazardModel?.risk_category || (cabinCo2 >= 4.5 ? "HIGH_RISK" : "NOMINAL")}
              </div>
              <p className="text-[10px] text-space-400">
                Prob: {hazardModel?.headache_probability_pct ?? Math.round(Math.min(95, currentOr * 4))}%
              </p>
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-space-950 border border-space-800 space-y-1 text-xs">
            <span className="text-[10px] font-mono text-cyan-400 uppercase font-bold">
              Clinical Countermeasure:
            </span>
            <p className="text-space-200">
              {hazardModel?.recommendation ||
                "Maintain localized airflow fan speed > 25 ft/min. Switch CDRA to high desorption mode if PCO2 exceeds 4.0 mmHg."}
            </p>
          </div>
        </div>
      </section>

      {/* ── 3. Spaceflight Symptom Triage Checklist ───────────────────────── */}
      <section
        aria-label="Spaceflight Symptom Triage"
        className="p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-4"
      >
        <div className="border-b border-space-800 pb-3">
          <h3 className="text-sm font-bold text-space-100 uppercase tracking-wider flex items-center gap-2">
            <HeartPulse className="w-4 h-4 text-red-400" />
            Spaceflight Differential Symptom Triage Matrix
          </h3>
          <p className="text-xs text-space-400">
            Interactive Aerospace Clinical Decision Support &bull; Microgravity Syndromes &bull; Linked Cabin Factors
          </p>
        </div>

        {/* Symptom Selection Tabs */}
        <div className="flex flex-wrap gap-2">
          {Object.entries(SYMPTOMS).map(([key, sym]) => (
            <button
              key={key}
              onClick={() => setSelectedSymptom(key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition ${
                selectedSymptom === key
                  ? "bg-cyan-600 text-white shadow-sm"
                  : "bg-space-850 text-space-400 hover:text-space-200 border border-space-800"
              }`}
            >
              {sym.title}
            </button>
          ))}
        </div>

        {/* Selected Symptom Detail Card */}
        {SYMPTOMS[selectedSymptom] && (
          <div className="p-4 rounded-xl bg-space-850 border border-space-800 space-y-3 text-xs">
            <div className="flex items-center justify-between border-b border-space-800 pb-2">
              <span className="font-bold text-sm text-space-100">
                {SYMPTOMS[selectedSymptom].title}
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                  SYMPTOMS[selectedSymptom].severity === "HIGH"
                    ? "bg-red-500/20 text-red-300 border border-red-500/30"
                    : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                }`}
              >
                {SYMPTOMS[selectedSymptom].severity} PRIORITY
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <span className="text-[10px] font-mono text-cyan-400 uppercase font-bold">
                  Root Spaceflight Etiologies:
                </span>
                <ul className="list-disc list-inside space-y-1 text-space-300">
                  {SYMPTOMS[selectedSymptom].causes.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </div>

              <div className="space-y-1.5">
                <span className="text-[10px] font-mono text-emerald-400 uppercase font-bold">
                  Recommended Operational Actions:
                </span>
                <ul className="list-disc list-inside space-y-1 text-space-300">
                  {SYMPTOMS[selectedSymptom].mitigations.map((m, i) => (
                    <li key={i}>{m}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-space-950 border border-space-800 text-[11px] font-mono text-space-300">
              <strong className="text-space-100">Medical Kit Formulary Intervention:</strong>{" "}
              {SYMPTOMS[selectedSymptom].medicalKit}
            </div>
          </div>
        )}
      </section>
    </div>
  );
};
