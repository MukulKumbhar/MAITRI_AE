import React, { useEffect, useState } from "react";
import { LogRecord, PsychLogRecord } from "../../types";
import { fetchLogs, fetchLogTrends, fetchPsychLogs } from "../../services/api";
import {
  LineChart,
  BarChart,
  Database,
  Search,
  Filter,
  RefreshCw,
  AlertOctagon,
  TrendingUp,
  Brain,
  MessageSquare,
} from "lucide-react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Line, Bar } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const EMOTION_COLORS: Record<string, string> = {
  happy: "#ffd600",
  neutral: "#94a3b8",
  surprise: "#00e5ff",
  sad: "#2979ff",
  fear: "#d500f9",
  angry: "#e74c3c",
  disgust: "#2ecc71",
};

export const LogsTab: React.FC = () => {
  const [logs, setLogs] = useState<LogRecord[]>([]);
  const [trends, setTrends] = useState<any[]>([]);
  const [psychLogs, setPsychLogs] = useState<PsychLogRecord[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchFilter, setSearchFilter] = useState<string>("");
  const [emotionFilter, setEmotionFilter] = useState<string>("ALL");

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [logsData, trendsData, psychData] = await Promise.all([
        fetchLogs(250, 0),
        fetchLogTrends(60),
        fetchPsychLogs(50),
      ]);
      setLogs(logsData.records || []);
      setTrends(trendsData.records || []);
      setPsychLogs(psychData.records || []);
    } catch (e) {
      console.error("Failed to fetch mission logs", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  // Filter logs for table
  const filteredLogs = logs.filter((record) => {
    const matchesSearch =
      searchFilter === "" ||
      record.fused_emotion?.toLowerCase().includes(searchFilter.toLowerCase()) ||
      record.face_emotion?.toLowerCase().includes(searchFilter.toLowerCase()) ||
      record.alert_triggered?.toLowerCase().includes(searchFilter.toLowerCase()) ||
      record.timestamp?.includes(searchFilter);

    const matchesEmotion =
      emotionFilter === "ALL" ||
      record.fused_emotion?.toUpperCase() === emotionFilter.toUpperCase();

    return matchesSearch && matchesEmotion;
  });

  // Calculate Metrics (M-06 to M-09, M-11 to M-14)
  const totalReadings = logs.length;
  const avgStress = totalReadings > 0
    ? logs.reduce((acc, curr) => acc + (curr.stress_score || 0), 0) / totalReadings
    : 0.0;
  const peakStress = totalReadings > 0
    ? Math.max(...logs.map((r) => r.stress_score || 0))
    : 0.0;
  const criticalCount = logs.filter((r) => r.stress_level === "CRITICAL").length;

  const latestRecord = trends.length > 0 ? trends[trends.length - 1] : null;
  const dominantAffect = latestRecord?.fused_emotion || latestRecord?.face_emotion || "NEUTRAL";

  // Affect switches in window
  let affectSwitches = 0;
  for (let i = 1; i < trends.length; i++) {
    const prev = trends[i - 1].fused_emotion || trends[i - 1].face_emotion;
    const curr = trends[i].fused_emotion || trends[i].face_emotion;
    if (prev && curr && prev !== curr) {
      affectSwitches++;
    }
  }

  const peakConfidence = trends.length > 0
    ? Math.max(
        ...trends.map((r) =>
          Math.max(
            r.prob_angry || 0,
            r.prob_disgust || 0,
            r.prob_fear || 0,
            r.prob_happy || 0,
            r.prob_neutral || 0,
            r.prob_sad || 0,
            r.prob_surprise || 0
          )
        )
      ) * 100
    : 0;

  const meanWindowStress = trends.length > 0
    ? trends.reduce((acc, curr) => acc + (curr.stress_score || 0), 0) / trends.length
    : 0.0;

  // Chart 1: 7-Emotion Multi-Line Trajectory (M-05)
  const trendLabels = trends.map((r) => {
    const ts = r.timestamp || "";
    return ts.includes(" ") ? ts.split(" ")[1] : ts;
  });

  const emotionTrajectoryData = {
    labels: trendLabels,
    datasets: (["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"] as const).map(
      (emo) => ({
        label: emo.toUpperCase(),
        data: trends.map((r) => Math.round((r[`prob_${emo}`] || 0) * 100)),
        borderColor: EMOTION_COLORS[emo],
        backgroundColor: `${EMOTION_COLORS[emo]}20`,
        borderWidth: 1.8,
        pointRadius: 0,
        tension: 0.25,
      })
    ),
  };

  // Chart 2: Stress Index Trend Line Chart (M-10)
  const stressTrendData = {
    labels: trendLabels,
    datasets: [
      {
        label: "Stress Score (%)",
        data: trends.map((r) => r.stress_score || 0),
        borderColor: "#e74c3c",
        backgroundColor: "rgba(231, 76, 60, 0.15)",
        fill: true,
        borderWidth: 2,
        pointRadius: 1,
        tension: 0.3,
      },
    ],
  };

  // Chart 3: Emotion Distribution Histogram (M-16)
  const emotionCounts: Record<string, number> = {};
  logs.forEach((r) => {
    const emo = (r.fused_emotion || r.face_emotion || "neutral").toLowerCase();
    emotionCounts[emo] = (emotionCounts[emo] || 0) + 1;
  });

  const histogramLabels = ["happy", "neutral", "surprise", "sad", "fear", "angry", "disgust"];
  const histogramData = {
    labels: histogramLabels.map((l) => l.toUpperCase()),
    datasets: [
      {
        label: "Log Occurrences",
        data: histogramLabels.map((l) => emotionCounts[l] || 0),
        backgroundColor: histogramLabels.map((l) => EMOTION_COLORS[l] || "#2ecc71"),
        borderRadius: 4,
      },
    ],
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12 font-sans">
      {/* M-01: Mission Logs Subheader */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-space-800 pb-4">
        <div>
          <h2 className="text-base font-bold uppercase tracking-wider text-space-100 flex items-center gap-2">
            <Database className="w-5 h-5 text-cyan-400" />
            📋 Mission Telemetry History &amp; Long-Term Affective Trends
          </h2>
          <p className="text-xs text-space-400 mt-0.5">
            Offline SQLite log ledger archiving multimodal telemetry snapshots, clinical responses &amp; psych turns.
          </p>
        </div>

        <button
          onClick={loadData}
          className="px-3 py-1.5 rounded-lg bg-space-850 hover:bg-space-800 text-space-200 border border-space-700 text-xs font-mono flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* M-02: Empty State Callout if zero records */}
      {logs.length === 0 && !isLoading && (
        <div className="p-4 rounded-lg bg-space-900 border border-cyan-800/60 text-cyan-200 text-xs flex items-center gap-2">
          <Database className="w-4 h-4 text-cyan-400 shrink-0" />
          <span>No telemetry logs recorded yet. Start camera stream on Live Cockpit or click "Log Reading".</span>
        </div>
      )}

      {/* Overall Lifetime Mission KPIs (M-11 to M-14) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 font-mono text-center">
        <div className="p-4 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel">
          <span className="text-[10px] text-space-400 uppercase tracking-widest block">Total Readings</span>
          <span className="text-2xl font-bold text-space-100 mt-1 block">{totalReadings}</span>
          <span className="text-[10px] text-space-400 mt-0.5 block">Recorded snapshots</span>
        </div>

        <div className="p-4 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel">
          <span className="text-[10px] text-space-400 uppercase tracking-widest block">Avg Stress Index</span>
          <span className="text-2xl font-bold text-cyan-300 mt-1 block">{avgStress.toFixed(1)}%</span>
          <span className="text-[10px] text-space-400 mt-0.5 block">Lifetime mean</span>
        </div>

        <div className="p-4 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel">
          <span className="text-[10px] text-space-400 uppercase tracking-widest block">Lifetime Peak Stress</span>
          <span className="text-2xl font-bold text-amber-400 mt-1 block">{peakStress.toFixed(1)}%</span>
          <span className="text-[10px] text-space-400 mt-0.5 block">Maximum recorded</span>
        </div>

        <div className="p-4 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel">
          <span className="text-[10px] text-space-400 uppercase tracking-widest block">Critical Alerts</span>
          <span className="text-2xl font-bold text-red-400 mt-1 block">{criticalCount}</span>
          <span className="text-[10px] text-space-400 mt-0.5 block">&gt; 75% threshold</span>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────────────────── */}
      {/* 7-Affect Multi-Dimensional Emotion Confidence Trajectory (M-03 to M-09)  */}
      {/* ──────────────────────────────────────────────────────────────────────── */}
      <div className="bg-space-900 border border-space-700 rounded-xl p-5 shadow-glass-panel space-y-4">
        <div>
          {/* M-03: Header */}
          <h3 className="text-sm font-bold uppercase tracking-wider text-space-100 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            📈 Multi-Dimensional Emotion Confidence Trajectory (Rolling 60 Points)
          </h3>
          {/* M-04: Caption */}
          <p className="text-[11px] text-space-400 mt-0.5">
            Continuous line graph tracking all 7 emotion probabilities with color-matching to webcam HUD reticle.
          </p>
        </div>

        {/* 4 Rolling Window KPIs (M-06, M-07, M-08, M-09) */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-center">
          <div className="p-3 rounded bg-space-850 border border-space-800">
            <span className="text-[10px] text-space-400 uppercase block">Dominant Affect</span>
            <span className="text-sm font-bold text-cyan-300 uppercase mt-0.5 block">
              {dominantAffect}
            </span>
          </div>

          <div className="p-3 rounded bg-space-850 border border-space-800">
            <span className="text-[10px] text-space-400 uppercase block">Affect Switches</span>
            <span className="text-sm font-bold text-space-200 mt-0.5 block">
              {affectSwitches} events
            </span>
          </div>

          <div className="p-3 rounded bg-space-850 border border-space-800">
            <span className="text-[10px] text-space-400 uppercase block">Peak Confidence</span>
            <span className="text-sm font-bold text-emerald-400 mt-0.5 block">
              {peakConfidence.toFixed(1)}%
            </span>
          </div>

          <div className="p-3 rounded bg-space-850 border border-space-800">
            <span className="text-[10px] text-space-400 uppercase block">Mean Stress</span>
            <span className="text-sm font-bold text-amber-400 mt-0.5 block">
              {meanWindowStress.toFixed(1)}%
            </span>
          </div>
        </div>

        {/* M-05: 7-Emotion Multi-Line Chart */}
        <div className="h-64 w-full bg-space-950/70 p-3 rounded-lg border border-space-800">
          <Line
            data={emotionTrajectoryData}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              scales: {
                y: {
                  min: 0,
                  max: 100,
                  grid: { color: "rgba(30, 43, 66, 0.4)" },
                  ticks: { color: "#64748b", font: { family: "JetBrains Mono", size: 10 } },
                },
                x: {
                  grid: { display: false },
                  ticks: { color: "#64748b", font: { family: "JetBrains Mono", size: 10 }, maxTicksLimit: 10 },
                },
              },
              plugins: {
                legend: {
                  position: "top",
                  labels: { color: "#94a3b8", font: { family: "JetBrains Mono", size: 10 }, boxWidth: 10 },
                },
              },
            }}
          />
        </div>

        {/* M-10: Stress Index Trend Chart */}
        <div className="pt-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-space-300 block mb-2">
            Stress Index Trajectory (Rolling 60)
          </span>
          <div className="h-36 w-full bg-space-950/70 p-3 rounded-lg border border-space-800">
            <Line
              data={stressTrendData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                  y: {
                    min: 0,
                    max: 100,
                    grid: { color: "rgba(30, 43, 66, 0.4)" },
                    ticks: { color: "#64748b", font: { family: "JetBrains Mono", size: 10 } },
                  },
                  x: {
                    grid: { display: false },
                    ticks: { color: "#64748b", font: { family: "JetBrains Mono", size: 10 }, maxTicksLimit: 10 },
                  },
                },
                plugins: {
                  legend: { display: false },
                },
              }}
            />
          </div>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────────────────── */}
      {/* Categorical Emotion Distribution Histogram (M-16)                        */}
      {/* ──────────────────────────────────────────────────────────────────────── */}
      <div className="bg-space-900 border border-space-700 rounded-xl p-5 shadow-glass-panel space-y-3">
        <h3 className="text-sm font-bold uppercase tracking-wider text-space-100 flex items-center gap-2">
          <BarChart className="w-4 h-4 text-cyan-400" />
          Emotion Distribution Histogram (Lifetime Mission Logged Readings)
        </h3>
        <div className="h-44 w-full bg-space-950/70 p-3 rounded-lg border border-space-800">
          <Bar
            data={histogramData}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              scales: {
                y: {
                  grid: { color: "rgba(30, 43, 66, 0.4)" },
                  ticks: { color: "#64748b", font: { family: "JetBrains Mono", size: 10 } },
                },
                x: {
                  grid: { display: false },
                  ticks: { color: "#94a3b8", font: { family: "JetBrains Mono", size: 10 } },
                },
              },
              plugins: { legend: { display: false } },
            }}
          />
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────────────────── */}
      {/* Full Telemetry Log Table (M-15)                                          */}
      {/* ──────────────────────────────────────────────────────────────────────── */}
      <div className="bg-space-900 border border-space-700 rounded-xl p-5 shadow-glass-panel space-y-3">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <h3 className="text-sm font-bold uppercase tracking-wider text-space-100 flex items-center gap-2">
            <Database className="w-4 h-4 text-cyan-400" />
            Full Telemetry Log Table (All 20 Parameters)
          </h3>

          {/* Search & Filter */}
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-space-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search logs..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="pl-8 pr-3 py-1 rounded bg-space-850 border border-space-700 text-xs font-mono text-space-200 placeholder-space-400 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <select
              value={emotionFilter}
              onChange={(e) => setEmotionFilter(e.target.value)}
              className="py-1 px-2 rounded bg-space-850 border border-space-700 text-xs font-mono text-space-200 focus:outline-none"
            >
              <option value="ALL">ALL AFFECTS</option>
              <option value="HAPPY">HAPPY</option>
              <option value="NEUTRAL">NEUTRAL</option>
              <option value="SURPRISE">SURPRISE</option>
              <option value="SAD">SAD</option>
              <option value="FEAR">FEAR</option>
              <option value="ANGRY">ANGRY</option>
              <option value="DISGUST">DISGUST</option>
            </select>
          </div>
        </div>

        {/* Interactive Data Table */}
        <div className="overflow-x-auto max-h-96 border border-space-800 rounded-lg">
          <table className="w-full text-left font-mono text-[11px] border-collapse">
            <thead className="bg-space-850 text-space-400 sticky top-0 border-b border-space-700">
              <tr>
                <th className="p-2.5">ID</th>
                <th className="p-2.5">Timestamp</th>
                <th className="p-2.5">Fused Affect</th>
                <th className="p-2.5">Stress %</th>
                <th className="p-2.5">Level</th>
                <th className="p-2.5">Heart Rate</th>
                <th className="p-2.5">Temp</th>
                <th className="p-2.5">SpO₂</th>
                <th className="p-2.5">Blink</th>
                <th className="p-2.5">Fatigue</th>
                <th className="p-2.5">Clinical Alert</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-space-800">
              {filteredLogs.map((r, idx) => (
                <tr key={r.id || idx} className="hover:bg-space-850/50 transition-colors">
                  <td className="p-2.5 text-space-400">{r.id || idx + 1}</td>
                  <td className="p-2.5 text-space-300">{r.timestamp}</td>
                  <td className="p-2.5">
                    <span
                      className="px-2 py-0.5 rounded uppercase font-bold text-[10px]"
                      style={{
                        backgroundColor: `${EMOTION_COLORS[(r.fused_emotion || "neutral").toLowerCase()]}20`,
                        color: EMOTION_COLORS[(r.fused_emotion || "neutral").toLowerCase()],
                      }}
                    >
                      {r.fused_emotion || r.face_emotion}
                    </span>
                  </td>
                  <td className="p-2.5 font-bold text-space-100">{r.stress_score?.toFixed(1)}%</td>
                  <td className="p-2.5">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] ${
                        r.stress_level === "CRITICAL"
                          ? "bg-red-500/20 text-red-400"
                          : r.stress_level === "ELEVATED"
                          ? "bg-orange-500/20 text-orange-400"
                          : "bg-emerald-500/20 text-emerald-400"
                      }`}
                    >
                      {r.stress_level}
                    </span>
                  </td>
                  <td className="p-2.5 text-red-300">{r.heart_rate} BPM</td>
                  <td className="p-2.5 text-amber-300">{r.temperature}°C</td>
                  <td className="p-2.5 text-cyan-300">{r.spo2}%</td>
                  <td className="p-2.5 text-purple-300">{r.blink_rate}/m</td>
                  <td className="p-2.5 text-space-300">{r.fatigue_label}</td>
                  <td className="p-2.5 text-space-300 max-w-xs truncate">{r.alert_triggered}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────────────────── */}
      {/* Psychological Dialogue History Table (M-17, M-18)                        */}
      {/* ──────────────────────────────────────────────────────────────────────── */}
      <div className="bg-space-900 border border-space-700 rounded-xl p-5 shadow-glass-panel space-y-3">
        <h3 className="text-sm font-bold uppercase tracking-wider text-space-100 flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-purple-400" />
          🧠 In-Flight AI Psychological Support Dialogue History (Last 50 Turns)
        </h3>
        <div className="overflow-x-auto max-h-64 border border-space-800 rounded-lg">
          <table className="w-full text-left font-mono text-[11px] border-collapse">
            <thead className="bg-space-850 text-space-400 sticky top-0 border-b border-space-700">
              <tr>
                <th className="p-2.5">ID</th>
                <th className="p-2.5">Timestamp</th>
                <th className="p-2.5">Crew Member</th>
                <th className="p-2.5">Channel</th>
                <th className="p-2.5">Astronaut Query</th>
                <th className="p-2.5">Detected Affect</th>
                <th className="p-2.5">Stress %</th>
                <th className="p-2.5">MAITRI Response</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-space-800">
              {psychLogs.map((p, idx) => (
                <tr key={p.id || idx} className="hover:bg-space-850/50 transition-colors">
                  <td className="p-2.5 text-space-400">{p.id || idx + 1}</td>
                  <td className="p-2.5 text-space-300">{p.timestamp}</td>
                  <td className="p-2.5 text-cyan-300">{p.crew_member}</td>
                  <td className="p-2.5 uppercase text-space-400">{p.input_channel}</td>
                  <td className="p-2.5 text-space-100 max-w-xs truncate font-sans">{p.astronaut_query}</td>
                  <td className="p-2.5 uppercase text-amber-300">{p.detected_emotion}</td>
                  <td className="p-2.5 text-red-300">{p.stress_pct?.toFixed(1)}%</td>
                  <td className="p-2.5 text-space-300 max-w-sm truncate font-sans">{p.ai_response}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
