import React from "react";
import { WatchdogTelemetry } from "../../types";
import { AlertTriangle, ShieldAlert, CheckCircle, RefreshCw } from "lucide-react";

interface WatchdogBannerProps {
  watchdog: WatchdogTelemetry;
  onAcknowledge: () => void;
  onReset: () => void;
}

export const WatchdogBanner: React.FC<WatchdogBannerProps> = ({
  watchdog,
  onAcknowledge,
  onReset,
}) => {
  if (watchdog.state === "NORMAL") return null;

  const isIncapacitated = watchdog.state === "INCAPACITATED";

  return (
    <div
      className={`px-6 py-3 border-b flex flex-col sm:flex-row items-center justify-between gap-3 transition-all ${
        isIncapacitated
          ? "bg-red-950/90 border-red-500/80 text-red-200 animate-pulse shadow-glow-critical"
          : "bg-amber-950/80 border-amber-500/80 text-amber-200"
      }`}
    >
      <div className="flex items-center gap-3">
        {isIncapacitated ? (
          <ShieldAlert className="w-6 h-6 text-red-400 shrink-0 animate-bounce" />
        ) : (
          <AlertTriangle className="w-6 h-6 text-amber-400 shrink-0" />
        )}
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm tracking-wide uppercase">
              {isIncapacitated
                ? "🚨 ASTRONAUT INCAPACITATION PROTOCOL ACTIVE"
                : "⚠️ ASTRONAUT SAFETY CHECK-IN REQUIRED"}
            </span>
            {!isIncapacitated && (
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/40 text-amber-300">
                {watchdog.countdown}s remaining
              </span>
            )}
          </div>
          <p className="text-xs opacity-90">
            {watchdog.message ||
              (isIncapacitated
                ? "No crew response detected within critical threshold. Telemetry broadcasting to Ground DTN."
                : "Continuous inactivity threshold reached. Please verify crew awareness.")}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {isIncapacitated ? (
          <button
            onClick={onReset}
            className="px-4 py-2 rounded bg-red-600 hover:bg-red-500 text-white text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-lg transition-all"
          >
            <RefreshCw className="w-4 h-4" />
            🔄 Override & Reset System
          </button>
        ) : (
          <button
            onClick={onAcknowledge}
            className="px-4 py-2 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-lg transition-all"
          >
            <CheckCircle className="w-4 h-4" />
            ✅ Acknowledge Watchdog
          </button>
        )}
      </div>
    </div>
  );
};
