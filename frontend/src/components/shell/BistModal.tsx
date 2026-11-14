import React, { useState, useEffect } from "react";
import { BistReport } from "../../types";
import { runBistDiagnostic, fetchBistStatus } from "../../services/api";
import {
  ShieldCheck,
  ShieldAlert,
  Cpu,
  Camera,
  Mic,
  Database,
  HardDrive,
  RefreshCw,
  X,
  CheckCircle2,
  AlertTriangle,
  Lock,
} from "lucide-react";

interface BistModalProps {
  isOpen: boolean;
  onClose: () => void;
  auditHash?: string;
  auditCount?: number;
}

export const BistModal: React.FC<BistModalProps> = ({
  isOpen,
  onClose,
  auditHash,
  auditCount,
}) => {
  const [report, setReport] = useState<BistReport | null>(null);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && !report) {
      loadStatus();
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const loadStatus = async () => {
    try {
      const data = await fetchBistStatus();
      setReport(data);
      setErrorMsg(null);
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to fetch BIST diagnostic status.");
    }
  };

  const handleRunDiagnostic = async () => {
    setIsRunning(true);
    setErrorMsg(null);
    try {
      const data = await runBistDiagnostic();
      setReport(data);
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to execute BIST diagnostic suite.");
    } finally {
      setIsRunning(false);
    }
  };

  if (!isOpen) return null;

  const renderStatusBadge = (status: string) => {
    if (status === "PASSED") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          PASSED
        </span>
      );
    }
    if (status === "DEGRADED") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30">
          <AlertTriangle className="w-3 h-3 text-amber-400" />
          DEGRADED
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-red-500/20 text-red-400 border border-red-500/30">
        <ShieldAlert className="w-3 h-3 text-red-400" />
        FAILED
      </span>
    );
  };

  const dbSubs = report?.subsystems?.database_cryptography;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="bist-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fadeIn"
    >
      <div className="bg-space-900 border border-space-700 rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-space-700 flex items-center justify-between bg-space-950/70">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2
                id="bist-modal-title"
                className="text-lg font-bold text-space-100 flex items-center gap-2"
              >
                Built-In Self-Test (BIST) & Cryptographic Audit Ledger
              </h2>
              <p className="text-xs text-space-400">
                Autonomous Spacecraft Subsystem Verification & SHA-256 Ledger
                Integrity
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close BIST diagnostic modal"
            className="p-1.5 rounded-lg text-space-400 hover:text-space-100 hover:bg-space-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-sm">
          {errorMsg && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-xs">
              {errorMsg}
            </div>
          )}

          {/* Overall Status Banner */}
          <div className="p-4 rounded-lg bg-space-850 border border-space-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-space-400 uppercase tracking-wider font-mono">
                  Overall System Health:
                </span>
                {report ? renderStatusBadge(report.overall_status) : <span>Loading...</span>}
              </div>
              <p className="text-xs text-space-400 mt-1">
                Last checked:{" "}
                <span className="font-mono text-space-300">
                  {report?.timestamp_iso || "Never"}
                </span>{" "}
                ({report?.duration_ms ? `${report.duration_ms} ms` : "—"})
              </p>
            </div>
            <button
              onClick={handleRunDiagnostic}
              disabled={isRunning}
              className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-xs flex items-center gap-2 disabled:opacity-50 transition shadow-glow-nominal"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRunning ? "animate-spin" : ""}`} />
              {isRunning ? "Running Diagnostic..." : "Run Diagnostic Now"}
            </button>
          </div>

          {/* Subsystem Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Camera */}
            <div className="p-4 rounded-lg bg-space-850/80 border border-space-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-space-200 flex items-center gap-2">
                  <Camera className="w-4 h-4 text-cyan-400" />
                  Optical Camera Feed
                </span>
                {report && renderStatusBadge(report.subsystems.camera.status)}
              </div>
              <p className="text-xs text-space-400">
                {report?.subsystems.camera.details || "Awaiting scan..."}
              </p>
              {report?.subsystems.camera.has_devices && (
                <div className="text-[11px] font-mono text-space-400">
                  Devices: {report.subsystems.camera.device_count} | Capture:{" "}
                  {report.subsystems.camera.capture_success ? "OK" : "NO"}
                </div>
              )}
            </div>

            {/* Microphone */}
            <div className="p-4 rounded-lg bg-space-850/80 border border-space-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-space-200 flex items-center gap-2">
                  <Mic className="w-4 h-4 text-cyan-400" />
                  Acoustic Microphone
                </span>
                {report && renderStatusBadge(report.subsystems.microphone.status)}
              </div>
              <p className="text-xs text-space-400">
                {report?.subsystems.microphone.details || "Awaiting scan..."}
              </p>
            </div>

            {/* Neural Models */}
            <div className="p-4 rounded-lg bg-space-850/80 border border-space-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-space-200 flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-cyan-400" />
                  Air-Gapped Neural Models
                </span>
                {report && renderStatusBadge(report.subsystems.models_on_disk.status)}
              </div>
              <p className="text-xs text-space-400">
                {report?.subsystems.models_on_disk.details || "Awaiting scan..."}
              </p>
              {report?.subsystems.models_on_disk.models_found && (
                <div className="text-[11px] font-mono text-space-400">
                  Bundled models:{" "}
                  {report.subsystems.models_on_disk.models_found.join(", ") || "None"}
                </div>
              )}
            </div>

            {/* Memory & Headroom */}
            <div className="p-4 rounded-lg bg-space-850/80 border border-space-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-space-200 flex items-center gap-2">
                  <HardDrive className="w-4 h-4 text-cyan-400" />
                  Host Memory & RAM Headroom
                </span>
                {report && renderStatusBadge(report.subsystems.memory_ram.status)}
              </div>
              <p className="text-xs text-space-400">
                {report?.subsystems.memory_ram.details || "Awaiting scan..."}
              </p>
              {report?.subsystems.memory_ram && (
                <div className="text-[11px] font-mono text-space-400">
                  Avail: {report.subsystems.memory_ram.available_mb} MB /{" "}
                  {report.subsystems.memory_ram.total_mb} MB (
                  {report.subsystems.memory_ram.percent_used}%)
                </div>
              )}
            </div>
          </div>

          {/* Cryptographic Hash Chain Audit Ledger */}
          <div className="p-4 rounded-lg bg-space-950 border border-space-800 space-y-4">
            <div className="flex items-center justify-between border-b border-space-800 pb-3">
              <div className="flex items-center gap-2">
                <Lock className="w-4 h-4 text-emerald-400" />
                <span className="font-semibold text-space-100">
                  Cryptographic SHA-256 Audit Ledger
                </span>
              </div>
              {dbSubs && renderStatusBadge(dbSubs.status)}
            </div>

            <p className="text-xs text-space-300">{dbSubs?.details}</p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded bg-space-900 border border-space-800 space-y-1">
                <div className="text-space-400 font-mono text-[11px]">
                  LATEST BLOCK HASH (HEAD):
                </div>
                <div className="font-mono text-xs text-cyan-300 break-all select-all">
                  {auditHash || "0000000000000000000000000000000000000000000000000000000000000000"}
                </div>
                <div className="text-[11px] text-space-400">
                  Total Ledger Events:{" "}
                  <span className="font-mono text-space-200">{auditCount ?? 0}</span>
                </div>
              </div>

              <div className="p-3 rounded bg-space-900 border border-space-800 space-y-1">
                <div className="text-space-400 font-mono text-[11px] mb-1">
                  CHAIN VERIFICATION (5 CLINICAL TABLES):
                </div>
                {dbSubs?.hash_chains ? (
                  <div className="space-y-1 font-mono text-[11px]">
                    {Object.entries(dbSubs.hash_chains).map(([chainName, info]: any) => (
                      <div key={chainName} className="flex items-center justify-between">
                        <span className="text-space-300">{chainName}</span>
                        <span
                          className={
                            info.valid ? "text-emerald-400" : "text-red-400 font-bold"
                          }
                        >
                          {info.valid ? "VALID" : `FAILED @ ${info.fail_id}`}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-space-400 text-xs">Awaiting chain scan...</div>
                )}
              </div>
            </div>

            {/* Row Counts */}
            {dbSubs?.table_row_counts && (
              <div className="flex flex-wrap gap-2 pt-2 border-t border-space-800 text-[11px] font-mono text-space-400">
                <span className="text-space-400">Ledger Counts:</span>
                {Object.entries(dbSubs.table_row_counts).map(([tbl, cnt]: any) => (
                  <span key={tbl} className="px-2 py-0.5 rounded bg-space-850 text-space-300 border border-space-800">
                    {tbl}: <strong className="text-space-100">{cnt}</strong>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-space-700 bg-space-950/70 flex items-center justify-between text-xs text-space-400">
          <span>Decisions supported by offline immutable audit hashing</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-space-800 hover:bg-space-700 text-space-200 transition font-medium"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
