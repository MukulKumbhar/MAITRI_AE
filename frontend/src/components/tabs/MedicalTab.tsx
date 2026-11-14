import React, { useState, useEffect } from "react";
import {
  EmergencyChecklist,
  ChecklistStep,
  MedicalArticle,
  ChatMessage,
} from "../../types";
import {
  fetchEmergencyChecklists,
  fetchMedicalReferences,
  postPsychChat,
} from "../../services/api";
import {
  Stethoscope,
  AlertTriangle,
  BookOpen,
  Search,
  MessageSquare,
  Volume2,
  CheckSquare,
  Square,
  RotateCcw,
  Send,
  Sparkles,
  ShieldAlert,
  ExternalLink,
  Flame,
  CheckCircle2,
  Bot,
  User,
} from "lucide-react";

export const MedicalTab: React.FC = () => {
  // ── Emergency Checklists State ──────────────────────────────────────────────
  const [checklists, setChecklists] = useState<EmergencyChecklist[]>([]);
  const [selectedChecklistId, setSelectedChecklistId] = useState<string>("checklist_ammonia");
  const [completedSteps, setCompletedSteps] = useState<Record<string, Record<number, boolean>>>({
    checklist_ammonia: {},
    checklist_trauma: {},
    checklist_ocular_debris: {},
  });
  const [isSpeakingStep, setIsSpeakingStep] = useState<number | null>(null);

  // ── Curated Medical Reference KB State ──────────────────────────────────────
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [articles, setArticles] = useState<MedicalArticle[]>([]);
  const [selectedArticle, setSelectedArticle] = useState<MedicalArticle | null>(null);
  const [kbLoading, setKbLoading] = useState<boolean>(false);

  // ── Local Phi-3 Clinical AI Console State ───────────────────────────────────
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "init",
      role: "assistant",
      text: "MAITRI Clinical AI Assistant initialized. I am grounded solely in local aerospace medicine references (NASA-STD-3001, Law et al. 2014, Mader et al. 2011). How may I assist the Crew Medical Officer today?",
      timestamp: new Date().toLocaleTimeString(),
      citations: ["NASA-STD-3001 Vol 1 & 2", "ISS Flight Operations Manual Section 14"],
    },
  ]);
  const [chatInput, setChatInput] = useState<string>("");
  const [chatLoading, setChatLoading] = useState<boolean>(false);

  // Load checklists and KB on mount
  useEffect(() => {
    fetchEmergencyChecklists()
      .then((data) => {
        setChecklists(data.checklists || []);
        if (data.checklists && data.checklists.length > 0) {
          setSelectedChecklistId(data.checklists[0].id);
        }
      })
      .catch(() => {});

    loadArticles();
  }, []);

  const loadArticles = async (query?: string) => {
    setKbLoading(true);
    try {
      const data = await fetchMedicalReferences(query);
      setArticles(data.references || []);
      if (data.references && data.references.length > 0 && !selectedArticle) {
        setSelectedArticle(data.references[0]);
      }
    } finally {
      setKbLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadArticles(searchQuery);
  };

  // Toggle step completion
  const handleToggleStep = (checklistId: string, stepNum: number) => {
    setCompletedSteps((prev) => ({
      ...prev,
      [checklistId]: {
        ...prev[checklistId],
        [stepNum]: !prev[checklistId]?.[stepNum],
      },
    }));
  };

  // Reset current checklist
  const handleResetChecklist = (checklistId: string) => {
    setCompletedSteps((prev) => ({
      ...prev,
      [checklistId]: {},
    }));
  };

  // Voice readout for step
  const handleSpeakStep = (step: ChecklistStep) => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const text = `Step ${step.step_number}. ${step.action}. ${step.instruction}`;
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      setIsSpeakingStep(step.step_number);
      utterance.onend = () => setIsSpeakingStep(null);
      utterance.onerror = () => setIsSpeakingStep(null);
      window.speechSynthesis.speak(utterance);
    }
  };

  // Chat submit
  const handleSendChat = async (queryText?: string) => {
    const textToSend = queryText || chatInput;
    if (!textToSend.trim()) return;

    const userMsg: ChatMessage = {
      id: String(Date.now()),
      role: "user",
      text: textToSend,
      timestamp: new Date().toLocaleTimeString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setChatInput("");
    setChatLoading(true);

    try {
      const res = await postPsychChat(textToSend, "medical");
      const botMsg: ChatMessage = {
        id: String(Date.now() + 1),
        role: "assistant",
        text: res.reply || "No response received from clinical knowledge base.",
        timestamp: new Date().toLocaleTimeString(),
        audioBase64: res.audio_base64,
      };
      setMessages((prev) => [...prev, botMsg]);

      // Play audio if available
      if (res.audio_base64) {
        try {
          const audio = new Audio(`data:audio/wav;base64,${res.audio_base64}`);
          audio.play().catch(() => {});
        } catch {}
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: String(Date.now() + 1),
          role: "assistant",
          text: "I am restricted to verified spacecraft clinical references and cannot diagnose, speculate, or advise outside my curated local aerospace knowledge base. Please consult the Flight Surgeon or Crew Medical Officer via DTN telemetry outbox.",
          timestamp: new Date().toLocaleTimeString(),
          refusal: true,
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const activeChecklist = checklists.find((c) => c.id === selectedChecklistId);

  return (
    <div className="space-y-6">
      {/* ── Decision Support Notice Banner ──────────────────────────────────── */}
      <div className="p-3.5 rounded-xl bg-cyan-950/30 border border-cyan-500/40 flex items-start gap-3 text-xs text-cyan-200">
        <Stethoscope className="w-4 h-4 text-cyan-400 mt-0.5 shrink-0" />
        <div>
          <strong className="text-cyan-100 uppercase tracking-wider block font-mono text-[11px]">
            CLINICAL DECISION SUPPORT NOTICE (NON-MEDICAL DEVICE)
          </strong>
          <span>
            MAITRI is an autonomous onboard decision support tool for crewed spaceflight, NOT an automated diagnostic device.
            All recommendations must be corroborated by the Crew Medical Officer (CMO) or Mission Control Flight Surgeon.
          </span>
        </div>
      </div>

      {/* ── 1. Step-by-Step Voice-Guided Emergency Checklists ──────────────── */}
      <section
        aria-label="Step-by-Step Emergency Checklists"
        className="p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-6"
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-space-800 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-red-400" />
              <h2 className="text-sm font-bold text-space-100 uppercase tracking-wider">
                Voice-Guided Step-by-Step Emergency Protocols
              </h2>
            </div>
            <p className="text-xs text-space-400">
              Interactive Hands-Free Astronaut Checklists with Spoken Talkback &amp; Critical Safety Triggers
            </p>
          </div>

          {/* Checklist Selector Pills */}
          <div className="flex flex-wrap gap-1.5 bg-space-950 p-1 rounded-lg border border-space-800">
            {checklists.map((cl) => (
              <button
                key={cl.id}
                onClick={() => setSelectedChecklistId(cl.id)}
                className={`px-3 py-1 rounded text-xs font-mono font-bold transition flex items-center gap-1.5 ${
                  selectedChecklistId === cl.id
                    ? "bg-red-600 text-white shadow-sm"
                    : "text-space-400 hover:text-space-200"
                }`}
              >
                <span>{cl.title.split(" ")[0]}</span>
                <span className="text-[9px] px-1 py-0.2 rounded bg-black/40">
                  {cl.priority}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Selected Checklist Detail */}
        {activeChecklist ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-space-100 flex items-center gap-2">
                  <span>{activeChecklist.title}</span>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-red-500/20 text-red-300 border border-red-500/40">
                    {activeChecklist.priority}
                  </span>
                </h3>
                <p className="text-xs text-space-400 mt-0.5">
                  Source: {activeChecklist.source}
                </p>
              </div>

              <button
                onClick={() => handleResetChecklist(activeChecklist.id)}
                className="px-2.5 py-1 rounded bg-space-850 hover:bg-space-800 text-space-400 hover:text-space-200 border border-space-700 text-xs font-mono flex items-center gap-1 transition"
                title="Reset completed checklist steps"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Reset</span>
              </button>
            </div>

            {/* Checklist Steps List */}
            <div className="space-y-3">
              {activeChecklist.steps.map((step) => {
                const isChecked =
                  completedSteps[activeChecklist.id]?.[step.step_number] || false;
                const isSpeaking = isSpeakingStep === step.step_number;

                return (
                  <div
                    key={step.step_number}
                    className={`p-4 rounded-xl border flex items-start gap-4 transition ${
                      isChecked
                        ? "bg-space-950/60 border-space-800 opacity-70"
                        : step.critical
                        ? "bg-red-950/20 border-red-500/40"
                        : "bg-space-850 border-space-800"
                    }`}
                  >
                    {/* Checkbox */}
                    <button
                      type="button"
                      onClick={() => handleToggleStep(activeChecklist.id, step.step_number)}
                      aria-label={`Mark step ${step.step_number} as ${isChecked ? "incomplete" : "complete"}`}
                      className="mt-0.5 text-space-300 hover:text-cyan-400 transition shrink-0"
                    >
                      {isChecked ? (
                        <CheckSquare className="w-5 h-5 text-emerald-400" />
                      ) : (
                        <Square className="w-5 h-5" />
                      )}
                    </button>

                    {/* Step Body */}
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-cyan-400">
                          STEP {step.step_number}
                        </span>
                        <span
                          className={`text-sm font-bold ${
                            isChecked ? "line-through text-space-400" : "text-space-100"
                          }`}
                        >
                          {step.action}
                        </span>
                        {step.critical && (
                          <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-red-600 text-white">
                            CRITICAL
                          </span>
                        )}
                      </div>

                      <p
                        className={`text-xs leading-relaxed ${
                          isChecked ? "line-through text-space-500" : "text-space-300"
                        }`}
                      >
                        {step.instruction}
                      </p>
                    </div>

                    {/* Voice Readout Button */}
                    <button
                      type="button"
                      onClick={() => handleSpeakStep(step)}
                      aria-label={`Listen to step ${step.step_number} instructions`}
                      className={`p-2 rounded-lg border text-xs font-mono flex items-center gap-1 shrink-0 transition ${
                        isSpeaking
                          ? "bg-cyan-500/30 text-cyan-300 border-cyan-500 animate-pulse"
                          : "bg-space-800 text-space-400 hover:text-space-200 border-space-700"
                      }`}
                      title="Read Step Aloud (Voice Talkback)"
                    >
                      <Volume2 className="w-4 h-4" />
                      <span className="hidden sm:inline">Voice</span>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="text-space-400 text-xs">Loading checklists...</div>
        )}
      </section>

      {/* ── 2. Offline Curated Medical Reference Library ──────────────────── */}
      <section
        aria-label="Offline Aerospace Medical Reference Library"
        className="p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-6"
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-space-800 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-cyan-400" />
              <h2 className="text-sm font-bold text-space-100 uppercase tracking-wider">
                Offline Curated Medical Knowledge Base
              </h2>
            </div>
            <p className="text-xs text-space-400">
              Verified PubMed &amp; NASA Clinical Citations • Self-Contained Air-Gapped Search
            </p>
          </div>

          {/* Search Box */}
          <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 w-full sm:w-auto">
            <div className="relative w-full sm:w-64">
              <Search className="w-4 h-4 text-space-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search references (e.g. CO2, SANS)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-space-850 border border-space-700 text-xs text-space-100 placeholder-space-500 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <button
              type="submit"
              disabled={kbLoading}
              className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold transition shrink-0"
            >
              Search
            </button>
          </form>
        </div>

        {/* KB Grid: Article List & Detail */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Article Titles List (5 cols) */}
          <div className="lg:col-span-5 space-y-2 max-h-96 overflow-y-auto pr-1">
            {articles.map((art) => (
              <div
                key={art.id}
                onClick={() => setSelectedArticle(art)}
                role="button"
                tabIndex={0}
                className={`p-3.5 rounded-lg border text-left transition cursor-pointer space-y-1 ${
                  selectedArticle?.id === art.id
                    ? "bg-cyan-950/40 border-cyan-500 shadow-glow-nominal"
                    : "bg-space-850 border-space-800 hover:border-space-700"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-space-100">{art.title}</span>
                  <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-space-950 text-cyan-400 border border-space-800">
                    {art.category}
                  </span>
                </div>
                <p className="text-[11px] text-space-400 line-clamp-2">
                  {art.summary}
                </p>
              </div>
            ))}
          </div>

          {/* Article Full Detail View (7 cols) */}
          <div className="lg:col-span-7 p-5 rounded-xl bg-space-850 border border-space-800 space-y-4 text-xs">
            {selectedArticle ? (
              <>
                <div className="border-b border-space-800 pb-3">
                  <span className="text-[10px] font-mono text-cyan-400 uppercase font-bold block mb-1">
                    {selectedArticle.category} &bull; ID: {selectedArticle.id}
                  </span>
                  <h3 className="text-base font-bold text-space-100">
                    {selectedArticle.title}
                  </h3>
                </div>

                <div className="space-y-1.5">
                  <span className="text-[10px] font-mono text-space-400 uppercase font-bold">
                    Aerospace Clinical Summary:
                  </span>
                  <p className="text-space-300 leading-relaxed">
                    {selectedArticle.summary}
                  </p>
                </div>

                <div className="space-y-1.5">
                  <span className="text-[10px] font-mono text-emerald-400 uppercase font-bold">
                    Clinical Management &amp; Countermeasures:
                  </span>
                  <pre className="p-3 rounded-lg bg-space-950 border border-space-800 text-[11px] font-sans text-space-200 whitespace-pre-wrap leading-relaxed">
                    {selectedArticle.clinical_management}
                  </pre>
                </div>

                <div className="space-y-1.5">
                  <span className="text-[10px] font-mono text-amber-400 uppercase font-bold">
                    Verified Citations &amp; Literature:
                  </span>
                  <ul className="list-disc list-inside space-y-1 text-space-400 text-[11px]">
                    {selectedArticle.citations.map((cite, i) => (
                      <li key={i}>{cite}</li>
                    ))}
                  </ul>
                </div>
              </>
            ) : (
              <div className="text-space-400">Select an article to view reference details.</div>
            )}
          </div>
        </div>
      </section>

      {/* ── 3. Local Phi-3 Clinical AI Assistant Console ───────────────────── */}
      <section
        aria-label="Local Phi-3 Clinical AI Console"
        className="p-6 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-4"
      >
        <div className="flex items-center justify-between border-b border-space-800 pb-3">
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-emerald-400" />
            <div>
              <h2 className="text-sm font-bold text-space-100 uppercase tracking-wider">
                Phi-3 Air-Gapped Clinical Decision Support Console
              </h2>
              <p className="text-xs text-space-400">
                Local Onboard Knowledge Base Inference • Explicit Refusal Beyond Verified Clinical Scope
              </p>
            </div>
          </div>
          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            LOCAL INFERENCE
          </span>
        </div>

        {/* Quick Prompt Presets */}
        <div className="flex flex-wrap gap-2 pt-1">
          <span className="text-[11px] text-space-400 font-mono self-center">
            Presets:
          </span>
          {[
            "Headache protocol for cabin CO2 above 4.0 mmHg",
            "Triage SANS visual acuity degradation & blur",
            "Microgravity hemorrhage direct pressure protocol",
            "Acute space motion sickness promethazine dosage",
          ].map((preset, idx) => (
            <button
              key={idx}
              onClick={() => handleSendChat(preset)}
              disabled={chatLoading}
              className="px-2.5 py-1 rounded bg-space-850 hover:bg-space-800 text-space-300 hover:text-space-100 border border-space-800 text-[11px] font-mono transition"
            >
              {preset}
            </button>
          ))}
        </div>

        {/* Chat Message Window */}
        <div className="h-64 overflow-y-auto p-4 rounded-xl bg-space-950 border border-space-800 space-y-3 font-mono text-xs">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {msg.role === "assistant" && (
                <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`p-3 rounded-xl max-w-xl space-y-1.5 leading-relaxed ${
                  msg.role === "user"
                    ? "bg-cyan-600 text-white"
                    : msg.refusal
                    ? "bg-red-950/40 border border-red-500/40 text-red-200"
                    : "bg-space-850 border border-space-800 text-space-200"
                }`}
              >
                <div className="text-[10px] opacity-60 flex items-center justify-between">
                  <span>{msg.role === "user" ? "Astronaut / CMO" : "MAITRI Clinical AI"}</span>
                  <span>{msg.timestamp}</span>
                </div>
                <p className="whitespace-pre-wrap">{msg.text}</p>
                {msg.citations && (
                  <div className="text-[10px] text-emerald-400 pt-1 border-t border-space-800">
                    Citations: {msg.citations.join(" | ")}
                  </div>
                )}
              </div>

              {msg.role === "user" && (
                <div className="w-7 h-7 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendChat();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            placeholder="Ask Clinical AI about spacecraft symptoms, protocols, or countermeasures..."
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            disabled={chatLoading}
            className="flex-1 px-4 py-2 rounded-lg bg-space-850 border border-space-700 text-xs text-space-100 placeholder-space-500 focus:outline-none focus:border-cyan-500"
          />
          <button
            type="submit"
            disabled={chatLoading || !chatInput.trim()}
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs font-bold flex items-center gap-1.5 transition disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            <span>{chatLoading ? "Querying..." : "Send"}</span>
          </button>
        </form>
      </section>
    </div>
  );
};
