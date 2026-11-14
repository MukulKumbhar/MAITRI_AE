import React, { useState, useEffect } from "react";
import { TabId, TelemetryPayload, VoiceDebugInfo } from "./types";
import { Header } from "./components/shell/Header";
import { WatchdogBanner } from "./components/shell/WatchdogBanner";
import { HandsFreeStudyModal } from "./components/shell/HandsFreeStudyModal";
import { VoiceDebugDrawer } from "./components/shell/VoiceDebugDrawer";
import { CabinAudioPlayer } from "./components/shell/CabinAudioPlayer";
import { BistModal } from "./components/shell/BistModal";

import { OverviewTab } from "./components/tabs/OverviewTab";
import { CardioTab } from "./components/tabs/CardioTab";
import { NeuroTab } from "./components/tabs/NeuroTab";
import { CabinTab } from "./components/tabs/CabinTab";
import { MedicalTab } from "./components/tabs/MedicalTab";
import { LiveTab } from "./components/tabs/LiveTab";
import { LogsTab } from "./components/tabs/LogsTab";
import { DemoTab } from "./components/tabs/DemoTab";
import { SupportTab } from "./components/tabs/SupportTab";

import { telemetrySocketService } from "./services/telemetrySocket";
import { audioService } from "./services/audioSocket";
import { acknowledgeWatchdog, pauseAlarmAudio } from "./services/api";

const ALL_TABS: TabId[] = [
  "overview",
  "cardio",
  "neuro",
  "cabin",
  "medical",
  "logs",
  "live",
  "mission",
  "support",
];

export const App: React.FC = () => {
  const getInitialTab = (): TabId => {
    try {
      const hash = window.location.hash.replace("#", "") as TabId;
      if (ALL_TABS.includes(hash)) return hash;
      const params = new URLSearchParams(window.location.search);
      const tab = params.get("tab") as TabId;
      if (ALL_TABS.includes(tab)) return tab;
    } catch {
      // fallback
    }
    return "overview";
  };

  const getInitialStudy = (): boolean => {
    try {
      const params = new URLSearchParams(window.location.search);
      return params.get("study") === "1" || params.get("modal") === "study";
    } catch {
      return false;
    }
  };

  const getInitialVoiceDebug = (): boolean => {
    try {
      const params = new URLSearchParams(window.location.search);
      return params.get("debug") === "1" || params.get("drawer") === "voice";
    } catch {
      return false;
    }
  };

  const [activeTab, setActiveTab] = useState<TabId>(getInitialTab());
  const [telemetry, setTelemetry] = useState<TelemetryPayload | null>(null);
  const [isStudyOpen, setIsStudyOpen] = useState<boolean>(getInitialStudy());
  const [isVoiceDebugOpen, setIsVoiceDebugOpen] = useState<boolean>(getInitialVoiceDebug());
  const [isBistOpen, setIsBistOpen] = useState<boolean>(false);
  const [isCircadianNight, setIsCircadianNight] = useState<boolean>(false);
  const [voiceDebugState, setVoiceDebugState] = useState<VoiceDebugInfo>(audioService.debugState);
  const [isMicCapturing, setIsMicCapturing] = useState<boolean>(false);

  // Keep URL hash in sync with activeTab
  useEffect(() => {
    try {
      window.location.hash = activeTab;
    } catch {}
  }, [activeTab]);

  // Initialize WebSockets on mount
  useEffect(() => {
    telemetrySocketService.connect();
    audioService.connect();

    // Subscribe to telemetry state
    const unsubTelemetry = telemetrySocketService.subscribe((payload) => {
      setTelemetry(payload);
    });

    // Subscribe to audio / voice events
    const unsubAudio = audioService.addEventListener((event) => {
      setVoiceDebugState({ ...audioService.debugState });
      setIsMicCapturing(audioService.getIsCapturing());

      // Autonomous Voice Director Action Execution
      if (event.type === "voice_action_dispatched") {
        if (event.action === "navigate" && event.target) {
          const targetTab = event.target as TabId;
          if (ALL_TABS.includes(targetTab)) {
            setActiveTab(targetTab);
          }
        } else if (event.action === "circadian_night" || event.action === "night_mode") {
          setIsCircadianNight(true);
        } else if (event.action === "day_mode") {
          setIsCircadianNight(false);
        } else if (
          event.action === "watchdog_ack" ||
          event.action === "critical_override_confirmed"
        ) {
          acknowledgeWatchdog();
        }
      }
    });

    return () => {
      unsubTelemetry();
      unsubAudio();
    };
  }, []);

  // Hotkey Listener (Keys 1-5 for instant view switching)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is currently typing inside an input or textarea
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        return;
      }

      if (e.key === "1") {
        e.preventDefault();
        setActiveTab("overview");
      } else if (e.key === "2") {
        e.preventDefault();
        setActiveTab("cardio");
      } else if (e.key === "3") {
        e.preventDefault();
        setActiveTab("neuro");
      } else if (e.key === "4") {
        e.preventDefault();
        setActiveTab("cabin");
      } else if (e.key === "5") {
        e.preventDefault();
        setActiveTab("medical");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Watchdog handlers
  const handleWatchdogAck = async () => {
    await acknowledgeWatchdog();
    telemetrySocketService.sendWatchdogAck();
  };

  const handleWatchdogReset = async () => {
    await acknowledgeWatchdog();
    telemetrySocketService.sendWatchdogAck();
  };

  const handleToggleMic = async () => {
    if (!isMicCapturing) {
      const ok = await audioService.startMicrophoneCapture();
      setIsMicCapturing(ok);
    } else {
      audioService.stopMicrophoneCapture();
      setIsMicCapturing(false);
    }
  };

  const handlePauseAlarmAudio = async () => {
    try {
      await pauseAlarmAudio(120.0);
    } catch {}
  };

  return (
    <div
      className={`min-h-screen bg-space-950 text-space-100 flex flex-col font-sans transition-colors duration-500 ${
        isCircadianNight ? "night-circadian" : ""
      }`}
    >
      {/* Shell Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isCircadianNight={isCircadianNight}
        onToggleCircadianNight={() => setIsCircadianNight((prev) => !prev)}
        onOpenBist={() => setIsBistOpen(true)}
        alarms={telemetry?.alarms}
        onPauseAlarmAudio={handlePauseAlarmAudio}
        onOpenStudy={() => setIsStudyOpen(true)}
        onOpenVoiceDebug={() => setIsVoiceDebugOpen(true)}
        isVoiceSpeaking={voiceDebugState.is_speaking}
        isVoskReady={voiceDebugState.vosk_ready}
        isMicCapturing={isMicCapturing}
        onToggleMic={handleToggleMic}
        auditHash={telemetry?.security?.audit_hash}
      />

      {/* Global Watchdog Banner */}
      {telemetry?.watchdog && (
        <WatchdogBanner
          watchdog={telemetry.watchdog}
          onAcknowledge={handleWatchdogAck}
          onReset={handleWatchdogReset}
        />
      )}

      {/* Main Tab Content */}
      <main className="flex-1 p-4 lg:p-6 max-w-7xl w-full mx-auto">
        {activeTab === "overview" && (
          <OverviewTab telemetry={telemetry} onNavigateTab={setActiveTab} />
        )}
        {activeTab === "cardio" && <CardioTab telemetry={telemetry} />}
        {activeTab === "neuro" && <NeuroTab telemetry={telemetry} />}
        {activeTab === "cabin" && <CabinTab telemetry={telemetry} />}
        {activeTab === "medical" && <MedicalTab />}
        {activeTab === "live" && (
          <LiveTab telemetry={telemetry} onNavigateTab={setActiveTab} />
        )}
        {activeTab === "logs" && <LogsTab />}
        {activeTab === "mission" && (
          <DemoTab onSimulateWatchdogSuccess={() => {}} />
        )}
        {activeTab === "support" && <SupportTab telemetry={telemetry} />}
      </main>

      {/* Built-In Self-Test & Cryptographic Ledger Modal */}
      <BistModal
        isOpen={isBistOpen}
        onClose={() => setIsBistOpen(false)}
        auditHash={telemetry?.security?.audit_hash}
        auditCount={telemetry?.security?.entry_count}
      />

      {/* Astronaut Hands-Free Navigation Study Modal */}
      <HandsFreeStudyModal
        isOpen={isStudyOpen}
        onClose={() => setIsStudyOpen(false)}
      />

      {/* Voice Debug HUD Drawer */}
      <VoiceDebugDrawer
        isOpen={isVoiceDebugOpen}
        onClose={() => setIsVoiceDebugOpen(false)}
        debugState={voiceDebugState}
        isCapturing={isMicCapturing}
        onToggleMic={handleToggleMic}
      />

      {/* Global Cabin Audio Autoplay */}
      <CabinAudioPlayer />
    </div>
  );
};

export default App;
