import React, { useState, useEffect } from "react";
import { TabId, TelemetryPayload, VoiceDebugInfo } from "./types";
import { Header } from "./components/shell/Header";
import { WatchdogBanner } from "./components/shell/WatchdogBanner";
import { HandsFreeStudyModal } from "./components/shell/HandsFreeStudyModal";
import { VoiceDebugDrawer } from "./components/shell/VoiceDebugDrawer";
import { CabinAudioPlayer } from "./components/shell/CabinAudioPlayer";
import { LiveTab } from "./components/tabs/LiveTab";
import { LogsTab } from "./components/tabs/LogsTab";
import { DemoTab } from "./components/tabs/DemoTab";
import { SupportTab } from "./components/tabs/SupportTab";

import { telemetrySocketService } from "./services/telemetrySocket";
import { audioService } from "./services/audioSocket";
import { acknowledgeWatchdog } from "./services/api";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>("live");
  const [telemetry, setTelemetry] = useState<TelemetryPayload | null>(null);
  const [isStudyOpen, setIsStudyOpen] = useState<boolean>(false);
  const [isVoiceDebugOpen, setIsVoiceDebugOpen] = useState<boolean>(false);
  const [voiceDebugState, setVoiceDebugState] = useState<VoiceDebugInfo>(audioService.debugState);
  const [isMicCapturing, setIsMicCapturing] = useState<boolean>(false);

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

      // G-07: Autonomous Voice Director Action Execution
      if (event.type === "voice_action_dispatched") {
        if (event.action === "navigate" && event.target) {
          const targetTab = event.target as TabId;
          setActiveTab(targetTab);
        } else if (event.action === "watchdog_ack" || event.action === "critical_override_confirmed") {
          acknowledgeWatchdog();
        }
      }
    });

    return () => {
      unsubTelemetry();
      unsubAudio();
    };
  }, []);

  // G-09: Tactile Hotkey Listener (Keys 1-4 for instant view switching)
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
        setActiveTab("live");
      } else if (e.key === "2") {
        e.preventDefault();
        setActiveTab("logs");
      } else if (e.key === "3") {
        e.preventDefault();
        setActiveTab("mission");
      } else if (e.key === "4") {
        e.preventDefault();
        setActiveTab("support");
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

  return (
    <div className="min-h-screen bg-space-950 text-space-100 flex flex-col font-sans">
      {/* Shell Header (G-01, G-02, G-10) */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenStudy={() => setIsStudyOpen(true)}
        onOpenVoiceDebug={() => setIsVoiceDebugOpen(true)}
        isVoiceSpeaking={voiceDebugState.is_speaking}
        isVoskReady={voiceDebugState.vosk_ready}
        isMicCapturing={isMicCapturing}
        onToggleMic={handleToggleMic}
      />

      {/* Global Watchdog Banner (G-03, G-04, G-05) */}
      {telemetry?.watchdog && (
        <WatchdogBanner
          watchdog={telemetry.watchdog}
          onAcknowledge={handleWatchdogAck}
          onReset={handleWatchdogReset}
        />
      )}

      {/* Main Tab Content */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto">
        {activeTab === "live" && (
          <LiveTab telemetry={telemetry} onNavigateTab={setActiveTab} />
        )}
        {activeTab === "logs" && <LogsTab />}
        {activeTab === "mission" && (
          <DemoTab onSimulateWatchdogSuccess={() => {}} />
        )}
        {activeTab === "support" && <SupportTab telemetry={telemetry} />}
      </main>

      {/* G-08: Astronaut Hands-Free Navigation Study Collapsible/Modal */}
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

      {/* G-06: Global Cabin Audio Autoplay */}
      <CabinAudioPlayer />
    </div>
  );
};

export default App;
