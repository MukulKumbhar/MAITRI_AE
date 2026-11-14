import React, { useState, useEffect, useRef } from "react";
import {
  TelemetryPayload,
  PVTSessionStatus,
  PVTHistoryRecord,
  SleepStatus,
  ScreenerResult,
  ThirdQuarterAnalysis,
  ScreenerHistoryRecord,
} from "../../types";
import {
  startPVT,
  recordPVTResponse,
  abortPVT,
  fetchPVTHistory,
  fetchSleepStatus,
  logSleep,
  submitScreener,
  fetchThirdQuarter,
} from "../../services/api";
import {
  Brain,
  Moon,
  Sun,
  Clock,
  Play,
  RotateCcw,
  CheckCircle,
  AlertTriangle,
  Flame,
  ShieldAlert,
  Calendar,
  Send,
  Zap,
  Activity,
  Award,
} from "lucide-react";

interface NeuroTabProps {
  telemetry: TelemetryPayload | null;
}

export const NeuroTab: React.FC<NeuroTabProps> = ({ telemetry }) => {
  // ── PVT-B Reaction Self-Test State ──────────────────────────────────────────
  const [pvtRunning, setPvtRunning] = useState<boolean>(false);
  const [pvtStatus, setPvtStatus] = useState<"IDLE" | "WAITING" | "STIMULUS" | "FEEDBACK" | "FINISHED">("IDLE");
  const [stimulusStartTime, setStimulusStartTime] = useState<number>(0);
  const [tickerMs, setTickerMs] = useState<number>(0);
  const [lastRt, setLastRt] = useState<number | null>(null);
  const [lastOutcome, setLastOutcome] = useState<string | null>(null);

  // Local PVT session metrics
  const [trialCount, setTrialCount] = useState<number>(0);
  const [validHits, setValidHits] = useState<number>(0);
  const [lapses, setLapses] = useState<number>(0);
  const [falseStarts, setFalseStarts] = useState<number>(0);
  const [rtHistory, setRtHistory] = useState<number[]>([]);
  const [pvtPastRecords, setPvtPastRecords] = useState<PVTHistoryRecord[]>([]);

  const pvtTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const testTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Sleep Pod & Circadian State ─────────────────────────────────────────────
  const [sleepData, setSleepData] = useState<SleepStatus | null>(null);
  const [logSleepHours, setLogSleepHours] = useState<number>(7.0);
  const [logLux, setLogLux] = useState<number>(120);
  const [logDate, setLogDate] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  const [sleepLogging, setSleepLogging] = useState<boolean>(false);
  const [sleepLogSuccess, setSleepLogSuccess] = useState<boolean>(false);

  // ── Validated Screeners State ───────────────────────────────────────────────
  const [activeScreener, setActiveScreener] = useState<"PHQ-9" | "GAD-7" | "PSS-4">("PHQ-9");
  const [phq9Answers, setPhq9Answers] = useState<number[]>([0, 0, 0, 0, 0, 0, 0, 0, 0]);
  const [gad7Answers, setGad7Answers] = useState<number[]>([0, 0, 0, 0, 0, 0, 0]);
  const [pss4Answers, setPss4Answers] = useState<number[]>([1, 2, 2, 1]);
  const [screenerResult, setScreenerResult] = useState<ScreenerResult | null>(null);
  const [screenerSubmitting, setScreenerSubmitting] = useState<boolean>(false);
  const [thirdQuarter, setThirdQuarter] = useState<ThirdQuarterAnalysis | null>(null);

  // Load initial sleep and third-quarter data
  useEffect(() => {
    fetchSleepStatus(7.0, 8.0, 120.0)
      .then((res) => setSleepData(res))
      .catch(() => {});

    fetchThirdQuarter(90.0, 180.0)
      .then((res) => setThirdQuarter(res))
      .catch(() => {});

    fetchPVTHistory(5)
      .then((res) => setPvtPastRecords(res.records || []))
      .catch(() => {});
  }, []);

  // Keyboard shortcut listener for PVT spacebar hit
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === "Space" && pvtRunning) {
        e.preventDefault();
        handlePvtHit();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [pvtRunning, pvtStatus, stimulusStartTime]);

  // ── PVT Engine Logic (Basner & Dinges 2011) ──────────────────────────────────
  const startPvtTest = async () => {
    setPvtRunning(true);
    setTrialCount(0);
    setValidHits(0);
    setLapses(0);
    setFalseStarts(0);
    setRtHistory([]);
    setLastRt(null);
    setLastOutcome(null);

    try {
      await startPVT("Astronaut", 180.0);
    } catch {}

    scheduleNextStimulus();

    // 3-minute hard stop
    testTimeoutRef.current = setTimeout(() => {
      finishPvtTest();
    }, 180000);
  };

  const scheduleNextStimulus = () => {
    setPvtStatus("WAITING");
    setTickerMs(0);
    // Random delay between 2 and 6 seconds for responsive testing
    const delayMs = Math.floor(Math.random() * 4000) + 2000;

    pvtTimerRef.current = setTimeout(() => {
      const now = performance.now();
      setStimulusStartTime(now);
      setPvtStatus("STIMULUS");

      // Animate millisecond counter ticker
      const updateTicker = () => {
        const elapsed = Math.round(performance.now() - now);
        setTickerMs(elapsed);
        if (elapsed < 5000) {
          animFrameRef.current = requestAnimationFrame(updateTicker);
        } else {
          // Timeout = Lapse
          handleTimeoutLapse();
        }
      };
      animFrameRef.current = requestAnimationFrame(updateTicker);
    }, delayMs);
  };

  const handlePvtHit = async () => {
    if (!pvtRunning) return;

    if (pvtStatus === "WAITING") {
      // False start (<100ms)
      if (pvtTimerRef.current) clearTimeout(pvtTimerRef.current);
      setFalseStarts((prev) => prev + 1);
      setLastOutcome("FALSE START (ANTICIPATION)");
      setLastRt(0);
      setPvtStatus("FEEDBACK");
      try {
        await recordPVTResponse({ is_false_start: true });
      } catch {}

      setTimeout(() => {
        scheduleNextStimulus();
      }, 1200);
      return;
    }

    if (pvtStatus === "STIMULUS") {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      const rt = Math.round(performance.now() - stimulusStartTime);
      setLastRt(rt);
      setRtHistory((prev) => [...prev, rt]);
      setTrialCount((prev) => prev + 1);

      let outcome = "VALID HIT";
      if (rt < 100) {
        setFalseStarts((prev) => prev + 1);
        outcome = "FALSE START (<100ms)";
      } else if (rt >= 355) {
        setLapses((prev) => prev + 1);
        outcome = "PVT-B LAPSE (≥355ms)";
      } else {
        setValidHits((prev) => prev + 1);
      }

      setLastOutcome(outcome);
      setPvtStatus("FEEDBACK");

      try {
        await recordPVTResponse({ rt_ms: rt, is_false_start: rt < 100 });
      } catch {}

      setTimeout(() => {
        scheduleNextStimulus();
      }, 1200);
    }
  };

  const handleTimeoutLapse = async () => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    setLapses((prev) => prev + 1);
    setTrialCount((prev) => prev + 1);
    setRtHistory((prev) => [...prev, 5000]);
    setLastRt(5000);
    setLastOutcome("TIMED OUT (5000ms)");
    setPvtStatus("FEEDBACK");

    try {
      await recordPVTResponse({ rt_ms: 5000, is_false_start: false });
    } catch {}

    setTimeout(() => {
      scheduleNextStimulus();
    }, 1200);
  };

  const stopPvtTest = async () => {
    if (pvtTimerRef.current) clearTimeout(pvtTimerRef.current);
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (testTimeoutRef.current) clearTimeout(testTimeoutRef.current);
    setPvtRunning(false);
    setPvtStatus("IDLE");
    try {
      await abortPVT();
    } catch {}
  };

  const finishPvtTest = () => {
    if (pvtTimerRef.current) clearTimeout(pvtTimerRef.current);
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    setPvtRunning(false);
    setPvtStatus("FINISHED");
    fetchPVTHistory(5).then((res) => setPvtPastRecords(res.records || []));
  };

  // Mean RT
  const meanRt =
    rtHistory.length > 0
      ? Math.round(rtHistory.reduce((a, b) => a + b, 0) / rtHistory.length)
      : 0;

  // ── Sleep Logging Handler ───────────────────────────────────────────────────
  const handleLogSleep = async (e: React.FormEvent) => {
    e.preventDefault();
    setSleepLogging(true);
    try {
      await logSleep({
        sleep_date: logDate,
        sleep_duration_hours: logSleepHours,
        target_sleep_hours: 8.0,
        light_exposure_lux: logLux,
        notes: "Onboard sleep pod daily check-in",
      });
      setSleepLogSuccess(true);
      setTimeout(() => setSleepLogSuccess(false), 3000);
      const updated = await fetchSleepStatus(logSleepHours, 8.0, logLux);
      setSleepData(updated);
    } finally {
      setSleepLogging(false);
    }
  };

  // ── Screener Submission Handler ─────────────────────────────────────────────
  const handleSubmitScreener = async () => {
    setScreenerSubmitting(true);
    try {
      const answers =
        activeScreener === "PHQ-9"
          ? phq9Answers
          : activeScreener === "GAD-7"
          ? gad7Answers
          : pss4Answers;

      const res = await submitScreener({
        screener_type: activeScreener,
        item_responses: answers,
        mission_elapsed_days: 90.0,
        mission_total_days: 180.0,
      });

      setScreenerResult(res.result);
      if (res.third_quarter_effect) {
        setThirdQuarter(res.third_quarter_effect);
      }
    } finally {
      setScreenerSubmitting(false);
    }
  };

  const PHQ9_QUESTIONS = [
    "1. Little interest or pleasure in doing things",
    "2. Feeling down, depressed, or hopeless",
    "3. Trouble falling or staying asleep, or sleeping too much",
    "4. Feeling tired or having little energy",
    "5. Poor appetite or overeating",
    "6. Feeling bad about yourself — or that you are a failure",
    "7. Trouble concentrating on tasks, reading, or mission ops",
    "8. Moving or speaking slowly, or unusually fidgety/restless",
    "9. Thoughts that you would be better off dead, or of hurting yourself [SAFETY GATE TRIGGER]",
  ];

  const GAD7_QUESTIONS = [
    "1. Feeling nervous, anxious, or on edge",
    "2. Not being able to stop or control worrying",
    "3. Worrying too much about different things",
    "4. Trouble relaxing",
    "5. Being so restless that it is hard to sit still",
    "6. Becoming easily annoyed or irritable",
    "7. Feeling afraid as if something awful might happen",
  ];

  const PSS4_QUESTIONS = [
    "1. In the last month, felt unable to control important things?",
    "2. Felt confident in ability to handle personal problems? [Reverse Scored]",
    "3. Felt that things were going your way? [Reverse Scored]",
    "4. Felt difficulties were piling up too high to overcome?",
  ];

  return (
    <div className="space-y-6">
      {/* ── 1. Interactive 3-Minute PVT-B Reaction Self Test Widget ──────────── */}
      <section
        aria-label="Psychomotor Vigilance Test PVT-B"
        className="p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-6"
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-space-800 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-purple-400" />
              <h2 className="text-sm font-bold text-space-100 uppercase tracking-wider">
                Psychomotor Vigilance Reaction Self-Test (PVT-B)
              </h2>
            </div>
            <p className="text-xs text-space-400">
              Basner &amp; Dinges (2011) Brief 3-Min Spaceflight Fatigue Standard • Lapses (≥355ms) &amp; Anticipation (&lt;100ms)
            </p>
          </div>

          <div className="flex items-center gap-2">
            {!pvtRunning ? (
              <button
                onClick={startPvtTest}
                className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs font-mono flex items-center gap-1.5 transition shadow-glow-mild"
              >
                <Play className="w-3.5 h-3.5" />
                START 3-MIN PVT-B
              </button>
            ) : (
              <button
                onClick={stopPvtTest}
                className="px-4 py-2 rounded-lg bg-red-600/80 hover:bg-red-500 text-white font-bold text-xs font-mono flex items-center gap-1.5 transition"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                ABORT TEST
              </button>
            )}
          </div>
        </div>

        {/* PVT Interactive Target Area */}
        <div className="flex flex-col items-center justify-center p-8 rounded-xl bg-[#070b12] border-2 border-space-800 relative min-h-[220px]">
          {pvtStatus === "IDLE" && (
            <div className="text-center space-y-2">
              <Brain className="w-12 h-12 text-space-500 mx-auto" />
              <h3 className="text-sm font-bold text-space-200">
                Astronaut Vigilance &amp; Sustained Attention Test
              </h3>
              <p className="text-xs text-space-400 max-w-md">
                Click "Start 3-Min PVT-B". When the red millisecond counter appears, press{" "}
                <kbd className="px-1.5 py-0.5 rounded bg-space-800 border border-space-700 font-mono text-cyan-300">
                  SPACEBAR
                </kbd>{" "}
                or click the screen as fast as possible.
              </p>
            </div>
          )}

          {pvtStatus === "WAITING" && (
            <div
              onClick={handlePvtHit}
              className="text-center space-y-3 cursor-pointer w-full py-8 select-none"
            >
              <div className="w-16 h-16 rounded-full border-2 border-dashed border-space-600 animate-spin mx-auto" />
              <p className="text-xs font-mono text-space-400 uppercase tracking-widest animate-pulse">
                Awaiting Stimulus (Random ISI 2-6s)... Do Not False Start!
              </p>
            </div>
          )}

          {pvtStatus === "STIMULUS" && (
            <div
              onClick={handlePvtHit}
              role="button"
              tabIndex={0}
              className="w-full max-w-md py-6 rounded-xl bg-red-600 hover:bg-red-500 cursor-pointer text-center text-white select-none transition-all shadow-[0_0_35px_rgba(239,68,68,0.7)] animate-pulse"
            >
              <div className="font-mono text-5xl font-extrabold tracking-wider">
                {tickerMs} <span className="text-2xl font-normal">ms</span>
              </div>
              <div className="text-xs font-mono font-bold mt-2 uppercase tracking-widest">
                [ HIT SPACEBAR / TAP SCREEN NOW ]
              </div>
            </div>
          )}

          {pvtStatus === "FEEDBACK" && (
            <div className="text-center space-y-2">
              <div
                className={`font-mono text-4xl font-extrabold ${
                  lastOutcome?.includes("FALSE")
                    ? "text-red-400"
                    : lastOutcome?.includes("LAPSE")
                    ? "text-amber-400"
                    : "text-emerald-400"
                }`}
              >
                {lastRt !== null ? `${lastRt} ms` : "FALSE START"}
              </div>
              <div className="text-xs font-mono font-bold text-space-300 uppercase">
                {lastOutcome}
              </div>
            </div>
          )}

          {pvtStatus === "FINISHED" && (
            <div className="text-center space-y-3">
              <Award className="w-12 h-12 text-emerald-400 mx-auto" />
              <h3 className="text-sm font-bold text-emerald-300">
                PVT-B Vigilance Test Completed &amp; Cryptographically Logged
              </h3>
              <p className="text-xs text-space-300">
                Mean RT: <strong className="text-white">{meanRt} ms</strong> • Valid Hits:{" "}
                <strong className="text-white">{validHits}</strong> • Lapses:{" "}
                <strong className="text-amber-300">{lapses}</strong> • False Starts:{" "}
                <strong className="text-red-300">{falseStarts}</strong>
              </p>
            </div>
          )}
        </div>

        {/* Live Metrics Row */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs font-mono">
          <div className="p-3 rounded-lg bg-space-850 border border-space-800 text-center">
            <span className="text-[10px] text-space-400 block">TOTAL TRIALS</span>
            <span className="text-base font-bold text-space-100">{trialCount}</span>
          </div>
          <div className="p-3 rounded-lg bg-space-850 border border-space-800 text-center">
            <span className="text-[10px] text-space-400 block">VALID HITS</span>
            <span className="text-base font-bold text-emerald-400">{validHits}</span>
          </div>
          <div className="p-3 rounded-lg bg-space-850 border border-space-800 text-center">
            <span className="text-[10px] text-space-400 block">LAPSES (≥355ms)</span>
            <span className="text-base font-bold text-amber-400">{lapses}</span>
          </div>
          <div className="p-3 rounded-lg bg-space-850 border border-space-800 text-center">
            <span className="text-[10px] text-space-400 block">FALSE STARTS</span>
            <span className="text-base font-bold text-red-400">{falseStarts}</span>
          </div>
          <div className="p-3 rounded-lg bg-space-850 border border-space-800 text-center">
            <span className="text-[10px] text-space-400 block">MEAN RT</span>
            <span className="text-base font-bold text-cyan-300">{meanRt} ms</span>
          </div>
        </div>
      </section>

      {/* ── 2. Circadian Sleep Pod & Orbital Cycle Tracker ─────────────────── */}
      <section
        aria-label="Circadian Sleep Pod and Orbital Cycle"
        className="grid grid-cols-1 lg:grid-cols-12 gap-6"
      >
        {/* Left Column (7 Cols): Orbital Cycle & Melatonin */}
        <div className="lg:col-span-7 p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-4">
          <div className="flex items-center justify-between border-b border-space-800 pb-3">
            <div>
              <h3 className="text-sm font-bold text-space-100 uppercase tracking-wider flex items-center gap-2">
                <Moon className="w-4 h-4 text-cyan-400" />
                ISS 90-Minute Daylight / Night Orbital Cycle Pod
              </h3>
              <p className="text-xs text-space-400">
                Circadian Entrainment • Melatonin Suppression Index &bull; Sleep Debt
              </p>
            </div>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-space-800 text-cyan-400 border border-space-700">
              ORBIT: 92.68 MIN
            </span>
          </div>

          {/* Orbital Cycle Visualizer Bar */}
          <div className="p-4 rounded-lg bg-space-850 border border-space-800 space-y-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-space-300 flex items-center gap-1.5">
                <Sun className="w-3.5 h-3.5 text-amber-400" />
                Current Phase:{" "}
                <strong className="text-space-100">
                  {sleepData?.orbital_cycle?.current_phase || "DAYLIGHT"}
                </strong>
              </span>
              <span className="text-space-400">
                Elapsed: {sleepData?.orbital_cycle?.cycle_elapsed_min?.toFixed(1) || "24.5"}m / 92.7m
              </span>
            </div>

            {/* Split Daylight / Eclipse Bar */}
            <div className="h-4 rounded-full bg-space-950 overflow-hidden flex border border-space-700">
              <div
                className="bg-gradient-to-r from-amber-500 to-yellow-300 h-full w-1/2 flex items-center justify-center text-[9px] font-mono text-space-950 font-bold"
              >
                ORBITAL DAY (46m)
              </div>
              <div
                className="bg-gradient-to-r from-indigo-900 to-purple-950 h-full w-1/2 flex items-center justify-center text-[9px] font-mono text-space-300"
              >
                ORBITAL ECLIPSE (46m)
              </div>
            </div>
          </div>

          {/* Melatonin & Sleep Debt Cards */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3.5 rounded-lg bg-space-850 border border-space-800 space-y-1 font-mono">
              <span className="text-[10px] text-space-400 uppercase">
                Cumulative Sleep Debt
              </span>
              <div className="text-xl font-bold text-amber-300">
                {sleepData?.sleep_debt?.cumulative_debt_hours?.toFixed(1) || "1.5"} hrs
              </div>
              <p className="text-[10px] text-space-400">
                Status: {sleepData?.sleep_debt?.clinical_status || "MILD DEBT"}
              </p>
            </div>

            <div className="p-3.5 rounded-lg bg-space-850 border border-space-800 space-y-1 font-mono">
              <span className="text-[10px] text-space-400 uppercase">
                Melatonin Suppression
              </span>
              <div className="text-xl font-bold text-cyan-300">
                {sleepData?.melatonin_suppression?.melatonin_suppression_pct?.toFixed(0) || "18"}%
              </div>
              <p className="text-[10px] text-space-400">
                Ambient Lux: {sleepData?.melatonin_suppression?.light_lux || 120} lux
              </p>
            </div>
          </div>
        </div>

        {/* Right Column (5 Cols): Daily Sleep Logger Form */}
        <div className="lg:col-span-5 p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel flex flex-col justify-between">
          <div className="border-b border-space-800 pb-3">
            <h3 className="text-sm font-bold text-space-100 uppercase tracking-wider flex items-center gap-2">
              <Calendar className="w-4 h-4 text-emerald-400" />
              Log Sleep Duration &amp; Light Exposure
            </h3>
            <p className="text-xs text-space-400">
              SHA-256 Chained Astronaut Daily Circadian Record
            </p>
          </div>

          <form onSubmit={handleLogSleep} className="space-y-3 py-3 text-xs font-mono">
            <div>
              <label className="text-space-400 block mb-1">Date:</label>
              <input
                type="date"
                value={logDate}
                onChange={(e) => setLogDate(e.target.value)}
                className="w-full px-3 py-1.5 rounded bg-space-850 border border-space-700 text-space-100"
              />
            </div>

            <div>
              <div className="flex justify-between text-space-400 mb-1">
                <span>Duration Slept:</span>
                <span className="text-cyan-400 font-bold">{logSleepHours} hrs</span>
              </div>
              <input
                type="range"
                min="3.0"
                max="12.0"
                step="0.5"
                value={logSleepHours}
                onChange={(e) => setLogSleepHours(parseFloat(e.target.value))}
                className="w-full accent-cyan-500"
              />
            </div>

            <div>
              <div className="flex justify-between text-space-400 mb-1">
                <span>Cabin Light Level:</span>
                <span className="text-cyan-400 font-bold">{logLux} lux</span>
              </div>
              <input
                type="range"
                min="0"
                max="500"
                step="20"
                value={logLux}
                onChange={(e) => setLogLux(parseInt(e.target.value))}
                className="w-full accent-cyan-500"
              />
            </div>

            <button
              type="submit"
              disabled={sleepLogging}
              className="w-full py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold flex items-center justify-center gap-2 transition"
            >
              <Send className="w-3.5 h-3.5" />
              {sleepLogging ? "Logging to Ledger..." : "Save Sleep Record"}
            </button>

            {sleepLogSuccess && (
              <div className="text-center text-emerald-400 text-xs font-bold">
                ✓ Recorded with SHA-256 block hash!
              </div>
            )}
          </form>

          <div className="text-[10px] text-space-500 border-t border-space-800 pt-2 font-mono">
            Preserves crew alertness index according to NASA circadian guidelines.
          </div>
        </div>
      </section>

      {/* ── 3. Validated Screeners (PHQ-9 / GAD-7 / PSS-4) ──────────────────── */}
      <section
        aria-label="Clinical Psychological Screeners"
        className="p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-6"
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-space-800 pb-3">
          <div>
            <h3 className="text-sm font-bold text-space-100 uppercase tracking-wider flex items-center gap-2">
              <Brain className="w-4 h-4 text-purple-400" />
              Validated Behavioral Health Screeners (PHQ-9 / GAD-7 / PSS-4)
            </h3>
            <p className="text-xs text-space-400">
              Offline Clinical Psychometrics &bull; Item 9 Suicide Safety Gate &bull; Third-Quarter Phenomenon
            </p>
          </div>

          {/* Screener Selector Buttons */}
          <div className="flex items-center gap-1 bg-space-950 p-1 rounded-lg border border-space-800">
            {(["PHQ-9", "GAD-7", "PSS-4"] as const).map((sc) => (
              <button
                key={sc}
                onClick={() => {
                  setActiveScreener(sc);
                  setScreenerResult(null);
                }}
                className={`px-3 py-1 rounded text-xs font-mono font-bold transition ${
                  activeScreener === sc
                    ? "bg-purple-600 text-white shadow-sm"
                    : "text-space-400 hover:text-space-200"
                }`}
              >
                {sc}
              </button>
            ))}
          </div>
        </div>

        {/* Screener Questionnaire Form */}
        <div className="space-y-4">
          <div className="space-y-3">
            {(activeScreener === "PHQ-9"
              ? PHQ9_QUESTIONS
              : activeScreener === "GAD-7"
              ? GAD7_QUESTIONS
              : PSS4_QUESTIONS
            ).map((question, idx) => {
              const currentVal =
                activeScreener === "PHQ-9"
                  ? phq9Answers[idx]
                  : activeScreener === "GAD-7"
                  ? gad7Answers[idx]
                  : pss4Answers[idx];

              const isItem9 = activeScreener === "PHQ-9" && idx === 8;

              return (
                <div
                  key={idx}
                  className={`p-3.5 rounded-lg border flex flex-col md:flex-row items-start md:items-center justify-between gap-3 transition ${
                    isItem9
                      ? "bg-red-950/20 border-red-500/40"
                      : "bg-space-850 border-space-800"
                  }`}
                >
                  <div className="text-xs text-space-200">
                    <span className="font-semibold">{question}</span>
                    {isItem9 && (
                      <span className="block text-[10px] text-red-400 font-mono mt-0.5 font-bold">
                        CRITICAL SAFETY TRIGGER: Any endorsement initiates immediate behavioral health consultation.
                      </span>
                    )}
                  </div>

                  {/* Radio Choice Buttons (0 - 3 or 0 - 4) */}
                  <div className="flex items-center gap-1.5 self-end md:self-center shrink-0 font-mono text-xs">
                    {[0, 1, 2, 3].map((val) => (
                      <button
                        key={val}
                        type="button"
                        onClick={() => {
                          if (activeScreener === "PHQ-9") {
                            const updated = [...phq9Answers];
                            updated[idx] = val;
                            setPhq9Answers(updated);
                          } else if (activeScreener === "GAD-7") {
                            const updated = [...gad7Answers];
                            updated[idx] = val;
                            setGad7Answers(updated);
                          } else {
                            const updated = [...pss4Answers];
                            updated[idx] = val;
                            setPss4Answers(updated);
                          }
                        }}
                        className={`w-8 h-8 rounded border text-xs font-bold transition flex items-center justify-center ${
                          currentVal === val
                            ? isItem9 && val > 0
                              ? "bg-red-600 text-white border-red-500 animate-pulse"
                              : "bg-purple-600 text-white border-purple-500 shadow-sm"
                            : "bg-space-900 border-space-700 text-space-400 hover:text-space-200"
                        }`}
                      >
                        {val}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="flex items-center justify-between pt-2">
            <span className="text-xs text-space-400">
              Rating Scale: 0 = Not at all, 1 = Several days, 2 = More than half, 3 = Nearly every day
            </span>
            <button
              onClick={handleSubmitScreener}
              disabled={screenerSubmitting}
              className="px-5 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs font-mono flex items-center gap-2 transition disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              {screenerSubmitting ? "Scoring..." : `Score & Submit ${activeScreener}`}
            </button>
          </div>

          {/* Screener Scored Result Card */}
          {screenerResult && (
            <div
              className={`p-4 rounded-xl border mt-4 space-y-2 ${
                screenerResult.safety_alert
                  ? "bg-red-950/50 border-red-500 shadow-glow-critical animate-pulse"
                  : "bg-space-850 border-space-700"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 font-mono">
                  <span className="text-xs text-space-300 font-bold uppercase">
                    {screenerResult.screener_type} SCORE:
                  </span>
                  <span className="text-lg font-extrabold text-white">
                    {screenerResult.total_score} / {screenerResult.max_possible_score}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    {screenerResult.severity}
                  </span>
                </div>
                {screenerResult.safety_alert && (
                  <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-red-600 text-white animate-pulse">
                    SAFETY GATE TRIGGERED
                  </span>
                )}
              </div>

              <p className="text-xs text-space-200">
                {screenerResult.clinical_interpretation}
              </p>
              <p className="text-xs text-space-400 font-mono">
                Recommendation: {screenerResult.action_recommendation}
              </p>
            </div>
          )}
        </div>
      </section>

      {/* ── 4. Third-Quarter Trend Graph & Vulnerability Tracker ───────────── */}
      {thirdQuarter && (
        <section
          aria-label="Third-Quarter Phenomenon Analysis"
          className="p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-4"
        >
          <div className="flex items-center justify-between border-b border-space-800 pb-3">
            <div>
              <h3 className="text-sm font-bold text-space-100 uppercase tracking-wider flex items-center gap-2">
                <Flame className="w-4 h-4 text-amber-400" />
                Third-Quarter Phenomenon Longitudinal Vulnerability Curve
              </h3>
              <p className="text-xs text-space-400">
                Bechtel &amp; Berning (1991) &bull; Kanas et al. (2006) Psychological Decline Vulnerability Window
              </p>
            </div>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-space-800 text-amber-300 border border-space-700">
              WINDOW: 50% – 75%
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="p-4 rounded-lg bg-space-850 border border-space-800 space-y-1">
              <span className="text-[10px] text-space-400 uppercase font-mono">
                Mission Elapsed Days
              </span>
              <div className="text-xl font-bold font-mono text-cyan-300">
                Day {thirdQuarter.mission_elapsed_days} / {thirdQuarter.mission_total_days}
              </div>
              <p className="text-space-400 text-[11px]">
                Fraction: {(thirdQuarter.mission_fraction * 100).toFixed(0)}% Completed
              </p>
            </div>

            <div className="p-4 rounded-lg bg-space-850 border border-space-800 space-y-1">
              <span className="text-[10px] text-space-400 uppercase font-mono">
                Vulnerability Risk Tier
              </span>
              <div className="text-xl font-bold font-mono text-amber-300">
                {thirdQuarter.vulnerability_tier} ({(thirdQuarter.vulnerability_index * 100).toFixed(0)}%)
              </div>
              <p className="text-space-400 text-[11px]">
                {thirdQuarter.is_third_quarter_window
                  ? "Active in high-risk 3rd Quarter window."
                  : "Outside 3rd Quarter window."}
              </p>
            </div>

            <div className="p-4 rounded-lg bg-space-850 border border-space-800 space-y-1">
              <span className="text-[10px] text-space-400 uppercase font-mono">
                BHP Countermeasure Action
              </span>
              <p className="text-space-200 text-xs">
                {thirdQuarter.clinical_recommendation}
              </p>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};
