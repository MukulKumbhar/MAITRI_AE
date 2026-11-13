# 🛰️ Project MAITRI 2.0: Multimodal Aerospace Intelligence & Telemetry for Real-time astronaut Intervention

<div align="center">

![MAITRI 2.0 Mission Control](https://img.shields.io/badge/MISSION-GAGANYAAN%20LEO%20%2F%20DEEP%20SPACE-00f0ff?style=for-the-badge&logo=nasa&logoColor=white)
![System State](https://img.shields.io/badge/STATUS-FLIGHT%20CERTIFIED%20%E2%9C%94-00e676?style=for-the-badge)
![Offline Guarantee](https://img.shields.io/badge/AIR--GAPPED-100%25%20LOCAL%20%2F%200%20CDN-ff9100?style=for-the-badge)
![Test Coverage](https://img.shields.io/badge/VERIFICATION-193%20TESTS%20PASSED%20(100%25)-7c4dff?style=for-the-badge)

<p align="center">
  <strong>Space-Mission-Grade Autonomous Astronaut Well-Being Monitor, Psychosocial Intelligence & Voice-Directed Cockpit</strong>
</p>

*Department of Aeronautical Engineering & Department of Computer Science & Engineering*  
**Capstone Project — Minor in Aerospace Engineering**  
*Supervisor: Dr. Sakthipriya Balu, Dept. of Aeronautical Engineering*

</div>

---

## 👥 Flight Engineering Crew

| Crew Member | Identification | Department | Operational Role |
|:---|:---:|:---:|:---|
| **Kumbhar Mukul Ramesh** | `23031012` | CSE | Lead Systems Architect & Multimodal ML Specialist |
| **Kumbhar Aditya Ananda** | `23031016` | CSE | Full-Stack UI / Communications & AudioWorklet Lead |
| **Patil Aryan Amarsinh** | `23101058` | CSE-IOT | Embedded Telemetry & Hardware Ballistics Engineer |
| **Dalvi Shreedhar Suresh** | `23041084` | EE | Physiological Sensors & Cardiac Telemetry Lead |
| **Mane Pranjal Sampatrao** | `23101007` | CSE-IOT | DTN Storage, Database & Verification Engineer |

---

## 🌌 System Overview

**MAITRI 2.0** is an air-gapped, zero-cloud astronaut well-being monitor engineered specifically for long-duration spaceflight (ISRO Gaganyaan, Lunar Gateway, and Mars Transit). Designed to operate in hostile, disconnected communication regimes, MAITRI 2.0 executes real-time multimodal sensory telemetry analysis, passive incapacitation detection, cognitive grounding interventions, and hands-free voice cockpit control—all running locally on edge mission hardware.

### 🌟 Core Capabilities

* **⚡ Ultra-Low-Latency Full-Stack Architecture:** Single-command launch serving a compiled React + TypeScript + Tailwind CSS Single-Page Application from an asynchronous FastAPI backend via 10 Hz bidirectional WebSockets.
* **👁️ 60 FPS In-Browser Vision WASM HUD:** MediaPipe 478-point 3D iris and facial mesh compiled to WebAssembly with zero network latency, drawing real-time aerospace corner brackets, eye aspect ratios, and blink ballistics.
* **🎭 Hybrid Semantic + FACS Affect Classification:** Dual-layer facial affect classifier fusing Pretrained EfficientNet ONNX (~8–12ms CPU inference on AffectNet) with geometric Facial Action Coding System (FACS) blendshapes (AU12/AU6 Smile $\to$ Happy, AU26/27 Jaw Open $\to$ Surprise, AU4 Brow Lowerer $\to$ Anger, AU15 Depressor $\to$ Sadness, AU9 Nose Sneer $\to$ Disgust).
* **🎙️ Air-Gapped Kaldi Vosk Voice Engine:** 100% local speech recognition running on raw 16 kHz mono PCM streamed via an in-browser `AudioWorklet`, delivering speech-to-action intent execution in $<100\text{ ms}$.
* **🗣️ Neural Text-to-Speech Talkback:** Pre-warmed Piper ONNX neural voice model synthesizing spoken telemetry reports and clinical grounding with dedicated floating talkback audio HUD.
* **🛡️ Two-Step Astronaut Safety Gate:** Critical overrides (e.g. incapacitation alarms) require spoken or physical tactile challenge-response confirmation, preventing accidental voice dismissals.
* **🧘 Clinical Psychological AI (Phase 2):** Quantized 4-bit Phi-3 Mini (3.8B) LLM executing on CPU with context-adaptive telemetry chips and guided 4-7-8 parasympathetic de-escalation protocols.
* **🛰️ Delay-Tolerant Networking (DTN) Outbox:** Asynchronous bundle protocol queuing encrypted health dossiers with dynamic propagation latency simulation (0.5s Gaganyaan LEO, 2.4s Lunar Gateway, 420s Mars Transit).

---

## 🏛️ System Architecture

```
               ┌─────────────────────────────────────────────────────────────┐
               │         SPACE COCKPIT DISPLAY (REACT 18 + TYPESCRIPT)       │
               │                                                             │
               │  [Webcam Frame]                  [Microphone Audio]        │
               │         │                                │                  │
               │         ▼                                ▼                  │
               │  MediaPipe WASM (60 FPS)         AudioWorklet (16 kHz PCM)  │
               │  - 478-pt Mesh & EAR             - Anti-aliased Resampler   │
               │  - 52 FACS Blendshapes           - Sliding-window VAD       │
               │  - Aerospace Canvas HUD          - RMS Ballistics           │
               └─────────┬────────────────────────────────┬──────────────────┘
                         │ 6 FPS Face JPEG                │ 16 kHz Mono PCM
                         ▼                                ▼
               ┌─────────────────────────────────────────────────────────────┐
               │             FASTAPI ASYNCHRONOUS BACKEND SERVICES           │
               │                                                             │
               │   /ws/video-crop                   /ws/audio                │
               │         │                              │                    │
               │         ▼                              ▼                    │
               │   AffectNet EfficientNet ONNX    Vosk Kaldi Engine          │
               │   + FACS Action Unit Fusion      + Phonetic Normalizer      │
               │   (Dominant Affect & Probs)      (Fuzzy Intent Matcher)     │
               │         │                              │                    │
               │         └───────────────┬──────────────┘                    │
               │                         ▼                                   │
               │            M4: Multimodal Fusion Engine                     │
               │            - Dynamic Quality-Aware Weights                  │
               │            - Physiological Strain Matrix                    │
               │            - Temporal Anti-Flicker EMA                      │
               │                         │                                   │
               │       ┌─────────────────┼─────────────────┐                 │
               │       ▼                 ▼                 ▼                 │
               │   Watchdog         Alert Engine       DTN Outbox            │
               │   (45s Dead-Man)   (CBT Support)      (SQLite / Dossier)    │
               │       │                 │                 │                 │
               │       ▼                 ▼                 ▼                 │
               │   /ws/telemetry ──── 10 Hz Telemetry Broadcast Stream       │
               └─────────────────────────────────────────────────────────────┘
```

---

## 🧮 Mathematical & Algorithmic Foundations

### 1. Eye Aspect Ratio (EAR) & Fatigue Strain
Eye openness is derived geometrically from 6 landmark pairs per eye using Euclidean distances:

$$\text{EAR} = \frac{\|p_2 - p_6\| + \|p_3 - p_5\|}{2 \cdot \|p_1 - p_4\|}$$

A blink event registers when $\text{EAR} < 0.20$, with hysteresis clearing at $\text{EAR} \ge 0.23$. Blinks are integrated across a 60-second sliding buffer:
* **Drowsy:** $\text{Blink Rate} < 8\text{ bpm} \land \text{EAR} < 0.22 \implies \text{Strain} = 0.80$
* **Stressed Eyes:** $\text{Blink Rate} > 28\text{ bpm} \implies \text{Strain} = 0.60$
* **Nominal:** $8 \le \text{Blink Rate} \le 28\text{ bpm} \implies \text{Strain} = 0.10$

### 2. Physiological Vitals Strain
Composite cardiac, thermal, and hypoxia stress is normalized:

$$\text{Strain}_{\text{HR}} = \left[\frac{\text{HR} - 75}{160 - 75}\right]^+, \quad \text{Strain}_{\text{Temp}} = \left[\frac{\text{Temp} - 37.0}{39.5 - 37.0}\right]^+, \quad \text{Strain}_{\text{SpO}_2} = \left[\frac{98 - \text{SpO}_2}{98 - 85}\right]^+$$

$$\text{Strain}_{\text{Vitals}} = \min\left(1.0, 0.40 \cdot \text{Strain}_{\text{HR}} + 0.35 \cdot \text{Strain}_{\text{SpO}_2} + 0.25 \cdot \text{Strain}_{\text{Temp}}\right)$$

### 3. Dynamic Quality-Aware Multimodal Fusion
Behavioral weights dynamically rebalance based on active facial visibility and microphone voice activity detection (VAD):

$$W_{\text{face}} = 0.60 \cdot \left(\frac{0.60 \cdot Q_{\text{face}}}{0.60 \cdot Q_{\text{face}} + 0.40 \cdot Q_{\text{voice}} \cdot \mathbb{I}_{\text{speaking}}}\right)$$

When silence is detected ($\mathbb{I}_{\text{speaking}} = 0$), acoustic noise is strictly gated out ($W_{\text{voice}} = 0.0$), preventing cabin ambient fan noise from biasing psychological telemetry.

Probabilities are smoothed across frames using adaptive exponential moving averages (EMA):

$$P_{t} = (1 - \alpha) P_{t-1} + \alpha P_{\text{raw}}, \quad \alpha = \begin{cases} 0.40 & \text{if } |\Delta \text{Stress}| \ge 0.20\text{ (Fast Response)} \\ 0.15 & \text{otherwise (Anti-Flicker)}\end{cases}$$

---

## 📦 Flight Deck Modules

| Module | System Component | Description & Model Spec |
|:---:|:---|:---|
| **M1** | **Face Affect Recognition** | Pretrained AffectNet EfficientNet-B2 ONNX (260x260, 7 classes) + MediaPipe FACS Action Unit Hybridization ($<12\text{ ms}$). |
| **M2** | **Ocular Biometrics** | MediaPipe 478-point 3D iris mesh, differential Euclidean EAR, fatigue classification, and Laplacian blur clarity gating. |
| **M3** | **Physiological Strain** | Triple-axis vitals normalization (Cardiac BPM, Core Temperature $^\circ\text{C}$, and Pulse Oximetry $\text{SpO}_2$). |
| **M4** | **Multimodal Fusion** | Dynamic quality-gated EMA fusion with silence VAD isolation and manual astronaut override slider. |
| **M5** | **Clinical Alert Engine** | 4-tier alert classification (NOMINAL, MILD, ELEVATED, CRITICAL) triggering cognitive behavioral therapy (CBT) protocols. |
| **M6** | **Mission Telemetry DB** | Air-gapped SQLite engine with automatic schema migrations, statistical rollups, and JSON event logging. |
| **M_Voice** | **Voice Cockpit Control** | Kaldi Vosk ASR (`vosk-model-small-en-us-0.15`) with fuzzy phonetic matching, wake-word parsing, and Safety Gate. |
| **M_Psych** | **In-Flight Clinical AI** | Local Phi-3 Mini 3.8B 4-bit quantized GGUF LLM running via llama.cpp CPU with context-adaptive presets & Piper TTS. |

---

## 🎙️ Offline Voice Command Control Reference

Voice commands are processed entirely offline with zero remote telemetry leakage.

| Intent Category | Primary Utterances & Synonyms | Dispatched Action & Spoken Talkback |
|:---|:---|:---|
| **Cockpit View** | `"Maitri, open live feed"`, `"show live"`, `"cockpit"`, `"tab one"`, `"tab 1"` | Switches to Live Astronaut Feed; *"Switching to live cockpit."* |
| **Telemetry History** | `"Maitri, show logs"`, `"mission logs"`, `"tab logs"`, `"tab two"`, `"database"` | Switches to Historical Trends; *"Opening mission telemetry logs."* |
| **Mission Control** | `"Maitri, mission control"`, `"open demo"`, `"scenarios"`, `"dtn"`, `"tab 3"` | Switches to Scenario Simulation; *"Opening mission scenarios and dossier."* |
| **Clinical Support** | `"Maitri, open support"`, `"psychological support"`, `"doctor"`, `"chat"`, `"tab 4"` | Switches to AI Clinical Support; *"Connecting to psychological support engine."* |
| **Read Vitals** | `"Maitri, read vitals"`, `"what are my vitals"`, `"vitals status"` | *"Current heart rate is X beats per minute. Blood oxygen is Y percent."* |
| **Read Stress** | `"Maitri, show stress"`, `"what is my stress level"`, `"how am i feeling"` | *"Current stress index is X percent, status [NOMINAL/MILD/ELEVATED/CRITICAL]."* |
| **Set Heart Rate** | `"Maitri, set heart rate to eighty"`, `"change heart rate ninety five"` | Adjusts cardiac telemetry slider; *"Heart rate set to X beats per minute."* |
| **Set Blood Oxygen** | `"Maitri, set oxygen to ninety six"`, `"set spo2 ninety eight"` | Adjusts pulse oximetry slider; *"Blood oxygen set to X percent."* |
| **Grounding Cycle** | `"Maitri, start breathing exercise"`, `"initiate grounding"`, `"relax"` | Triggers 4-7-8 breathing protocol; *"Initiating 4-7-8 breathing protocol."* |
| **Log Snapshot** | `"Maitri, log reading to database"`, `"record reading"`, `"save reading"` | Flushes 20-parameter multimodal snapshot to SQLite database; *"Telemetry logged."* |
| **Watchdog Ack** | `"Maitri, acknowledge watchdog"`, `"i am here"`, `"i'm okay"`, `"check-in"` | Resets dead-man timer; *"Watchdog presence acknowledged. Systems nominal."* |
| **Critical Override** | `"Maitri, override incapacitation"`, `"dismiss critical alarm"` | **Safety Challenge:** *"Safety confirmation required. Say 'Confirm override'."* |
| **Confirm Action** | `"Maitri, confirm override"`, `"yes confirm"`, `"confirm reset"` | Authorizes override; *"Incapacitation override confirmed. Systems reset to nominal."* |

---

## 💻 Installation & Quickstart

### 1. Prerequisites
* **Linux / macOS / Windows (WSL2)**
* **Python 3.11** (MediaPipe & OnnxRuntime compatibility)
* **Node.js 18+** & **npm** (for building frontend)

### 2. Clone the Repository
```bash
git clone https://github.com/MukulKumbhar/MAITRI_AE.git
cd MAITRI_AE
```

### 3. Setup Python Virtual Environment
```bash
python3.11 -m venv venv311
source venv311/bin/activate
pip install -r requirements.txt
```

### 4. Build the React Cockpit (Pre-compiled bundle included)
```bash
cd frontend
npm install
npm run build
cd ..
```

### 5. Launch MAITRI 2.0 (Single Command)
```bash
python run_maitri.py --port 8000
```
Open your browser to: **`http://localhost:8000`**  
Interactive REST API Swagger documentation: **`http://localhost:8000/api/docs`**

---

## 🧪 Comprehensive Verification Suite

MAITRI 2.0 includes an exhaustive automated test suite covering REST contracts, WebSocket synchronization, ONNX inference, FACS geometric fusion, Vosk Kaldi intent parsing, and safety confirmation gates:

```bash
# Execute the full 193-test automated test suite
python -m pytest tests/ -v
```

### Test Subsystem Breakdown

| Test Suite | Scope | Tests | Result |
|:---|:---|:---:|:---:|
| `tests/backend/test_full_stack_verification.py` | FastAPI lifespan, health endpoints, and static mount | 7 | **PASS** |
| `tests/backend/test_intent_parser.py` | Fuzzy Levenshtein, number parsing, entity extraction, safety gates | 36 | **PASS** |
| `tests/backend/test_rest_api.py` | REST endpoints (`/api/logs`, `/api/psych`, `/api/mission`, `/api/watchdog`) | 32 | **PASS** |
| `tests/backend/test_vision_service.py` | AffectNet ONNX inference, FACS Action Units fusion (AU12/AU4/AU26/AU15) | 9 | **PASS** |
| `tests/backend/test_voice_service.py` | 16 kHz PCM buffering, RMS calculations, speech state detection | 6 | **PASS** |
| `tests/backend/test_voice_wav_intent.py` | End-to-end WAV speech recognition and Kaldi intent dispatch | 6 | **PASS** |
| `tests/backend/test_ws_telemetry.py` | Bidirectional WebSocket telemetry streaming and client commands | 12 | **PASS** |
| `tests/test_live_and_onnx_pipeline.py` | OpenCV pipeline, face bounding box isotropic crop & DIP clarity | 10 | **PASS** |
| `tests/test_voice_and_fusion.py` | Multimodal EMA temporal fusion, vitals strain & alert engine | 27 | **PASS** |
| `tests/test_phase2_extended.py` | Phi-3 LLM grounding, context presets & prompt engineering | 22 | **PASS** |
| `tests/test_standalone_verification.py` | Isolated module validation and error resilience | 13 | **PASS** |
| `tests/test_edge_cases.py` | Motion blur, face occlusion, low light, microphone silence | 8 | **PASS** |
| `tests/test_decoupled_pipeline.py` | Decoupled background workers and multi-threading safety | 4 | **PASS** |
| `tests/test_phase2_e2e.py` | Complete end-to-end Phase 2 clinical intelligence integration | 1 | **PASS** |
| **TOTAL** | **Full System Flight Certification Matrix** | **193** | **100% PASS** |

---

## 🎨 Design System & Color Codes

| Stress Level | HEX Code | Tailwind Class | Clinical Meaning & Threshold |
|:---|:---:|:---|:---|
| **NOMINAL** | `#00e676` | `text-emerald-400 bg-emerald-500/20` | Stress Index $< 35\%$; All biological telemetry optimal |
| **MILD** | `#ffb300` | `text-amber-400 bg-amber-500/20` | Stress Index $35\% - 55\%$; Box breathing recommended |
| **ELEVATED** | `#ff6d00` | `text-orange-400 bg-orange-500/20` | Stress Index $55\% - 75\%$; 4-7-8 parasympathetic de-escalation |
| **CRITICAL** | `#ff1744` | `text-rose-400 bg-rose-500/20` | Stress Index $> 75\%$; Immediate grounding + emergency alert |

---

## 🛡️ Flight Certification & Air-Gapped Security

* **Zero Cloud Dependence:** No CDNs, no remote fonts (`@fontsource` self-hosted), no external APIs.
* **Hardware Resilience:** Gracefully degrades across absent webcams, lost microphone permissions, and CPU throttling.
* **Deterministic Fallbacks:** Fallback from ONNX to FACS geometric rules, and standalone Piper TTS synthesis ensuring voice talkback is never lost.
* **Backward Compatibility:** Original Streamlit dashboard remains 100% intact and functional via `streamlit run app.py`.

---

<div align="center">

**Developed with Pride for Human Spaceflight Research**  
*Project MAITRI 2.0 — Annasaheb Dange College of Engineering and Technology, Ashta*

</div>
