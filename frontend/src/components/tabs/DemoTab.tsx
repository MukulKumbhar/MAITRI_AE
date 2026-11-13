import React, { useEffect, useState } from "react";
import { MissionStatus } from "../../types";
import {
  fetchMissionStatus,
  updateMissionProfile,
  compileDossier,
  simulateWatchdog,
} from "../../services/api";
import {
  Radio,
  FileText,
  Clock,
  Send,
  Download,
  AlertTriangle,
  UserCheck,
  CheckCircle,
  RefreshCw,
  Eye,
} from "lucide-react";

interface DemoTabProps {
  onSimulateWatchdogSuccess: () => void;
}

export const DemoTab: React.FC<DemoTabProps> = ({ onSimulateWatchdogSuccess }) => {
  const [missionStatus, setMissionStatus] = useState<MissionStatus | null>(null);
  const [selectedMission, setSelectedMission] = useState<string>("ISRO Gaganyaan (LEO)");
  const [selectedCrew, setSelectedCrew] = useState<string>("Cdr. A. Sharma (Pilot / CMO)");
  const [dossierMd, setDossierMd] = useState<string | null>(null);
  const [isCompiling, setIsCompiling] = useState<boolean>(false);
  const [showPreview, setShowPreview] = useState<boolean>(true);

  const loadStatus = async () => {
    try {
      const data = await fetchMissionStatus();
      setMissionStatus(data);
      if (data.mission) setSelectedMission(data.mission);
      if (data.crew) setSelectedCrew(data.crew);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  // Update profile
  const handleProfileChange = async (mission: string, crew: string) => {
    setSelectedMission(mission);
    setSelectedCrew(crew);
    try {
      await updateMissionProfile(mission, crew);
      await loadStatus();
    } catch (e) {
      console.error(e);
    }
  };

  // Simulate watchdog check-in (D-03)
  const handleSimulateWatchdog = async () => {
    try {
      await simulateWatchdog();
      onSimulateWatchdogSuccess();
    } catch (e) {
      console.error(e);
    }
  };

  // Force compile medical dossier (D-04)
  const handleCompileDossier = async () => {
    setIsCompiling(true);
    try {
      const res = await compileDossier();
      setDossierMd(res.markdown);
      await loadStatus();
    } catch (e) {
      console.error(e);
    } finally {
      setIsCompiling(false);
    }
  };

  // Download dossier as .md file (D-11)
  const handleDownloadDossier = () => {
    if (!dossierMd) return;
    const blob = new Blob([dossierMd], { type: "text/markdown;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Medical_Dossier_${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const latencyFormatted = missionStatus?.dtn?.latency_formatted || (missionStatus?.dtn as any)?.latency_display || "500 ms";
  const packets = missionStatus?.dtn?.packets || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12 font-sans">
      {/* D-01: Demo Scenarios Subheader */}
      <div className="border-b border-space-800 pb-4">
        <h2 className="text-base font-bold uppercase tracking-wider text-space-100 flex items-center gap-2">
          <Radio className="w-5 h-5 text-cyan-400" />
          🎬 Presentation Demo Scenarios &amp; Mission Control Hub
        </h2>
        {/* D-02: Demo Guidance Callout */}
        <p className="text-xs text-space-400 mt-1">
          Trigger simulated aerospace contingencies and compile Delay-Tolerant Networking (DTN) telemetry dossiers.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Mission Profile & Demo Scenario Buttons */}
        <div className="space-y-6">
          {/* Mission Profile & Astronaut Selector (D-05, D-06) */}
          <div className="p-5 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-space-200 flex items-center gap-2">
              <UserCheck className="w-4 h-4 text-cyan-400" />
              Mission Flight Profile &amp; Crew Assignment
            </h3>

            {/* D-05: Mission Profile Selector */}
            <div className="space-y-1.5 font-mono text-xs">
              <label className="text-space-400">🚀 Select Mission Profile:</label>
              <select
                value={selectedMission}
                onChange={(e) => handleProfileChange(e.target.value, selectedCrew)}
                className="w-full p-2.5 rounded-lg bg-space-850 border border-space-700 text-space-100 focus:outline-none focus:border-cyan-500"
              >
                <option value="ISRO Gaganyaan (LEO)">ISRO Gaganyaan (LEO) — 0.5s Latency</option>
                <option value="Artemis Gateway (Lunar)">Artemis Gateway (Lunar) — 2.4s Latency</option>
                <option value="Mars Transit (Deep Space)">Mars Transit (Deep Space) — 420.0s Latency</option>
              </select>
            </div>

            {/* D-06: Active Astronaut Selector */}
            <div className="space-y-1.5 font-mono text-xs">
              <label className="text-space-400">👨‍🚀 Active Astronaut Subject:</label>
              <select
                value={selectedCrew}
                onChange={(e) => handleProfileChange(selectedMission, e.target.value)}
                className="w-full p-2.5 rounded-lg bg-space-850 border border-space-700 text-space-100 focus:outline-none focus:border-cyan-500"
              >
                <option value="Cdr. A. Sharma (Pilot / CMO)">Cdr. A. Sharma (Pilot / CMO)</option>
                <option value="Lt. Cdr. P. Nair (Flight Engineer)">Lt. Cdr. P. Nair (Flight Engineer)</option>
                <option value="Dr. V. Rao (Mission Specialist)">Dr. V. Rao (Mission Specialist)</option>
              </select>
            </div>
          </div>

          {/* Contingency Simulation Buttons (D-03, D-04) */}
          <div className="p-5 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-space-200 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              Safety Protocols &amp; Presentation Controls
            </h3>

            <div className="space-y-3">
              {/* D-03: Simulate Watchdog Button */}
              <button
                onClick={handleSimulateWatchdog}
                className="w-full py-3 px-4 rounded-lg bg-amber-600/30 hover:bg-amber-600/40 text-amber-200 border border-amber-500/60 font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-sm"
              >
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                ⚡ Simulate Watchdog Check-In (15s Countdown)
              </button>
              <p className="text-[11px] text-space-400 px-1">
                Forces the watchdog into CHECK_IN state immediately without waiting 45 seconds of physical inactivity.
              </p>

              {/* D-04: Force Compile Medical Dossier Button */}
              <button
                onClick={handleCompileDossier}
                disabled={isCompiling}
                className="w-full py-3 px-4 rounded-lg bg-cyan-700 hover:bg-cyan-600 text-white font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-lg"
              >
                <FileText className="w-4 h-4 text-cyan-300" />
                {isCompiling ? "Compiling Telemetry Dossier..." : "📄 Force Compile Medical Dossier"}
              </button>
              <p className="text-[11px] text-space-400 px-1">
                Aggregates current crew physiological vitals, affective state &amp; dispatches audit packet to DTN outbox.
              </p>
            </div>
          </div>
        </div>

        {/* Right Column: Ground DTN Outbox (D-07, D-08, D-09) */}
        <div className="p-5 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel flex flex-col justify-between">
          <div className="space-y-4">
            {/* D-07: Ground DTN Outbox Subheader */}
            <div className="flex items-center justify-between border-b border-space-800 pb-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-space-200 flex items-center gap-2">
                <Send className="w-4 h-4 text-cyan-400" />
                📡 Ground DTN Outbox (Delay-Tolerant Networking)
              </h3>
              {/* D-08: Propagation Delay Readout */}
              <span className="font-mono text-xs px-2.5 py-1 rounded bg-space-850 border border-space-800 text-cyan-300 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-cyan-400" />
                Delay: {latencyFormatted}
              </span>
            </div>

            <p className="text-[11px] text-space-400">
              Bundle Protocol (RFC 9171) store-and-forward queue archiving clinical telemetry packets awaiting line-of-sight ground passes.
            </p>

            {/* D-09: DTN Packet Queue List */}
            <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
              {packets.length === 0 ? (
                <div className="p-4 rounded-lg bg-space-950/60 border border-space-800 text-center text-xs text-space-400 font-mono">
                  DTN Queue empty. Click "Force Compile Medical Dossier" to enqueue a clinical telemetry packet.
                </div>
              ) : (
                packets.map((pkt) => (
                  <div
                    key={pkt.packet_id}
                    className="p-3 rounded-lg bg-space-850 border border-space-800 font-mono text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-cyan-400">{pkt.packet_id}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30">
                        {pkt.status}
                      </span>
                    </div>
                    <p className="text-space-300 text-[11px] font-sans">{pkt.summary}</p>
                    <div className="flex justify-between text-[10px] text-space-400">
                      <span>Priority: {pkt.priority}</span>
                      <span>Enqueued: {new Date(pkt.created_at * 1000).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-space-800 text-[11px] font-mono text-space-400 flex justify-between items-center">
            <span>DTN Mode: Store &amp; Forward</span>
            <span>Queued: {packets.length} bundles</span>
          </div>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────────────────── */}
      {/* Compiled Clinical Dossier Section (D-10, D-11, D-12)                    */}
      {/* ──────────────────────────────────────────────────────────────────────── */}
      {dossierMd && (
        <div className="p-5 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-4 animate-fade-in">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-space-800 pb-3">
            {/* D-10: Clinical Dossier Section Header */}
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-space-100 flex items-center gap-2">
                <FileText className="w-4 h-4 text-cyan-400" />
                📄 Compiled Medical Telemetry Dossier
              </h3>
              <p className="text-[11px] text-space-400 mt-0.5">
                Cryptographically audited Markdown dossier generated for flight surgeons and ground medical team.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowPreview(!showPreview)}
                className="px-3 py-1.5 rounded bg-space-850 hover:bg-space-800 text-space-300 border border-space-700 text-xs font-mono flex items-center gap-1.5"
              >
                <Eye className="w-3.5 h-3.5" />
                {showPreview ? "Collapse" : "Preview"}
              </button>

              {/* D-11: Download Dossier Button */}
              <button
                onClick={handleDownloadDossier}
                className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs uppercase tracking-wider flex items-center gap-1.5 shadow-md transition-all"
              >
                <Download className="w-4 h-4" />
                📥 Download Dossier (.md)
              </button>
            </div>
          </div>

          {/* D-12: Dossier Markdown Preview */}
          {showPreview && (
            <div className="p-4 rounded-lg bg-space-950 border border-space-800 font-mono text-xs text-space-200 overflow-x-auto max-h-80 whitespace-pre-wrap leading-relaxed">
              {dossierMd}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
