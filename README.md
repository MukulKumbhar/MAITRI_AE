<div align="center">

```
███╗   ███╗ █████╗ ██╗████████╗██████╗ ██╗    ██████╗    ██████╗
████╗ ████║██╔══██╗██║╚══██╔══╝██╔══██╗██║   ╚════██╗  ██╔═████╗
██╔████╔██║███████║██║   ██║   ██████╔╝██║    █████╔╝  ██║██╔██║
██║╚██╔╝██║██╔══██║██║   ██║   ██╔══██╗██║   ██╔═══╝   ████╔╝██║
██║ ╚═╝ ██║██║  ██║██║   ██║   ██║  ██║██║   ███████╗  ╚██████╔╝
╚═╝     ╚═╝╚═╝  ╚═╝╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝   ╚══════╝   ╚═════╝
```

# MAITRI 2.0 — Multimodal Astronaut Intelligence for Total Real-time Integration

**The first fully offline, air-gapped, multimodal AI health cockpit designed for long-duration spaceflight.**

[![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=for-the-badge&logo=typescript)](https://typescriptlang.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/Tests-254%20Passed-brightgreen?style=for-the-badge&logo=pytest)](tests/)
[![Offline](https://img.shields.io/badge/Network-100%25%20Offline-orange?style=for-the-badge)](docs/)
[![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)](LICENSE)

> ⚠️ **CLINICAL DECISION SUPPORT ONLY** — MAITRI is not a certified medical device.  
> All thresholds carry cited sources or are marked **"configurable demo default"**.  
> Always defer to flight surgeons and mission medical protocols.

</div>

---

## 📖 Table of Contents

1. [What Is MAITRI?](#-what-is-maitri)
2. [Why It Matters](#-why-it-matters)
3. [System Architecture](#-system-architecture)
4. [5-View Operational Cockpit](#-5-view-operational-cockpit)
5. [Internal Workflows — Step-by-Step](#-internal-workflows--step-by-step)
   - [Voice Command Pipeline](#1-voice-command-pipeline-maitri-set-heart-rate-to-85)
   - [Live Camera + Emotion Pipeline](#2-live-camera--emotion-ai-pipeline)
   - [Tab Navigation (keyboard or voice)](#3-tab-navigation--keyboard-or-voice)
   - [HRV Calculation Pipeline](#4-hrv-calculation-pipeline)
   - [PVT-B Cognitive Test Flow](#5-pvt-b-psychomotor-vigilance-test-flow)
   - [IEC Alarm Escalation Path](#6-iec-60601-1-8-alarm-lifecycle)
   - [SHA-256 Hash Chain Audit](#7-sha-256-hash-chain-audit-log)
   - [CO₂ Hazard Model Calculation](#8-co-hazard-model--law-2014)
   - [PHQ-9 Item 9 Safety Trigger](#9-phq-9-screener--safety-gate)
   - [Sensor Adapter Modes](#10-sensor-adapter-modes)
6. [Module Reference](#-module-reference-m1--m6--new)
7. [Mathematical Formulations](#-mathematical-formulations)
8. [AI Models Bundled](#-ai-models-bundled-fully-offline)
9. [Voice Command Reference](#-voice-command-reference)
10. [Design System](#-design-system)
11. [Installation & Quickstart](#-installation--quickstart)
12. [Running Fully Offline](#-running-fully-offline-proof)
13. [Test Matrix](#-test-matrix--254-tests)
14. [Architecture Diagram](#-full-architecture-diagram)
15. [Known Limitations](#-known-limitations--disclaimer)
16. [Contributing](#-contributing)

---

## 🛰️ What Is MAITRI?

**MAITRI** (Multimodal Astronaut Intelligence for Total Real-time Integration) is a **100% offline, air-gapped** crew health monitoring cockpit purpose-built for long-duration space missions — ISS, lunar Gateway, and Mars transit.

It runs **entirely on a laptop with no internet connection**, no cloud APIs, and no CDN dependencies. Every AI model, font, and asset is bundled locally. It uses a crewmember's **webcam, microphone, and manual input** to monitor:

| Health Domain | What MAITRI Monitors |
|:---|:---|
| 🫀 **Cardiovascular** | Heart rate, SpO₂, HRV (rMSSD, SDNN, Baevsky SI), respiratory rate |
| 🧠 **Neurocognitive** | Psychomotor Vigilance Test (PVT-B), reaction time, lapses, false starts |
| 😴 **Circadian / Sleep** | Sleep debt, cosinor phase angle, ISS 90-min orbital cycle alignment |
| 😶 **Emotional / Behavioral** | 7-class facial emotion (EfficientNet-B2), voice affect, isolation trends |
| 👁️ **Oculomotor** | Eye Aspect Ratio (EAR), blink detection, SANS-related ocular metrics |
| 🌬️ **Cabin ECLSS** | CO₂ (ppm), O₂ (%), temperature, humidity, noise — with Law 2014 hazard scoring |
| 🧪 **Psychometric** | PHQ-9 depression, GAD-7 anxiety, PSS-4 stress — with Item 9 safety gate |
| 💊 **Medical KB** | Offline emergency checklists (Ammonia leak, Trauma, Ocular), cited references |
| 🔔 **Alarm Management** | IEC 60601-1-8 tiered alarms (HIGH/MEDIUM/LOW/INFO), mute, acknowledge, escalation |
| 🔐 **Data Integrity** | SHA-256 hash-chained audit log, encrypted SQLite, tamper detection |

---

## 🚀 Why It Matters

During a **Mars transit (7–9 months each way)**, communication delays of **up to 24 minutes one-way** make real-time ground support impossible. The crew must autonomously manage their own health. MAITRI is designed around this reality:

| NASA HRP Risk | MAITRI Response |
|:---|:---|
| **SANS** (Spaceflight-Associated Neuro-ocular Syndrome) | Oculomotor EAR tracking, blink baseline deviation |
| **Behavioral Health & Performance** | Emotion AI, PHQ-9/GAD-7/PSS-4, isolation trend, PVT-B |
| **Sleep/Circadian Misalignment** | Sleep debt tracker, cosinor rhythm model, ISS 90-min cycle |
| **CO₂ Toxicity** | Law 2014 pCO₂ impairment model (headache onset at 0.5% CO₂) |
| **Cardiovascular Deconditioning** | HRV rMSSD/SDNN decline detection, Baevsky Stress Index |
| **Cognitive Fatigue** | PVT-B lapses >355ms per Basner & Dinges 2011 |
| **Communication Blackout** | Full offline operation, DTN-ready report export |

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        BROWSER (React + TypeScript)                  │
│                                                                      │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │Overview │ │  Cardio  │ │  Neuro   │ │  Cabin   │ │  Medical  │  │
│  │  Tab 1  │ │  Tab 2   │ │  Tab 3   │ │  Tab 4   │ │  Tab 5   │  │
│  └────┬────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘  │
│       │           │             │             │              │        │
│  ┌────▼───────────▼─────────────▼─────────────▼──────────────▼────┐ │
│  │                     App.tsx — Global Shell                      │ │
│  │  Header ▸ WatchdogBanner ▸ IEC Alarm Banner ▸ BIST Modal      │ │
│  └──────────────┬──────────────────────────────────────────────────┘ │
│                 │                                                     │
│  ┌──────────────▼──────────────────────────────────────────────────┐ │
│  │                  Services Layer                                  │ │
│  │  visionPipeline.ts  audioSocket.ts  telemetrySocket.ts  api.ts │ │
│  └──────┬────────────────────┬─────────────────────────────────────┘ │
│         │ WebSocket /ws/video │ WebSocket /ws/audio                  │
│         │ WebSocket /ws/telem │ REST /api/*                          │
└─────────┼────────────────────┼──────────────────────────────────────┘
          │                    │
┌─────────▼────────────────────▼──────────────────────────────────────┐
│                     FastAPI Backend (Python 3.11)                    │
│                                                                      │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │  vision_service │  │  voice_service   │  │ telemetry_service  │  │
│  │  EfficientNet   │  │  Vosk ASR (Kaldi)│  │ Sensor Adapter     │  │
│  │  ONNX 7-class   │  │  Intent Parser   │  │ Live/Manual/Replay  │  │
│  │  emotion model  │  │  Piper TTS       │  │                    │  │
│  └────────┬────────┘  └────────┬─────────┘  └─────────┬──────────┘  │
│           │                    │                        │             │
│  ┌────────▼────────────────────▼────────────────────────▼──────────┐ │
│  │                      modules/ — Clinical Core                    │ │
│  │  face_module    eye_module    vitals_module    fusion_module     │ │
│  │  pvt_module     circadian_module  screener_module               │ │
│  │  medical_kb     alert_module  database_module                   │ │
│  └──────────────────────────────────┬───────────────────────────────┘ │
│                                     │                                  │
│  ┌──────────────────────────────────▼───────────────────────────────┐ │
│  │               state.py — Global Clinical State                   │ │
│  │  PersonalBaseline • IECAlarmManager • SensorAdapter              │ │
│  │  TelemetryRecord  • PhaseState • ActiveScreener                 │ │
│  └──────────────────────────────────┬───────────────────────────────┘ │
│                                     │                                  │
│  ┌──────────────────────────────────▼───────────────────────────────┐ │
│  │               SQLite — maitri_clinical.db                        │ │
│  │  telemetry_log • alarm_events • screener_results                 │ │
│  │  audit_chain (SHA-256 hash-chained tamper-evident log)           │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🖥️ 5-View Operational Cockpit

The cockpit uses **keyboard shortcuts `1`–`5`** (or voice commands "Maitri, switch to cardio") to navigate instantly between five mission-critical views:

---

### Tab 1 — Overview (Mission Status Radar)
**Hotkey `1`** | Voice: `"Maitri, overview"`

The at-a-glance **command center**. Shows a composite health radar across all domains simultaneously.

| Widget | Data Source | Purpose |
|:---|:---|:---|
| Health Radar (Spider) | fusion_module.py adaptive EMA | 6-axis composite: Cardio, Neuro, Affect, Sleep, Cabin, Stress |
| Active Alarm Banner | IECAlarmManager | HIGH/MEDIUM/LOW priority with IEC color coding |
| Live Vitals Strip | telemetry_service.py | HR, SpO₂, RR, stress score — real-time 1 Hz |
| Emotion Chips | face_module.py ONNX | 7-class dominant emotion with confidence % |
| Watchdog Status | alert_module.py | Last check-in time, next deadline countdown |
| Phase State Indicator | phase2_core.py | Current mission phase, alert readiness level |

---

### Tab 2 — Cardio (Heart Rate Variability Panel)
**Hotkey `2`** | Voice: `"Maitri, cardio"`

Deep cardiovascular analysis with **HRV waveforms and autonomic health scoring**.

| Widget | Data Source | Clinical Standard |
|:---|:---|:---|
| RR Interval Chart | vitals_module.py + manual entry | Synthetic RR model for demo |
| HRV rMSSD | ESC/NASPE Task Force 1996 | Normal: >27ms (parasympathetic reserve) |
| HRV SDNN | ESC/NASPE Task Force 1996 | Normal: 50–100ms (global autonomic) |
| Baevsky Stress Index | Baevsky R.M. et al. 1984, 2001 | SI = AMo / (2 × Mo × MxDMn); normal <150 |
| HRV Strain Score | vitals_module.py | Composite 0–1: elevated if rMSSD<25 or SI>300 |
| Respiratory Rate | vitals_module.py | Guyton coupling: RR ≈ HR/4, normal 12–20 bpm |
| SpO₂ Trend | Sensor adapter | NASA-STD-3001 Vol.1 §4.5.3 threshold: <95% alert |
| Manual Input Sliders | CardioTab.tsx | Wired to WebSocket telemetrySocket.sendVitalsUpdate() |

---

### Tab 3 — Neuro (Cognitive & Circadian)
**Hotkey `3`** | Voice: `"Maitri, neuro"`

Cognitive performance monitoring via **PVT-B** (the gold standard for fatigue assessment in spaceflight) and **circadian rhythm tracking**.

| Widget | Data Source | Clinical Standard |
|:---|:---|:---|
| PVT-B Test Widget | pvt_module.py | Basner & Dinges 2011 (Neurology) — 3 min, random ISI 2–10s |
| Reaction Time Distribution | pvt_module.py | Lapse = RT > 355ms; False Start = RT < 100ms |
| PVT-B Score Summary | pvt_module.py | Mean RT, lapse count, fastest 10%, slowest 10% |
| Circadian Phase Clock | circadian_module.py | Cosinor model — CBT minimum estimated nadir |
| Sleep Debt Gauge | circadian_module.py | Hours short of 8-hr target over 7 days |
| ISS Orbital Alignment | circadian_module.py | 90-min orbital cycle vs. sleep schedule |
| Isolation Trend Indicator | screener_module.py | Third-Quarter Effect: mood slump in mission midpoint |

---

### Tab 4 — Cabin (ECLSS Environment)
**Hotkey `4`** | Voice: `"Maitri, cabin"`

Environmental Life Support System monitoring with **direct hazard model integration**.

| Widget | Data Source | Clinical Standard |
|:---|:---|:---|
| CO₂ pCO₂ Gauge | telemetry_service.py + Law 2014 | Law et al. 2014 J.Appl.Physiol — headache onset 0.5% |
| CO₂ Hazard Score | Law 2014 impairment model | Cognitive impairment 1.0% CO₂; incapacitation 3% |
| O₂ % Chart | Sensor adapter | NASA-STD-3001: 19.5–23.1% (ISS normal 20.9%) |
| Cabin Temperature | Manual / simulated | Comfort zone 18–27°C per NASA-STD-3001 |
| Humidity | Manual / simulated | 25–75% RH — below 25% dries mucous membranes |
| Noise Level | Manual / simulated | NASA-STD-3001: <72 dBA continuous, 60 dBA sleep areas |
| Alert Thresholds | IECAlarmManager | Color-coded per IEC 60601-1-8: red ▲ yellow ■ cyan ◆ |

---

### Tab 5 — Medical (AI Assistant & Checklists)
**Hotkey `5`** | Voice: `"Maitri, medical"`

Offline clinical decision support — **no guesses, no hallucinations, citations required**.

| Widget | Data Source | Design Rule |
|:---|:---|:---|
| Phi-3 Mini Chat | phi3_mini_q4.gguf (llama.cpp) | Local Phi-3 Mini 4-bit quantized — strictly offline |
| Medical KB Citations | medical_kb.py curated DB | Every answer references a source or is refused |
| Emergency Checklist: Ammonia | medical_kb.py | NASA-JSC JSC-24570 Ammonia Leak Response |
| Emergency Checklist: Trauma | medical_kb.py | Tactical Combat Casualty Care (TCCC) adapted |
| Emergency Checklist: Ocular | medical_kb.py | NASA spaceflight ocular health SOP |
| PHQ-9 Screener | screener_module.py | Kroenke & Spitzer 2001 — Item 9 triggers safety gate |
| GAD-7 Screener | screener_module.py | Spitzer et al. 2006 — generalized anxiety |
| PSS-4 Screener | screener_module.py | Cohen et al. 1983 — perceived stress scale |
| Screener History | SQLite screener_results | Trend over mission duration |

---

## 🔄 Internal Workflows — Step-by-Step

Understanding what MAITRI does *inside* when you interact with it:

---

### 1. Voice Command Pipeline: `"Maitri, set heart rate to 85"`

```
USER speaks into microphone
        │
        ▼
Browser AudioWorklet (frontend/src/services/audioSocket.ts)
  • Captures PCM at 16 kHz, 16-bit mono
  • Sends 1,600-sample (100ms) chunks via WebSocket /ws/audio
        │
        ▼
backend/services/voice_service.py — _stream_to_vosk()
  • VAD (Voice Activity Detection): computes RMS of chunk
  • If RMS > 0.03 threshold → audio is speech, pass to Vosk
  • If RMS < 0.03 for 8 consecutive chunks → silence detected
        │
        ▼
Vosk Kaldi ASR Engine (models/vosk/ — fully offline)
  • Processes incoming PCM stream
  • Returns partial transcripts in real-time, final on silence
  • Raw transcript: "that her three to eighty five"
        │
        ▼
backend/services/intent_parser.py — _apply_phonetic_corrections()
  PHONETIC_REPLACEMENTS applied (regex substitution):
  • "her three" → "heart rate"   (acoustic model confusion)
  • "that her"  → "set heart"    (Kaldi confusion of consonants)
  Result: "set heart rate to eighty five"
        │
        ▼
intent_parser.py — parse_intent()
  • WAKE WORD check: "maitri" / "matrix" / "mighty" etc.
  • Levenshtein fuzzy match against all INTENT_PATTERNS
  • Intent: "set_heart_rate" | Confidence: 0.97
        │
        ▼
voice_service.py — SafetyConfirmationGate
  • Is this a CRITICAL_SAFETY_INTENT? → No (set_heart_rate is safe)
  • Skip confirmation gate
        │
        ▼
voice_service.py — _execute_intent_action("set_heart_rate", entity=85.0)
  • state.heart_rate = 85.0
  • state.last_telemetry_updated = now()
  • Triggers IEC alarm re-evaluation against thresholds
        │
        ▼
Piper TTS — en_US-lessac-medium.onnx (models/piper_voice/)
  • Synthesizes: "Heart rate set to 85 beats per minute."
  • Outputs WAV bytes → base64 encoded
        │
        ▼
WebSocket response to browser
  • JSON: { "type": "tts_audio", "data": "<base64_wav>", "intent": "set_heart_rate" }
        │
        ▼
Browser audioSocket.ts
  • Decodes base64 → AudioBuffer → AudioContext.decodeAudioData()
  • Plays immediately through speakers
        │
        ▼
VoiceDebugDrawer (UI)
  • Displays: transcript, phonetic-corrected form, intent, entity, confidence
  • User sees confirmation visually + hears it spoken
```

---

### 2. Live Camera + Emotion AI Pipeline

```
USER clicks "Start Live Camera" button
        │
        ▼
Browser: navigator.mediaDevices.getUserMedia({ video: true })
  • Requests webcam access (browser permission dialog)
  • Returns MediaStream with video track
        │
        ▼
frontend/src/services/visionPipeline.ts
  • Creates HTMLVideoElement, feeds MediaStream
  • Loads MediaPipe FaceLandmarker WASM (models/face_landmarker.task)
  • Runs at 60 fps via requestAnimationFrame loop
        │
        ▼
MediaPipe FaceLandmarker (WASM — zero network calls)
  • Detects 478 3D face landmarks per frame
  • Outputs 52 FACS (Facial Action Coding System) blendshapes
  • Example: jawOpen=0.03, eyeBlinkLeft=0.72, browInnerUp=0.45
        │
        ▼
visionPipeline.ts — _extractEARMetrics()
  Eye Aspect Ratio:
  EAR = (‖p2-p6‖ + ‖p3-p5‖) / (2 × ‖p1-p4‖)
  • p1–p6 = 6 eyelid landmarks from MediaPipe mesh
  • EAR < 0.21 for >3 frames → blink detected
  • EAR sustained < 0.21 → drowsiness flag
        │
        ▼
visionPipeline.ts — Canvas snapshot
  • Crops face bounding box from video frame
  • Encodes as JPEG at 6 fps (not 60 fps — saves bandwidth)
  • Sends via WebSocket /ws/video-crop as binary blob
        │
        ▼
backend/services/vision_service.py — _process_frame()
  • Receives JPEG bytes
  • Decodes → numpy array (OpenCV)
  • Resizes to 260×260 (EfficientNet-B2 input size)
  • Normalizes pixel values to [0.0, 1.0]
        │
        ▼
EfficientNet-B2 ONNX (models/enet_b2_7.onnx)
  • Input: [1, 3, 260, 260] float32 tensor
  • Output: [1, 7] logits → softmax → probability distribution
  • 7 emotion classes: angry, disgust, fear, happy, neutral, sad, surprise
  • Example: neutral=0.52, sad=0.31, fear=0.12, ...
        │
        ▼
vision_service.py → state.py update
  • state.emotion_probs = {"neutral": 0.52, "sad": 0.31, ...}
  • state.dominant_emotion = "neutral"
  • state.ear = 0.28 (from EAR calculation)
        │
        ▼
modules/fusion_module.py — update_fusion()
  Adaptive EMA fusion:
  score_t = α × new_score + (1-α) × score_{t-1}
  • Emotion weight: 0.35 (of composite)
  • Vitals weight: 0.30
  • Cognitive weight: 0.20
  • Environment weight: 0.15
        │
        ▼
modules/fusion_module.py — Welford CUSUM baseline check
  • CUSUM: S_t = max(0, S_{t-1} + (x_t - μ₀) - K)
  • If S_t > threshold (4.0 sigma): Personal Baseline Deviation Alert
        │
        ▼
Telemetry broadcast via WebSocket /ws/telemetry
  • Full TelemetryRecord sent to all connected browser clients
  • Includes emotion probs, EAR, fusion scores, alarm states
        │
        ▼
Browser re-renders relevant tab widgets
  • Overview Tab: radar chart updates
  • Emotion chips in Header update
  • IEC alarm banner may appear if threshold crossed
```

---

### 3. Tab Navigation — Keyboard or Voice

```
USER presses key "2" (or says "Maitri, cardio")
        │
        ├── Keyboard path:
        │     App.tsx — useEffect keydown handler
        │     • Checks: not inside <input>/<textarea>/contentEditable
        │     • Maps key → tab: {"1":"overview", "2":"cardio", "3":"neuro", "4":"cabin", "5":"medical"}
        │     • Calls: setActiveTab("cardio")
        │
        └── Voice path:
              voice_service.py dispatches intent "navigate_clinical"
              → voice_service calls window broadcast { type: "intent_action", tab: "cardio" }
              → audioSocket.ts receives message
              → triggers tab change via React state
        │
        ▼
App.tsx — activeTab state updates → React re-renders
  • Old tab component unmounts: cleanup useEffect returns called
    (PVT timers cancelled, RAF loops stopped, WebSocket listeners removed)
  • New tab component mounts: useEffect setup called
    (new API fetch, new WebSocket subscription, chart init)
        │
        ▼
CardioTab.tsx — onMount useEffect
  • GET /api/clinical/hrv → loads historical HRV chart data
  • WebSocket /ws/telemetry → subscribes for live RR interval stream
  • Renders HRV chart (Recharts), sliders wired to telemetrySocket.sendVitalsUpdate()
```

---

### 4. HRV Calculation Pipeline

```
INPUT: Array of RR intervals (ms between heartbeats)
  e.g., [820, 835, 798, 812, 844, 801, 819, ...]  (N=100 values, 5 minutes)

modules/vitals_module.py — calculate_hrv_metrics()
        │
        ▼
Step 1: SDNN (Standard Deviation of NN intervals)
  μ = Σ(RR_i) / N
  SDNN = √[ Σ(RR_i - μ)² / (N-1) ]
  Normal range: 50–100 ms
  Source: ESC/NASPE Task Force (Circulation 1996;93:1043–65)
        │
        ▼
Step 2: rMSSD (Root Mean Square of Successive Differences)
  diffs = [RR_{i+1} - RR_i  for i in 0..N-2]
  rMSSD = √[ Σ(diffs_i²) / (N-1) ]
  Normal: >27 ms (parasympathetic tone indicator)
  Space relevance: drops with cardiovascular deconditioning
        │
        ▼
Step 3: Baevsky Stress Index
  Mode (Mo)   = most frequent RR value in histogram (bin width 50ms)
  AMo         = amplitude of mode (% of RR values in mode bin)
  MxDMn       = max(RR) - min(RR)  (variation range)
  SI = AMo / (2 × Mo × MxDMn)
  Normal: <150;  Elevated stress: >300
  Source: Baevsky R.M. et al. Human Physiology 27(6):735–748, 2001
        │
        ▼
Step 4: HRV Strain Score (composite)
  strain = 0.0
  if rMSSD < 25ms:    strain += 0.4
  elif rMSSD < 35ms:  strain += 0.2
  if SI > 300:        strain += 0.4
  elif SI > 200:      strain += 0.2
  if SDNN < 30ms:     strain += 0.2
  strain = clamp(strain, 0.0, 1.0)
        │
        ▼
Stored in state.py → broadcast in TelemetryRecord → displayed in CardioTab
```

---

### 5. PVT-B Psychomotor Vigilance Test Flow

```
USER says "Maitri, start PVT test" (or clicks button in Neuro tab)
        │
        ▼
modules/pvt_module.py — PVTSession.start()
  • Records session start timestamp
  • Sets test duration: 180 seconds (3 minutes per Basner & Dinges 2011)
        │
        ▼
Stimulus Loop (NeuroTab.tsx frontend):
  REPEAT until 180s elapsed or user stops:
        │
        ▼
  Step 1: Wait random Inter-Stimulus Interval (ISI)
    ISI = random uniform [2000, 10000] ms  (2–10 seconds)
    Basner & Dinges 2011 Neurology: 2–10s range maximizes sensitivity
        │
        ▼
  Step 2: Show GO stimulus (cyan circle appears on screen)
    Frontend: setShowStimulus(true), startTime = performance.now()
        │
        ▼
  Step 3: Wait for SPACEBAR press
    If RT < 100ms: FALSE START (anticipation, not perception)
    If RT > 355ms: LAPSE (attentional failure, Basner 2011 cutoff)
    If 100ms ≤ RT ≤ 355ms: VALID response
        │
        ▼
  Step 4: Send trial to backend
    POST /api/clinical/pvt/trial { reaction_time_ms: 287 }
    pvt_module.py stores trial, updates running stats
        │
        ▼
After 180s: pvt_module.py — calculate_results()
  • mean_rt: mean of all valid responses (ms)
  • lapse_count: trials > 355ms
  • false_start_count: trials < 100ms  
  • fastest_10pct: mean of fastest 10% (ideal performance)
  • slowest_10pct: mean of slowest 10% (fatigue marker)
  • pvt_score: normalized 0–1 (1.0 = optimal alertness)
        │
        ▼
Piper TTS announces result:
  "PVT test complete. Mean reaction time: 287 milliseconds.
   0 lapses detected. Alertness level: good."
        │
        ▼
Stored in SQLite screener_results table with SHA-256 hash chain seal
Displayed in Neuro tab as score + trend line across mission
```

---

### 6. IEC 60601-1-8 Alarm Lifecycle

```
TRIGGER EVENT: SpO₂ drops to 93% (below 95% threshold)
        │
        ▼
backend/state.py — IECAlarmManager.raise_alarm()
  • Deduplication check: same alarm type active within 30s? → skip (prevent spam)
  • Priority assignment:
    HIGH    (▲ red)    = immediate life threat (SpO₂<90, HR<40/>160, CO₂>1%)
    MEDIUM  (■ yellow) = urgent attention needed (SpO₂<95, HR<50/>130)
    LOW     (◆ cyan)   = advisory notice
    INFO    (● blue)   = informational
  • SpO₂ 93% → MEDIUM priority
        │
        ▼
IECAlarmManager — escalation timer started
  • Timer: 3 minutes
  • If alarm not acknowledged within 3 minutes → escalate to HIGH
        │
        ▼
Alarm broadcast via WebSocket /ws/telemetry to all clients
  Frontend: WatchdogBanner.tsx + Overview alarm strip updates
  IEC color: amber background, ■ square icon (MEDIUM)
  Text: "⚠ MEDIUM: SpO₂ 93% — below 95% advisory threshold"
        │
        ▼
USER acknowledges: "Maitri, acknowledge" (voice) or clicks ✓ button
        │
        ▼
voice_service.py dispatches intent "watchdog_ack"
  → IECAlarmManager.acknowledge_alarm(alarm_id)
  → alarm moves to "acknowledged" state (still visible but dimmed)
  → Piper TTS: "Alarm acknowledged. Monitoring continues."
        │
        ▼
If SpO₂ recovers to > 95%:
  IECAlarmManager.clear_alarm(alarm_id)
  → Alarm removed from active list
  → Logged to audit_chain in SQLite with SHA-256 seal
        │
        ▼
Mute path: User clicks 🔇 (120-second mute):
  IECAlarmManager.mute_alarm(alarm_id, duration=120)
  → Alarm silences for 2 minutes, then auto-unmutes
  → HIGH priority alarms cannot be permanently dismissed (IEC requirement)
```

---

### 7. SHA-256 Hash-Chain Audit Log

```
Every database write goes through audit_chain sealing:

modules/database_module.py — _seal_audit_entry()

ENTRY N:
  canonical_string = JSON.dumps({
    "timestamp": "2026-11-14T10:23:45Z",
    "type": "telemetry_log",
    "heart_rate": 72,
    "spo2": 97.3,
    "emotion": "neutral",
    "alarm_triggered": false,
    "prev_hash": "7a3f9b2d..."   ← hash of ENTRY N-1
  }, sort_keys=True)
        │
        ▼
  entry_hash = SHA-256(canonical_string.encode('utf-8')).hexdigest()
  → "9c4e8a1b..."
        │
        ▼
  INSERT INTO audit_chain (entry_hash, prev_hash, payload, timestamp)
        │
        ▼
Tamper Detection: database_module.verify_audit_chain()
  • Reads all entries in order
  • For each entry N: recomputes SHA-256(canonical) → compare with stored hash
  • If MISMATCH: "⚠ TAMPER DETECTED at entry N — chain broken"
  • Reports: verified_count, tampered_count, chain_valid: true/false
        │
        ▼
BIST Modal in UI (Shift+B or "Maitri, run diagnostics"):
  • Displays: total entries, last 5 hashes, chain_valid status
  • User can inspect entire hash chain for forensic verification
  • Useful for flight surgeon review before DTN report export
```

---

### 8. CO₂ Hazard Model — Law 2014

```
INPUT: cabin_co2_ppm = 5500 ppm (0.55%)

modules/vitals_module.py / backend/state.py — law_2014_co2_hazard()

Step 1: Convert to partial pressure fraction
  co2_fraction = co2_ppm / 1,000,000  =  0.0055

Step 2: Apply Law 2014 hazard thresholds
  Source: Law J. et al. (2014) J.Appl.Physiol 116(10):1346-1357
  "Relationship of CO₂ Levels to Crewmember Health"

  THRESHOLDS:
  < 0.5%  (5000 ppm):   Normal — no impairment
  0.5–1.0% (5000–10000): Headache onset, mild cognitive impairment
  1.0–3.0%:              Significant cognitive impairment, dyspnea
  > 3.0%:               Incapacitation risk — emergency action required

Step 3: Cognitive impairment score (Law 2014 regression)
  impairment_score = max(0, (co2_ppm - 5000) / 5000)
  → 5500 ppm: impairment_score = 0.10 (10% — early onset)

Step 4: Output
  {
    "co2_ppm": 5500,
    "co2_fraction": 0.0055,
    "hazard_level": "MEDIUM",
    "impairment_score": 0.10,
    "symptom_prediction": "mild_headache_possible",
    "action": "increase_scrubber_capacity"
  }

Step 5: If hazard_level == HIGH or CRITICAL:
  → IECAlarmManager.raise_alarm("CO2_HAZARD", priority=HIGH)
  → Piper TTS: "Warning: CO2 at 5500 ppm. Headache risk. Check scrubbers."
  → Emergency Checklist trigger available in Medical tab
```

---

### 9. PHQ-9 Screener — Safety Gate

```
USER says "Maitri, start depression check"
        │
        ▼
backend/api/clinical.py — /api/clinical/screener/start
  screener_module.py — PHQ9Session.begin()
  • Loads 9 PHQ-9 questions
  • Question 1: "Little interest or pleasure in doing things"
        │
        ▼
Voice / UI walks through questions 1–9
  Each answer: 0=Not at all, 1=Several days, 2=More than half, 3=Nearly every day
        │
        ▼
ITEM 9 SPECIAL SAFETY CHECK (every screener):
  Question 9: "Thoughts that you would be better off dead,
               or of hurting yourself in some way"
        │
        ▼
  If Item 9 ≥ 1 (any positive response):
    screener_module.py — PHQ9SafetyGate.trigger()
    1. IMMEDIATELY escalate to HIGH alarm: "SAFETY CONCERN — Item 9 Positive"
    2. Piper TTS: "I noticed your response to question 9.
                   Please contact flight surgeon immediately.
                   I am here with you."
    3. Display emergency contact protocol in Medical tab
    4. Lock PHQ-9 results with restricted access flag
    5. Flag for DTN report export to flight surgeon
        │
        ▼
Scoring (all 9 questions):
  Total = Σ(item scores, 0–27)
  0–4:   Minimal depression
  5–9:   Mild depression
  10–14: Moderate depression
  15–19: Moderately severe depression
  20–27: Severe depression — PRIORITY flag for flight surgeon
        │
        ▼
Stored in SQLite screener_results with SHA-256 chain
Trend visualization in Medical tab across mission duration
```

---

### 10. Sensor Adapter Modes

MAITRI operates in three modes because real spacecraft sensors don't exist on a laptop:

```
backend/state.py — SensorAdapter

MODE 1: LIVE (default if camera/mic available)
  • Video: browser webcam → MediaPipe → EfficientNet-B2
  • Audio: browser microphone → Vosk ASR
  • Vitals: Manual slider entry (no hardware sensors)
  • ECLSS: Manual entry (no actual air sensors)

MODE 2: MANUAL
  • All values set via UI sliders or voice commands
  • Example: "Maitri, set heart rate to 72"
  • Useful: testing, demo, training scenarios

MODE 3: REPLAY / SIMULATION
  • Loads pre-recorded scenario from JSON file
  • 4 built-in scenarios:
    ┌─────────────────────────────────────────────────────┐
    │ Scenario A: "Nominal Operations"                    │
    │   HR 65-72, SpO₂ 97-98%, emotion neutral/happy    │
    │   Sleep debt low, CO₂ normal, all green            │
    │                                                     │
    │ Scenario B: "Sleep Deprivation - Day 3"            │
    │   HR 78-85, elevated cortisol proxy               │
    │   Sleep debt 6h, PVT lapses 4+, mood sad           │
    │                                                     │
    │ Scenario C: "CO₂ Scrubber Degradation"            │
    │   CO₂ rising: 2000→6000 ppm over 20 min          │
    │   Law 2014 hazard escalation triggered             │
    │   IEC HIGH alarm sequence demonstrated             │
    │                                                     │
    │ Scenario D: "Combined Stress Event"                │
    │   SpO₂ dip to 92%, HR 110, fear emotion 0.6       │
    │   Full alarm cascade + TTS announcement           │
    └─────────────────────────────────────────────────────┘
  • All simulated data visibly labeled "SIMULATED" in UI
  • No simulated value is ever presented as real medical data
```

---

## 📦 Module Reference (M1–M6 + New)

| Module | File | Lines | Purpose | Key Algorithm |
|:---|:---|:---:|:---|:---|
| **M1** Face Affect | `modules/face_module.py` | ~180 | Emotion recognition | EfficientNet-B2 ONNX 7-class |
| **M2** Eye Tracking | `modules/eye_module.py` | ~150 | Oculomotor / blink / EAR | MediaPipe landmarks, EAR formula |
| **M3** Vitals | `modules/vitals_module.py` | ~320 | HRV, respiratory, CO₂ | ESC/NASPE, Baevsky, Law 2014 |
| **M4** Fusion | `modules/fusion_module.py` | ~260 | Multi-modal health score | Adaptive EMA, Welford, CUSUM |
| **M5** Alert | `modules/alert_module.py` | ~200 | Alarm management | IEC 60601-1-8 priority, dedup |
| **M6** Database | `modules/database_module.py` | ~350 | Storage + audit | SHA-256 hash chain, SQLite |
| **NEW** PVT | `modules/pvt_module.py` | ~220 | Cognitive vigilance test | Basner & Dinges 2011 PVT-B |
| **NEW** Circadian | `modules/circadian_module.py` | ~180 | Sleep/rhythm tracking | Cosinor model, ISS orbital |
| **NEW** Screener | `modules/screener_module.py` | ~240 | PHQ-9/GAD-7/PSS-4 | Validated clinical instruments |
| **NEW** Medical KB | `modules/medical_kb.py` | ~300 | Offline medical reference | Curated citations + checklists |
| Voice | `backend/services/voice_service.py` | 520 | ASR + TTS + VAD | Vosk Kaldi, Piper, intent fuzzy |
| Vision | `backend/services/vision_service.py` | 202 | Frame processing | ONNX Runtime, OpenCV |
| Telemetry | `backend/services/telemetry_service.py` | 322 | Sensor adapter, broadcast | WebSocket fan-out, 3 modes |
| Psych | `backend/services/psych_service.py` | 216 | Phi-3 assistant | llama.cpp local LLM |
| BIST | `backend/services/bist_service.py` | ~180 | Built-in self test | Model integrity, DB verify |
| Intent Parser | `backend/services/intent_parser.py` | ~300 | NLU for voice | Fuzzy Levenshtein + phonetics |

---

## 📐 Mathematical Formulations

### HRV — Heart Rate Variability

$$\text{SDNN} = \sqrt{\frac{1}{N-1}\sum_{i=1}^{N}(RR_i - \bar{RR})^2}$$

$$\text{rMSSD} = \sqrt{\frac{1}{N-1}\sum_{i=1}^{N-1}(RR_{i+1} - RR_i)^2}$$

$$\text{Baevsky SI} = \frac{AMo}{2 \times Mo \times MxDMn}$$

Where: `Mo` = modal RR value, `AMo` = percentage of beats in modal bin, `MxDMn` = RR range

**Sources:** ESC/NASPE Task Force (1996); Baevsky R.M. et al. (2001)

---

### Eye Aspect Ratio (EAR) — SANS / Drowsiness

$$\text{EAR} = \frac{\|p_2-p_6\| + \|p_3-p_5\|}{2 \times \|p_1-p_4\|}$$

Where `p1–p6` are 6 eyelid landmarks from MediaPipe Face Mesh. Threshold: EAR < 0.21 → drowsiness.

---

### Personal Baseline — Welford Online Variance

$$\mu_n = \mu_{n-1} + \frac{x_n - \mu_{n-1}}{n}, \quad M_n = M_{n-1} + (x_n - \mu_{n-1})(x_n - \mu_n)$$

$$\sigma_n^2 = \frac{M_n}{n-1}$$

**CUSUM Change Detection:**

$$S_t = \max(0,\ S_{t-1} + (x_t - \mu_0) - K)$$

Where `K = 0.5σ` (slack), alert when `S_t > 4.0σ` (threshold). Evaluated at 1 Hz.

---

### Cosinor Circadian Model

$$f(t) = M + A \cdot \cos\!\left(\frac{2\pi t}{\tau} + \phi\right)$$

Where: `M` = MESOR (rhythm-adjusted mean), `A` = amplitude, `τ` = 24h period, `φ` = acrophase (peak time)

CBT Nadir ≈ acrophase - 12h (approximate core body temperature minimum)

---

### Law 2014 CO₂ Impairment

| CO₂ Level | ppm | Effect | MAITRI Alarm |
|:---|:---:|:---|:---:|
| Baseline | <1000 | No effect | None |
| Elevated | 1000–5000 | Mildly reduced cognitive performance | INFO |
| Hazardous | 5000–10000 | Headache onset (Law 2014 threshold) | MEDIUM |
| Dangerous | 10000–30000 | Significant impairment, dyspnea | HIGH |
| Critical | >30000 | Incapacitation risk | CRITICAL |

**Source:** Law J. et al. (2014) J.Applied Physiology 116(10):1346–1357

---

### SHA-256 Hash Chain

$$H_n = \text{SHA256}(\text{canonical}(\text{payload}_n, H_{n-1}))$$

Each entry includes previous hash → tamper-evidence. Chain verification: `O(N)` time.

---

## 🤖 AI Models Bundled (Fully Offline)

| Model | File | Size | Architecture | Task | Source |
|:---|:---|:---:|:---|:---|:---|
| **EfficientNet-B2** | `enet_b2_7.onnx` | ~28 MB | ONNX | 7-class facial emotion | FER+ / AffectNet pre-trained |
| **EfficientNet-B0** | `enet_b0_8_best_vgaf.onnx` | ~16 MB | ONNX | 8-class emotion (backup) | VGAF dataset |
| **Face Landmarker** | `face_landmarker.task` | ~6 MB | MediaPipe | 478 landmarks + 52 blendshapes | MediaPipe Tasks |
| **Vosk Kaldi** | `vosk/` (directory) | ~40 MB | Kaldi ASR | Offline speech recognition | vosk-model-en-us-0.22 |
| **Piper TTS** | `piper_voice/en_US-lessac-medium.onnx` | ~63 MB | VITS | Natural speech synthesis | Piper TTS (Rhasspy) |
| **Wav2Vec2 SER** | `wav2vec2_ser_q4.onnx` | ~95 MB | Transformer | Speech emotion recognition | Wav2Vec2 fine-tuned |
| **SER MLP** | `ser_mlp_mfcc.onnx` | ~1 MB | MLP | MFCC-based voice affect | Lightweight ensemble |
| **Phi-3 Mini** | `phi3_mini_q4.gguf` | ~2.4 GB | Transformer | Medical Q&A assistant | Microsoft Phi-3 Mini 4K |
| **Whisper Tiny** | `whisper_tiny_en/` | ~39 MB | Transformer | ASR fallback | OpenAI Whisper (tiny) |

**All models run on CPU** — no GPU required. Phi-3 Mini uses llama.cpp 4-bit quantization for <8 token/sec on modern laptop CPU.

---

## 🎙️ Voice Command Reference

All commands begin with the **wake word**: `"Maitri"` (or: Matri, Maytri, Matrix, Mighty)

### Navigation Commands

| Spoken Command | Intent | Tab | Talkback Response |
|:---|:---|:---:|:---|
| `"Maitri, overview"` | navigate_overview | 1 | "Switching to mission overview." |
| `"Maitri, show cockpit"` | navigate_live | 1 | "Opening live cockpit." |
| `"Maitri, cardio"` | navigate_cardio | 2 | "Opening cardiovascular panel." |
| `"Maitri, show HRV"` | navigate_cardio | 2 | "Opening cardiovascular panel." |
| `"Maitri, neuro"` | navigate_neuro | 3 | "Opening neurocognitive panel." |
| `"Maitri, cabin"` | navigate_cabin | 4 | "Opening cabin environment." |
| `"Maitri, medical"` | navigate_medical | 5 | "Opening medical assistant." |
| `"Maitri, show logs"` | navigate_logs | — | "Opening mission logs." |

### Vitals Commands

| Spoken Command | Intent | Action | Talkback Response |
|:---|:---|:---|:---|
| `"Maitri, set heart rate to 72"` | set_heart_rate | Updates HR = 72 | "Heart rate set to 72 beats per minute." |
| `"Maitri, set oxygen to 97"` | set_oxygen | Updates SpO₂ = 97 | "Blood oxygen set to 97 percent." |
| `"Maitri, read vitals"` | read_vitals | Reads all values | "Heart rate: 72. Oxygen: 97. Stress: low." |
| `"Maitri, check stress"` | read_stress | Reads stress score | "Current stress index is moderate at 0.42." |

### Clinical Test Commands

| Spoken Command | Intent | Action | Talkback Response |
|:---|:---|:---|:---|
| `"Maitri, start PVT test"` | start_pvt | Launches 3-min PVT-B | "Starting PVT test. Focus on the screen." |
| `"Maitri, stop PVT"` | stop_pvt | Ends test, scores | "PVT cancelled." |
| `"Maitri, start depression check"` | screener_depression | Begins PHQ-9 | "Starting PHQ-9 depression screener." |
| `"Maitri, start anxiety check"` | screener_anxiety | Begins GAD-7 | "Starting GAD-7 anxiety screener." |
| `"Maitri, start breathing exercise"` | start_breathing | Box breathing | "Beginning 4-7-8 breathing. Inhale for 4..." |

### Safety & Emergency Commands

| Spoken Command | Intent | Action | Talkback Response |
|:---|:---|:---|:---|
| `"Maitri, acknowledge"` | watchdog_ack | Check-in confirmation | "Presence confirmed. All clear." |
| `"Maitri, I am here"` | watchdog_ack | Watchdog keepalive | "Acknowledged. Monitoring continues." |
| `"Maitri, checklist ammonia"` | checklist_ammonia | Opens ammonia SOP | "Opening ammonia leak response checklist." |
| `"Maitri, checklist trauma"` | checklist_trauma | Opens trauma SOP | "Opening acute trauma response checklist." |
| `"Maitri, override incapacitation"` | critical_override | Safety gate prompt | "Critical override requested. Say 'confirm override' to proceed." |
| `"Maitri, confirm override"` | confirm_critical | Executes override | "Override confirmed. Logging to audit chain." |

### Data Commands

| Spoken Command | Intent | Action | Talkback Response |
|:---|:---|:---|:---|
| `"Maitri, log reading"` | log_reading | Saves snapshot to DB | "Telemetry reading logged to mission database." |
| `"Maitri, run diagnostics"` | (BIST) | Opens BIST modal | "Built-in self-test running..." |

---

## 🎨 Design System

MAITRI uses a custom **aerospace dark cockpit** design language inspired by NASA mission control and ISO/IEC medical device HMI standards.

### Color Tokens

| Token | Hex | Tailwind | Usage |
|:---:|:---:|:---:|:---|
| `--color-bg` | `#0a0e1a` | `bg-slate-950` | Main background (deep space black) |
| `--color-surface` | `#111827` | `bg-gray-900` | Card surfaces |
| `--color-border` | `#1f2937` | `border-gray-800` | Dividers, card outlines |
| `--color-text-primary` | `#f1f5f9` | `text-slate-100` | Primary text |
| `--color-text-secondary` | `#64748b` | `text-slate-500` | Labels, secondary |
| `--color-accent-cyan` | `#06b6d4` | `text-cyan-500` | Live indicators, active state |
| `--color-accent-blue` | `#3b82f6` | `text-blue-500` | Interactive elements |
| `--color-status-ok` | `#22c55e` | `text-green-500` | Nominal / safe |
| `--color-status-warn` | `#f59e0b` | `text-amber-500` | MEDIUM alarm (IEC ■) |
| `--color-status-crit` | `#ef4444` | `text-red-500` | HIGH alarm (IEC ▲) |
| `--color-status-info` | `#06b6d4` | `text-cyan-500` | INFO alarm (IEC ◆) |
| `--color-night-primary` | `#ff6b35` | `text-orange-500` | Night mode 620nm red/amber |
| `--color-night-bg` | `#1a0a00` | custom | Night mode background |

### IEC 60601-1-8 Alarm Visual Encoding

The standard mandates specific shapes and colors — MAITRI follows them exactly:

| Priority | Shape | Color | Sound | Action |
|:---:|:---:|:---:|:---:|:---|
| **HIGH** | ▲ Triangle | Red `#ef4444` | 3 pulses rapid | Immediate response required |
| **MEDIUM** | ■ Square | Amber `#f59e0b` | 2 pulses | Prompt attention |
| **LOW** | ◆ Diamond | Cyan `#06b6d4` | 1 pulse | Awareness |
| **INFO** | ● Circle | Blue `#3b82f6` | None | Information |

### Circadian Night Mode

Activated via toggle or voice (auto at mission night period):
- Background shifts to `#1a0a00` (deep amber-black)
- All text shifts to 620nm wavelength red/amber spectrum (`#ff6b35`)
- Charts use amber gradients instead of cyan
- **Rationale:** 620nm red light does not suppress melatonin (Brainard et al. 2001)
- NASA-STD-3001 Vol.1 §4.6.2 — crew quarters light specification

### Typography

| Use | Font | Weight | Size |
|:---|:---:|:---:|:---:|
| Data values | `JetBrains Mono` (self-hosted) | 700 Bold | 2xl–4xl |
| Labels | `Inter` (self-hosted) | 400 Regular | sm–base |
| Alarms | `Inter` | 600 SemiBold | base–lg |
| Code/JSON | `JetBrains Mono` | 400 Regular | xs–sm |

> All fonts are bundled as WOFF2 in `frontend/public/fonts/` — zero CDN dependencies.

### Motion & Accessibility

- **Reduced motion:** Respects `prefers-reduced-motion: reduce` — animations suppressed
- **Touch targets:** Minimum 44×44px per WCAG 2.5.5 (NASA-STD-3001 touch standard)
- **Color blind safe:** All status information encoded in SHAPE + COLOR (not color alone)
- **Keyboard:** Full operation without mouse — hotkeys 1–5, Tab/Enter/Space for forms
- **WCAG 2.2 AA:** 4.5:1 contrast ratio minimum for all text on dark backgrounds

---

## 🔧 Installation & Quickstart

### Prerequisites

| Requirement | Version | Notes |
|:---|:---:|:---|
| Python | **3.11** | ⚠️ Use `venv311` — NOT system Python 3.14 |
| Node.js | ≥18.0 | For frontend build |
| npm | ≥9.0 | Frontend package manager |
| Webcam | Any | Optional — works without |
| Microphone | Any | Optional — works without |

### Step 1: Clone & Setup

```bash
git clone https://github.com/MukulKumbhar/MAITRI_AE.git
cd MAITRI_AE

# Create Python 3.11 virtual environment (REQUIRED — do not use system Python)
python3.11 -m venv venv311
source venv311/bin/activate

# Install backend dependencies
pip install -r requirements.txt
```

### Step 2: Download AI Models

> Models are **not included** in git (too large). Download separately:

```bash
# Option A: Download from releases (when available)
wget https://github.com/MukulKumbhar/MAITRI_AE/releases/download/v2.0/models.tar.gz
tar -xzf models.tar.gz

# Option B: Download individually
mkdir -p models/vosk models/piper_voice

# Vosk English model (40 MB)
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip -d models/vosk/

# Piper TTS voice (63 MB)
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx \
     -O models/piper_voice/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json \
     -O models/piper_voice/en_US-lessac-medium.onnx.json
```

### Step 3: Build Frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### Step 4: Launch MAITRI

```bash
# Standard launch (opens browser automatically)
./venv311/bin/python run_maitri.py --port 8000

# Background / no browser
./venv311/bin/python run_maitri.py --port 8001 --no-browser

# Custom port
./venv311/bin/python run_maitri.py --port 8080
```

Then open: **http://localhost:8000**

> ⚠️ **IMPORTANT:** Always use `./venv311/bin/python` — NOT `python` or `python3`.  
> The system Python may be a different version and will fail to import modules.

### Common Issues

| Error | Cause | Fix |
|:---|:---|:---|
| `ModuleNotFoundError: uvicorn` | Wrong Python (system venv, not venv311) | Use `./venv311/bin/python run_maitri.py` |
| `Address already in use` | Port 8000 occupied by old process | Add `--port 8001` |
| Camera not working | Browser permission denied | Allow camera in browser settings |
| Vosk not loading | Model files missing | Download model to `models/vosk/` |
| Piper TTS silent | Voice model missing | Download to `models/piper_voice/` |
| `'dict' object has no attribute 'asr_enabled'` | Old state format | Delete `maitri_clinical.db` and restart |

---

## 🌐 Running Fully Offline (Proof)

MAITRI is designed to operate in a **complete network blackout** — as would occur during deep space transit or communication blackout periods.

```bash
# 1. Build frontend for offline (self-hosted)
cd frontend && npm run build && cd ..

# 2. Disable network (Linux)
sudo ip link set eth0 down
sudo ip link set wlan0 down

# 3. Start MAITRI
./venv311/bin/python run_maitri.py --port 8000

# 4. Open browser to http://localhost:8000
#    → Loads from local FastAPI static file server
#    → Zero external requests (verify in browser DevTools Network tab)

# 5. Test all features:
#    ✅ Camera live feed
#    ✅ Voice commands
#    ✅ AI emotion detection
#    ✅ PHQ-9 screener
#    ✅ PVT-B test
#    ✅ Medical knowledge base
#    ✅ Emergency checklists
#    ✅ Phi-3 medical assistant

# 6. Re-enable network
sudo ip link set eth0 up
```

**Offline verification checklist:**
- [ ] No requests to `fonts.googleapis.com` or any CDN
- [ ] No requests to `api.openai.com` or any AI cloud service
- [ ] No requests to any domain other than `localhost`
- [ ] All features functional with network disabled
- [ ] Piper TTS works (no cloud TTS fallback)
- [ ] Vosk ASR works (no cloud ASR fallback)

---

## 🧪 Test Matrix — 254 Tests

```bash
# Run full test suite
./venv311/bin/python -m pytest tests/ -v

# Expected output: 254 passed, 0 failed in ~58s
```

| Test File | Tests | Coverage Area |
|:---|:---:|:---|
| `tests/test_intent_parser.py` | 48 | Voice intent parsing, phonetic corrections, number words, safety gate |
| `tests/test_voice_service.py` | 35 | VAD, Vosk mock, TTS synthesis, wake word detection |
| `tests/test_vitals_module.py` | 32 | HRV (rMSSD, SDNN, Baevsky), respiratory rate, CO₂ Law 2014 |
| `tests/test_fusion_module.py` | 28 | Welford variance, CUSUM alerts, adaptive EMA, baseline deviation |
| `tests/test_clinical_core.py` | 38 | IEC alarm lifecycle, dedup, mute, escalation, SHA-256 chain |
| `tests/test_clinical_extended.py` | 23 | PVT-B engine, circadian model, PHQ-9 safety gate, medical KB |
| `tests/test_vision_service.py` | 18 | Frame processing, ONNX inference mock, EAR calculation |
| `tests/test_database_module.py` | 22 | SQLite operations, audit chain, tamper detection |
| `tests/test_api.py` | 10 | FastAPI endpoint integration tests |
| **TOTAL** | **254** | **100% pass rate** |

### Test Categories by Criticality

| Category | Tests | Status |
|:---|:---:|:---:|
| ✅ Safety-critical (PHQ-9 Item 9, alarm escalation, override gate) | 23 | Passing |
| ✅ Clinical algorithms (HRV, PVT-B, CO₂ model, circadian) | 71 | Passing |
| ✅ Data integrity (SHA-256 chain, tamper detection, DB operations) | 60 | Passing |
| ✅ Voice pipeline (ASR, intent, TTS, phonetics) | 83 | Passing |
| ✅ API contracts (REST endpoints, WebSocket events) | 17 | Passing |

---

## 📡 Full Architecture Diagram

```
╔══════════════════════════════════════════════════════════════════════╗
║                     MAITRI 2.0 — DATA FLOW MAP                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  INPUT SOURCES                    PROCESSING                OUTPUT   ║
║  ─────────────                    ──────────                ──────── ║
║                                                                      ║
║  📷 Webcam ──────────────► MediaPipe FaceLandmarker (WASM)          ║
║                             478 landmarks + 52 FACS                  ║
║                              ├── EAR (EyeAspectRatio)               ║
║                              └──► EfficientNet-B2 ONNX              ║
║                                    7-class emotion probs             ║
║                                     └──► fusion_module ──► 🖥 UI    ║
║                                                                      ║
║  🎤 Microphone ──────────► Vosk Kaldi ASR (offline)                 ║
║   (16kHz PCM)               Raw transcript                           ║
║                              └── intent_parser (fuzzy + phonetics)  ║
║                                   Intent + Entity                    ║
║                                    ├──► State update                 ║
║                                    └──► Piper TTS ──► 🔊 Speaker    ║
║                                                                      ║
║  🖱 Manual Input ────────► Telemetry Service (SensorAdapter)        ║
║   (sliders/voice)           Sensor Mode: Live / Manual / Replay      ║
║                              └──► state.py (PhaseState)             ║
║                                                                      ║
║  📊 Simulated Data ──────► Scenario Generator (4 scenarios)         ║
║   (Replay mode)             Time-stamped telemetry replay            ║
║                              └──► state.py (labeled SIMULATED)      ║
║                                                                      ║
║  ═══════════════════════════════════════════════════════════════════ ║
║                                                                      ║
║  CLINICAL ENGINE                                                     ║
║                                                                      ║
║  state.py ──────────────► fusion_module (Adaptive EMA)              ║
║   All signals               Welford baseline + CUSUM alerts          ║
║                              └──► Composite health score 0–1        ║
║                                                                      ║
║               ──────────► vitals_module (HRV engine)                ║
║                             rMSSD + SDNN + Baevsky SI               ║
║                             CO₂ Law 2014 hazard model               ║
║                                                                      ║
║               ──────────► pvt_module (PVT-B 3-min test)            ║
║                             Basner & Dinges 2011 protocol           ║
║                             Lapse count, mean RT, alertness score   ║
║                                                                      ║
║               ──────────► circadian_module (sleep/rhythm)           ║
║                             Cosinor model, ISS orbital sync         ║
║                                                                      ║
║               ──────────► screener_module (PHQ-9/GAD-7/PSS-4)      ║
║                             PHQ-9 Item 9 → Safety Gate              ║
║                                                                      ║
║               ──────────► alert_module (IEC 60601-1-8)              ║
║                             HIGH▲ MEDIUM■ LOW◆ INFO●               ║
║                             Dedup, mute 120s, escalate 3min         ║
║                                                                      ║
║  ═══════════════════════════════════════════════════════════════════ ║
║                                                                      ║
║  STORAGE & INTEGRITY                                                 ║
║                                                                      ║
║  database_module ────────► SQLite maitri_clinical.db                ║
║   SHA-256 hash chain        telemetry_log                           ║
║                             alarm_events                             ║
║                             screener_results                         ║
║                             audit_chain (tamper-evident)            ║
║                              └──► BIST verification                 ║
║                              └──► DTN export (flight surgeon)       ║
║                                                                      ║
║  ═══════════════════════════════════════════════════════════════════ ║
║                                                                      ║
║  FRONTEND — 5-VIEW COCKPIT (React 18 + TypeScript + Tailwind)       ║
║                                                                      ║
║  WebSocket /ws/telemetry ─► All tabs receive live TelemetryRecord   ║
║  WebSocket /ws/audio ─────► voice_service (bidirectional)           ║
║  WebSocket /ws/video ─────► vision_service (video frames)           ║
║  REST /api/clinical/* ────► Screeners, PVT, alarms, KB queries     ║
║                                                                      ║
║  Tab 1 Overview   ──────► Radar + Alarms + Emotion + Watchdog      ║
║  Tab 2 Cardio     ──────► HRV chart + Baevsky + Manual sliders     ║
║  Tab 3 Neuro      ──────► PVT-B widget + Circadian clock           ║
║  Tab 4 Cabin      ──────► CO₂/O₂/Temp/Humidity gauges             ║
║  Tab 5 Medical    ──────► Phi-3 chat + Checklists + Screeners      ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## ⚠️ Known Limitations & Disclaimer

### Medical Disclaimer

> **MAITRI is a CLINICAL DECISION SUPPORT TOOL, not a certified medical device.**
>
> - It has NOT been validated to IEC 62304, ISO 14155, or FDA 21 CFR Part 820
> - All clinical thresholds are cited from peer-reviewed sources OR explicitly marked "configurable demo default"
> - Emotion recognition models have known bias toward demographic groups underrepresented in training data
> - EfficientNet-B2 was trained on FER+/AffectNet — not validated for spaceflight population or microgravity facial changes
> - PVT-B via keyboard/screen may differ from laboratory validated apparatus
> - **Always defer to qualified flight surgeons and mission medical protocols**

### Technical Limitations

| Limitation | Details | Mitigation |
|:---|:---|:---|
| No real physiology sensors | HR/SpO₂ from manual entry or simulation | Clearly labeled; hardware adapter interface documented |
| Emotion AI bias | FER+/AffectNet training data demographics | Model card included; use as trend not diagnosis |
| Phi-3 hallucination risk | LLM can generate plausible-sounding wrong answers | Medical KB wrapper refuses if unsure; citations required |
| CPU-only Phi-3 | ~8 tokens/sec on laptop CPU | Acceptable for non-emergency use; not for real-time |
| SQLite concurrency | Single-writer limitation | Acceptable for single-crew-member use |
| ASR accuracy | Vosk small model ~90% WER for spaceflight terminology | Phonetic corrections, fuzzy matching mitigate this |
| Camera EAR limitations | Glasses/lighting affect EAR reliability | Used as trend indicator, not absolute measurement |

### Model Cards

| Model | Training Data | Known Biases | Validation |
|:---|:---|:---|:---|
| EfficientNet-B2 (emotion) | FER2013 + AffectNet (~280k images) | Lower accuracy for darker skin tones, ages >60 | 65.3% test accuracy on FER2013 |
| Vosk Kaldi | LibriSpeech + other English corpora | Accented speech may reduce accuracy | WER ~5.5% clean, ~15% noisy |
| Phi-3 Mini | Public web text, filtered | May generate confident wrong medical info | Use KB grounding layer only |

---

## 🌳 Repository Structure

```
MAITRI_AE/
├── 📄 run_maitri.py              # Main launcher (auto-detects venv311)
├── 📄 requirements.txt           # Python dependencies
├── 📄 README.md                  # This file
│
├── 🗂 backend/
│   ├── 📄 state.py               # Global clinical state, IEC alarms, sensor adapter
│   ├── 🗂 api/
│   │   ├── 📄 clinical.py        # REST endpoints: /api/clinical/*
│   │   └── 📄 health.py          # System health endpoint
│   └── 🗂 services/
│       ├── 📄 voice_service.py   # Vosk ASR + Piper TTS + VAD (520 lines)
│       ├── 📄 vision_service.py  # EfficientNet-B2 ONNX frame processing
│       ├── 📄 telemetry_service.py # Sensor adapter + WebSocket broadcast
│       ├── 📄 psych_service.py   # Phi-3 Mini medical assistant
│       ├── 📄 bist_service.py    # Built-in self-test diagnostics
│       └── 📄 intent_parser.py   # Fuzzy NLU + phonetic corrections
│
├── 🗂 modules/                   # Clinical intelligence modules
│   ├── 📄 face_module.py         # M1: Facial emotion recognition
│   ├── 📄 eye_module.py          # M2: EAR / oculomotor
│   ├── 📄 vitals_module.py       # M3: HRV + CO₂ Law 2014 model
│   ├── 📄 fusion_module.py       # M4: Multi-modal fusion + baselines
│   ├── 📄 alert_module.py        # M5: IEC 60601-1-8 alarm management
│   ├── 📄 database_module.py     # M6: SQLite + SHA-256 audit chain
│   ├── 📄 pvt_module.py          # Psychomotor Vigilance Test (PVT-B)
│   ├── 📄 circadian_module.py    # Sleep debt + cosinor rhythm model
│   ├── 📄 screener_module.py     # PHQ-9, GAD-7, PSS-4 screeners
│   └── 📄 medical_kb.py          # Offline medical KB + checklists
│
├── 🗂 frontend/
│   ├── 🗂 src/
│   │   ├── 📄 App.tsx             # Root: tab routing, global WebSocket, alarms
│   │   ├── 🗂 components/
│   │   │   ├── 🗂 tabs/
│   │   │   │   ├── 📄 OverviewTab.tsx   # Tab 1: Mission status radar
│   │   │   │   ├── 📄 CardioTab.tsx     # Tab 2: HRV panel + manual sliders
│   │   │   │   ├── 📄 NeuroTab.tsx      # Tab 3: PVT-B + circadian
│   │   │   │   ├── 📄 CabinTab.tsx      # Tab 4: ECLSS environment
│   │   │   │   └── 📄 MedicalTab.tsx    # Tab 5: AI assistant + screeners
│   │   │   └── 🗂 shell/
│   │   │       ├── 📄 Header.tsx        # Nav tabs + emotion chips + night mode
│   │   │       ├── 📄 WatchdogBanner.tsx # IEC alarm banner
│   │   │       ├── 📄 BistModal.tsx     # BIST + SHA-256 chain inspector
│   │   │       └── 📄 VoiceDebugDrawer.tsx # Voice pipeline debug panel
│   │   └── 🗂 services/
│   │       ├── 📄 visionPipeline.ts    # MediaPipe + JPEG frame capture
│   │       ├── 📄 audioSocket.ts       # Microphone AudioWorklet + VAD
│   │       ├── 📄 telemetrySocket.ts   # Vitals WebSocket client
│   │       └── 📄 api.ts               # REST client for clinical API
│   └── 📄 vite.config.ts         # Code splitting: 5 chunks, all <212kB
│
├── 🗂 models/                    # AI models (not in git — download separately)
│   ├── 📄 enet_b2_7.onnx         # EfficientNet-B2 7-class emotion
│   ├── 📄 enet_b0_8_best_vgaf.onnx
│   ├── 📄 face_landmarker.task   # MediaPipe Face Landmarker
│   ├── 📄 phi3_mini_q4.gguf      # Phi-3 Mini 4-bit (medical assistant)
│   ├── 📄 wav2vec2_ser_q4.onnx   # Speech emotion recognition
│   ├── 🗂 vosk/                  # Vosk Kaldi ASR model
│   └── 🗂 piper_voice/           # Piper TTS voice model
│
└── 🗂 tests/                     # 254 tests, 100% pass rate
    ├── 📄 test_intent_parser.py
    ├── 📄 test_voice_service.py
    ├── 📄 test_vitals_module.py
    ├── 📄 test_fusion_module.py
    ├── 📄 test_clinical_core.py
    ├── 📄 test_clinical_extended.py
    ├── 📄 test_vision_service.py
    ├── 📄 test_database_module.py
    └── 📄 test_api.py
```

---

## 🔐 Security & Data Integrity

| Feature | Implementation | Standard |
|:---|:---|:---|
| **Localhost-only binding** | FastAPI `host="127.0.0.1"` | No external network exposure |
| **Strict CSP** | `Content-Security-Policy: default-src 'self'` | OWASP recommendations |
| **SHA-256 audit chain** | Hash-chained SQLite table | Tamper-evident medical records |
| **Encrypted storage** | SQLite with SQLCipher (optional) | Healthcare data at rest |
| **No external requests** | Zero CDN, zero API calls | Air-gap compliance |
| **Input validation** | Pydantic models on all API inputs | FastAPI + Pydantic V2 |
| **Safety gate** | 2-step confirm for critical overrides | Prevents accidental system changes |

---

## 📚 Sources & Citations

| Reference | Used For |
|:---|:---|
| ESC/NASPE Task Force (1996). *Standards of Measurement, Physiological Interpretation and Clinical Use of Heart Rate Variability.* Circulation 93:1043–65. | HRV rMSSD, SDNN definitions |
| Baevsky R.M. et al. (2001). *Analysis of Heart Rate Variability in Space Medicine.* Human Physiology 27(6):735–748. | Baevsky Stress Index |
| Basner M. & Dinges D.F. (2011). *Maximizing Sensitivity of the Psychomotor Vigilance Test (PVT) to Sleep Loss.* Sleep 34(5):581–591. | PVT-B protocol, lapse threshold 355ms |
| Law J. et al. (2014). *Relationship of CO₂ Levels to Symptoms and Performance.* J.Applied Physiology 116(10):1346–1357. | CO₂ hazard model thresholds |
| Kroenke K. & Spitzer R.L. (2001). *The PHQ-9: Validity of a Brief Depression Severity Measure.* J.Gen.Intern.Med. 16(9):606–613. | PHQ-9 screener |
| Spitzer R.L. et al. (2006). *A Brief Measure for Assessing Generalized Anxiety Disorder.* Arch.Intern.Med. 166(10):1092–1097. | GAD-7 screener |
| Cohen S. et al. (1983). *A Global Measure of Perceived Stress.* J.Health.Soc.Behav. 24(4):385–396. | PSS-4 screener |
| IEC 60601-1-8 (2006, Amd.2015). *Medical Electrical Equipment — Alarm Systems.* | Alarm priority, shapes, colors |
| NASA-STD-3001 Vol.1 & Vol.2. *NASA Space Human Factors Design Standard.* | Environmental thresholds, HMI |
| Brainard G.C. et al. (2001). *Action Spectrum for Melatonin Regulation in Humans.* J.Neurosci. 21(16):6405–6412. | Night mode 620nm wavelength |
| WCAG 2.2 (2023). *Web Content Accessibility Guidelines.* W3C. | Contrast ratios, touch targets |

---

## 🤝 Contributing

MAITRI is an open research prototype for the aerospace medicine community.

```bash
# Fork and clone
git clone https://github.com/YourUsername/MAITRI_AE.git
cd MAITRI_AE
git checkout -b feature/your-feature

# Install dev dependencies
source venv311/bin/activate
pip install -r requirements-dev.txt

# Make changes and run tests
./venv311/bin/python -m pytest tests/ -v

# Submit PR against the experimental branch
git push origin feature/your-feature
```

**Contribution guidelines:**
1. All clinical thresholds must include peer-reviewed citations
2. New AI models must have a model card with known limitations
3. Tests required for all clinical algorithms
4. All assets must be self-hostable (no CDN dependencies)
5. No scope creep beyond astronaut health monitoring

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built for the crews who go where no one can help them in real-time.**

```
Mission Duration: Long
Communication Delay: 24 minutes
Ground Support: Unavailable
MAITRI: Online ✅
```

*"The best medical system for a Mars mission is the one that works when Earth can't answer."*

---

🛰️ **MAITRI 2.0** | 254 Tests Passing | 100% Offline | Aerospace Grade

</div>
