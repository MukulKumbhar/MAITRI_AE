# 🛰️ Project MAITRI 2.0: Multimodal Aerospace Intelligence & Telemetry for Real-time astronaut Intervention

<div align="center">

![MAITRI 2.0 Mission Control](https://img.shields.io/badge/MISSION-GAGANYAAN%20LEO%20%2F%20DEEP%20SPACE-00f0ff?style=for-the-badge&logo=nasa&logoColor=white)
![System State](https://img.shields.io/badge/STATUS-FLIGHT%20CERTIFIED%20%E2%9C%94-00e676?style=for-the-badge)
![Offline Guarantee](https://img.shields.io/badge/AIR--GAPPED-100%25%20LOCAL%20%2F%200%20CDN-ff9100?style=for-the-badge)
![Test Coverage](https://img.shields.io/badge/VERIFICATION-254%20TESTS%20PASSED%20(100%25)-7c4dff?style=for-the-badge)

<p align="center">
  <strong>Space-Mission-Grade Autonomous Astronaut Health Monitor, Psychosocial Intelligence & Voice-Directed Cockpit</strong>
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

**MAITRI 2.0** is an air-gapped, zero-cloud astronaut health and well-being monitor engineered specifically for long-duration spaceflight (ISRO Gaganyaan, Lunar Gateway, and Mars Transit). Designed to operate in hostile, disconnected communication regimes with deep-space signal delays (up to 22 minutes each way to Mars), MAITRI 2.0 executes real-time multimodal biosensory telemetry analysis, personal baseline anomaly detection, cognitive readiness assessment, validated psychometrics, cabin environmental hazard correlation, and voice-guided emergency checklists—all running 100% locally on edge flight hardware.

### 🌟 Core Architectural Capabilities

* **⚡ 5-View Operational Clinical Cockpit:** Single-command launch serving a compiled React 18 + TypeScript + Tailwind CSS Single-Page Application from an asynchronous FastAPI backend via 10 Hz bidirectional WebSockets with sub-212 kB code-split chunks.
* **👁️ 60 FPS In-Browser Vision WASM HUD:** MediaPipe 478-point 3D iris and facial mesh compiled to WebAssembly with zero network latency, drawing real-time aerospace corner brackets, eye aspect ratios, and blink ballistics.
* **🎭 Hybrid Semantic + FACS Affect Classification:** Dual-layer facial affect classifier fusing AffectNet EfficientNet-B2 ONNX (~9ms CPU inference) with geometric Facial Action Coding System (FACS) blendshapes (AU12/AU6 Smile $\to$ Happy, AU26/27 Jaw Open $\to$ Surprise, AU4 Brow Lowerer $\to$ Anger, AU15 Depressor $\to$ Sadness, AU9 Nose Sneer $\to$ Disgust).
* **🫀 Cardio-Respiratory Panel with HRV:** Time-domain Heart Rate Variability (rMSSD, SDNN, Baevsky Stress Index, Guyton respiratory coupling) measuring parasympathetic recovery and autonomic resilience under microgravity cardiovascular deconditioning.
* **🧠 3-Minute PVT-B Psychomotor Vigilance Test:** Operationalized Reaction Self Test (RST) measuring sustained cognitive attention, mean Reaction Time (RT), Lapses ($>355\text{ ms}$), and False Starts ($<100\text{ ms}$) with random 2–10s inter-stimulus intervals (Basner & Dinges 2011).
* **🌙 Circadian Sleep Pod & Night Shift Mode:** Sleep debt accumulator, cosinor circadian phase estimator, ISS 90-minute orbital twilight tracker, and a one-touch 620 nm red/amber night shift mode preserving astronaut melatonin secretion.
* **📋 Validated Psychometric Screeners:** Interactive PHQ-9 (with mandatory clinical safety alert on Item 9 suicidal ideation), GAD-7, and PSS-4 tracking the evidence-backed "Third-Quarter Effect" across mission duration.
* **🌬️ Cabin Life Support & Law 2014 $\text{CO}_2$ Hazard Model:** Real-time atmospheric monitoring ($\text{CO}_2, \text{O}_2$, pressure, temp, noise) linked to astronaut symptoms with Dr. Law et al. (2014) spaceflight $\text{CO}_2$-headache odds ratio calculations.
* **📖 Offline Cited Medical Reference & Emergency Checklists:** Curated air-gapped clinical reference dataset with PubMed/NASA citations, step-by-step voice-guided emergency checklists (Toxic Ammonia Leak, Acute Trauma, Ocular Debris), and local Phi-3 Mini 3.8B clinical AI counsel with refusal boundaries.
* **🛡️ Tiered Medical Alarm Manager (IEC 60601-1-8):** High/Medium/Low/Info priority queues with visual flashing, deduplication, 120-second clinical audio pause/mute, and 3-minute automatic escalation for unacknowledged alarms.
* **🔒 Cryptographic SHA-256 Audit Ledger:** Tamper-evident hash-chained database logging ensuring medical data integrity and Built-In Self-Test (BIST) diagnostics checking cameras, mics, models, and memory.
* **🎙️ Air-Gapped Kaldi Vosk Voice Engine:** 100% local speech recognition running on raw 16 kHz mono PCM streamed via an in-browser `AudioWorklet`, delivering speech-to-action intent execution in $<100\text{ ms}$ with Piper neural TTS spoken talkback.

---

## 📸 Cockpit Views & Visual Verification

The operational cockpit is organized into 5 primary clinical views plus specialized diagnostic modals:

| View / Tool | Hotkey | Focus & Capabilities |
|:---|:---:|:---|
| **1. Overview Cockpit** | `1` | 5-System Health Radar, Live 60 FPS Reticle HUD, Multimodal Stress Index with Baseline $\Delta Z$-Score, Active IEC Alarm Banner, and Quick 120s Audio Mute. |
| **2. Cardio-Vitals Panel** | `2` | Continuous ECG trace, HRV Spectrum (rMSSD, SDNN, Baevsky Stress Index, Guyton Respiratory Rate), and Sensor Adapter Mode (Live / Manual / Replay with 4 Scenarios). |
| **3. Neuro-Cognitive Pod** | `3` | Interactive 3-Minute PVT-B Reaction Self Test, Circadian Sleep Pod & Sleep Debt Gauge, Validated Screeners (PHQ-9, GAD-7, PSS-4), and Third-Quarter Trend graph. |
| **4. Cabin Environment** | `4` | ECLSS Atmospheric Gauges ($\text{CO}_2, \text{O}_2$, Pressure, Temp, Noise), Dr. Law 2014 Headache Hazard Curve, and Spaceflight Symptom Triage checklist. |
| **5. Medical Reference** | `5` | Voice-Guided Emergency Checklists (Ammonia Leak, Trauma, Eye Debris), Cited Medical Knowledge Base Search, and Phi-3 Clinical AI Console. |
| **🌙 Night Circadian Mode** | Toggle | One-touch 620 nm red/amber dark theme preserving dark adaptation and circadian rhythm during orbital sleep cycles. |
| **🛡️ BIST Diagnostic Modal** | Header | Automated Built-In Self-Test runner inspecting camera sensors, microphones, bundled neural models, memory, and cryptographic audit hash ledger. |

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        SPACE COCKPIT DISPLAY (REACT 18 + TYPESCRIPT)                   │
│                                                                                        │
│   [Webcam Stream]                                      [Microphone Audio]              │
│          │                                                      │                      │
│          ▼                                                      ▼                      │
│   MediaPipe WASM (60 FPS)                              AudioWorklet (16 kHz PCM)       │
│   - 478-pt Mesh & EAR Ballistics                       - Anti-aliased Resampler        │
│   - 52 FACS Blendshapes (AU12/4/26/15)                 - Rolling VAD Window            │
│   - Aerospace Canvas Reticle HUD                       - RMS VU Ballistics             │
└──────────┬──────────────────────────────────────────────────────┬──────────────────────┘
           │ 6 FPS Face Crop JPEG                                 │ 16 kHz Mono PCM Chunks
           ▼                                                      ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        FASTAPI ASYNCHRONOUS BACKEND SERVICES                           │
│                                                                                        │
│    /ws/video-crop                                          /ws/audio                   │
│          │                                                      │                      │
│          ▼                                                      ▼                      │
│    AffectNet EfficientNet ONNX                             Vosk Kaldi Engine           │
│    + FACS Action Unit Hybridization                        + Phonetic Space Dict       │
│    (Dominant Affect & 7-Class Probs)                       (Fuzzy Intent Matcher)      │
│          │                                                      │                      │
│          └───────────────────────┬──────────────────────────────┘                      │
│                                  ▼                                                     │
│                     M4: Multimodal Fusion Engine                                       │
│                     - Personal Baseline Calibration (Welford M2 Variance)              │
│                     - 1 Hz CUSUM Statistical Change Detection                          │
│                     - Cardio-Respiratory HRV Coupling (rMSSD, SDNN, Baevsky)           │
│                     - Quality-Aware Dynamic Gating & Anti-Flicker EMA                  │
│                                  │                                                     │
│        ┌─────────────────────────┼─────────────────────────┐                           │
│        ▼                         ▼                         ▼                           │
│   IEC 60601-1-8 Alarms     Cabin Environment      Cryptographic Ledger                 │
│   - Priority Queues        - Law 2014 CO2 Model   - SHA-256 Hash Chain                 │
│   - 120s Audio Mute        - ECLSS Symptoms       - SQLite maitri_logs.db              │
│   - 3-Min Escalation       - Triage Protocols     - BIST Diagnostics                   │
│        │                         │                         │                           │
│        └─────────────────────────┼─────────────────────────┘                           │
│                                  ▼                                                     │
│    /ws/telemetry ──────── 10 Hz Bidirectional Telemetry Stream                         │
└────────────────────────────────────────────────────────────────────────────────────────┘
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

### 2. Time-Domain Heart Rate Variability (HRV) & Baevsky Stress Index
Parasympathetic vagal tone and autonomic regulatory tension are computed from $N$ consecutive normal-to-normal RR intervals ($RR_i$ in milliseconds):

$$\text{rMSSD} = \sqrt{\frac{1}{N-1}\sum_{i=1}^{N-1}(RR_{i+1} - RR_i)^2}$$

$$\text{SDNN} = \sqrt{\frac{1}{N}\sum_{i=1}^N (RR_i - \overline{RR})^2}$$

Autonomic balance is quantified using the Soviet/Russian spaceflight gold standard, the **Baevsky Stress Index (SI)**:

$$\text{SI} = \frac{\text{AMo}}{2 \cdot \text{Mo} \cdot \Delta X}$$

where:
* $\text{Mo}$ (Mode) = most frequent RR interval duration in seconds ($0.75\text{–}0.95\text{s}$).
* $\text{AMo}$ (Amplitude of Mode) = percentage of RR intervals matching the mode bin ($30\text{–}50\%$).
* $\Delta X$ (Variational Range) = difference between maximal and minimal RR intervals in seconds ($\text{Max} - \text{Min}$).
* Interpretation: $\text{SI} < 50$ (vagotonia), $50\text{–}150$ (eutonia/nominal), $150\text{–}500$ (sympathetic activation), $>500$ (severe autonomic strain).

### 3. Personal Baselines, Welford Variance & CUSUM Change Detection
To eliminate microgravity cephalic fluid shift ("puffy-face") bias, individual crew baselines calibrate online using Welford's algorithm for numerically stable mean and variance:

$$M_k = M_{k-1} + \frac{x_k - M_{k-1}}{k}, \quad S_k = S_{k-1} + (x_k - M_{k-1})(x_k - M_k), \quad \sigma_k = \sqrt{\frac{S_k}{k-1}}$$

Standardized residuals ($z = \frac{x - \mu}{\sigma}$) feed a two-sided Cumulative Sum (CUSUM) control chart evaluated at 1 Hz ($k = 0.5$, threshold $h = 4.0$):

$$S_i^+ = \max(0, S_{i-1}^+ + (z_i - k)), \quad S_i^- = \max(0, S_{i-1}^- - (z_i + k))$$

A persistent physiological drift alarm triggers when $\max(S_i^+, S_i^-) \ge 4.0$, distinguishing chronic adaptation from momentary acute spikes.

### 4. Spaceflight $\text{CO}_2$ Headache Hazard Model (Law et al., 2014)
Using epidemiological multi-mission regression data from the International Space Station (*Law, J., et al., 2014*), the predicted odds ratio for astronaut headache as a function of ambient carbon dioxide partial pressure is:

$$\text{OR}_{\text{headache}} = \exp\left(0.38 \cdot \left(P_{\text{CO}_2}\text{ [mmHg]} - 2.5\right)\right)$$

* At $2.5\text{ mmHg}$ ($3,300\text{ ppm}$, nominal ISS operational target): $\text{OR} = 1.00$.
* At $3.5\text{ mmHg}$ ($4,600\text{ ppm}$): $\text{OR} = 1.46$ (+46% headache risk).
* At $5.0\text{ mmHg}$ ($6,600\text{ ppm}$, scrub malfunction): $\text{OR} = 2.59$ (+159% headache risk).

### 5. Cosinor Circadian Rhythm Model
Astronaut core temperature and alertness rhythm are modeled using a single-harmonic cosinor function:

$$C(t) = M + A \cos\left(\frac{2\pi(t - \phi)}{24}\right)$$

where $M$ is the mesor (circadian baseline mean), $A$ is the amplitude, and $\phi$ is the acrophase (time of peak alertness, nominal 14:00h). Cumulative sleep debt ($D_{\text{sleep}}$) integrates daily sleep duration ($T_{\text{sleep}}$) against the mandatory 8.0-hour requirement:

$$D_{\text{sleep}}(t) = \max\left(0, D_{\text{sleep}}(t-1) + (8.0 - T_{\text{sleep}})\right)$$

### 6. Cryptographic SHA-256 Tamper-Evident Hash Chain
Every telemetry log entry and clinical alarm event is permanently sealed into an append-only cryptographic chain:

$$H_0 = 0000000000000000000000000000000000000000000000000000000000000000$$

$$H_n = \text{SHA-256}\left(H_{n-1} \,\|\, \tau_n \,\|\, \text{CanonicalPayload}_n\right)$$

Any unauthorized modification of historical stress scores, emotion probabilities, or alarm acknowledgment timestamps invalidates the hash chain and pinpoints the exact tampered record ID.

---

## 🎙️ Offline Voice Command Control Reference

All voice commands execute entirely offline via local Kaldi Vosk ASR with spoken talkback synthesized by Piper neural TTS:

| Intent Category | Spoken Utterances & Synonyms | Dispatched Action & Neural Talkback |
|:---|:---|:---|
| **Overview Tab** | `"Maitri, open live feed"`, `"overview"`, `"cockpit"`, `"tab 1"` | Switches to View 1; *"Switching to overview cockpit."* |
| **Cardio Panel** | `"Maitri, show cardio"`, `"cardio vitals"`, `"hrv spectrum"`, `"tab 2"` | Switches to View 2; *"Opening cardio-respiratory panel."* |
| **Neuro Pod** | `"Maitri, open neuro"`, `"cognitive test"`, `"circadian"`, `"tab 3"` | Switches to View 3; *"Opening neuro-cognitive and circadian pod."* |
| **Cabin ECLSS** | `"Maitri, cabin environment"`, `"show atmosphere"`, `"co2 levels"`, `"tab 4"` | Switches to View 4; *"Opening cabin environmental monitor."* |
| **Medical Reference** | `"Maitri, medical reference"`, `"emergency checklist"`, `"tab 5"` | Switches to View 5; *"Opening medical reference library."* |
| **Telemetry History** | `"Maitri, show logs"`, `"mission logs"`, `"database"` | Switches to Historical Audit Logs; *"Opening mission telemetry logs."* |
| **PVT Test Control** | `"Maitri, start pvt test"`, `"reaction test"`, `"stop pvt"` | Controls 3-min reaction test; *"Starting PVT test."* / *"PVT test stopped."* |
| **Depression Check** | `"Maitri, start depression check"`, `"phq nine"`, `"mental health"` | Opens PHQ-9 Screener; *"Starting PHQ-9 screener."* |
| **Anxiety Check** | `"Maitri, start anxiety check"`, `"gad seven"` | Opens GAD-7 Screener; *"Starting GAD-7 screener."* |
| **Ammonia Checklist** | `"Maitri, checklist ammonia"`, `"ammonia leak"` | Opens Ammonia Procedure; *"Opening Ammonia Emergency Checklist."* |
| **Trauma Checklist** | `"Maitri, checklist trauma"`, `"acute injury"` | Opens Trauma Procedure; *"Opening Acute Trauma Checklist."* |
| **Eye Checklist** | `"Maitri, checklist eye"`, `"ocular foreign body"` | Opens Eye Procedure; *"Opening Ocular Emergency Checklist."* |
| **Mute Alarms** | `"Maitri, mute alarms"`, `"pause alarm audio"`, `"silence"` | Pauses IEC alarm audio 120s; *"Alarm audio paused for 120 seconds."* |
| **Acknowledge Alarms**| `"Maitri, acknowledge alarms"`, `"clear alarms"` | Acknowledges active alarms; *"Alarms acknowledged."* |
| **Night Shift Mode** | `"Maitri, toggle night mode"`, `"circadian mode"`, `"red lighting"` | Switches to 620 nm red spectrum; *"Toggling circadian night mode."* |
| **Read Vitals** | `"Maitri, read vitals"`, `"what are my vitals"` | Reads heart rate, oxygen, and HRV; *"Current heart rate is X. Oxygen is Y."* |
| **Read Stress** | `"Maitri, show stress"`, `"what is my stress level"` | Reads multimodal index; *"Stress index is X percent, status [NOMINAL/CRITICAL]."* |
| **Set Heart Rate** | `"Maitri, set heart rate to eighty five"` | Updates cardiac telemetry; *"Heart rate set to 85 beats per minute."* |
| **Set Blood Oxygen** | `"Maitri, set oxygen to ninety six"` | Updates pulse oximetry; *"Blood oxygen set to 96 percent."* |
| **Grounding Cycle** | `"Maitri, start breathing exercise"`, `"initiate grounding"` | Triggers 4-7-8 breathing; *"Initiating 4-7-8 breathing protocol."* |
| **Watchdog Ack** | `"Maitri, acknowledge watchdog"`, `"i am okay"` | Resets dead-man timer; *"Watchdog presence acknowledged."* |
| **Critical Override** | `"Maitri, override incapacitation"` | **Safety Challenge:** *"Safety confirmation required. Say 'Confirm override'."* |
| **Confirm Action** | `"Maitri, confirm override"` | Authorizes override; *"Incapacitation override confirmed. Systems nominal."* |

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

### 4. Build the React Cockpit (Pre-compiled bundle included in `frontend/dist/`)
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

MAITRI 2.0 includes an exhaustive automated test suite covering full-stack REST contracts, WebSocket synchronization, ONNX inference, FACS geometric fusion, Vosk Kaldi speech recognition, personal baseline CUSUM tracking, HRV calculations, PVT-B scoring, psychometrics, and cryptographic hash chaining:

```bash
# Execute the full 254-test automated test suite
python -m pytest tests/ -v
```

### Test Subsystem Breakdown

| Test Suite | Scope | Tests | Result |
|:---|:---|:---:|:---:|
| `tests/backend/test_full_stack_verification.py` | FastAPI lifespan, air-gapped asset integrity, zero-CDN validation | 7 | **PASS** |
| `tests/backend/test_intent_parser.py` | Fuzzy Levenshtein, number parsing, entity extraction, safety confirmation | 36 | **PASS** |
| `tests/backend/test_rest_api.py` | REST endpoints (`/api/logs`, `/api/psych`, `/api/mission`, `/api/watchdog`) | 32 | **PASS** |
| `tests/backend/test_vision_service.py` | AffectNet ONNX inference, FACS Action Units fusion (AU12/AU4/AU26/AU15) | 9 | **PASS** |
| `tests/backend/test_voice_service.py` | 16 kHz PCM buffering, RMS calculations, speech state detection | 6 | **PASS** |
| `tests/backend/test_voice_wav_intent.py` | End-to-end WAV speech recognition, spoken number parsing, Kaldi intents | 6 | **PASS** |
| `tests/backend/test_ws_telemetry.py` | Bidirectional WebSocket telemetry streaming and client commands | 12 | **PASS** |
| `tests/test_clinical_core.py` | HRV metrics (rMSSD, SDNN, Baevsky), personal baseline CUSUM, IEC alarms, SHA-256 audit chaining | 38 | **PASS** |
| `tests/test_clinical_extended.py` | PVT-B vigilance engine, sleep debt cosinor model, PHQ-9/GAD-7/PSS-4, Law 2014 CO2 model, BIST diagnostics | 23 | **PASS** |
| `tests/test_live_and_onnx_pipeline.py` | OpenCV pipeline, face bounding box isotropic crop & DIP clarity | 10 | **PASS** |
| `tests/test_voice_and_fusion.py` | Multimodal EMA temporal fusion, vitals strain & alert engine | 27 | **PASS** |
| `tests/test_phase2_extended.py` | Phi-3 LLM grounding, context presets & prompt engineering | 22 | **PASS** |
| `tests/test_standalone_verification.py` | Isolated module validation and error resilience | 13 | **PASS** |
| `tests/test_edge_cases.py` | Motion blur, face occlusion, low light, microphone silence | 8 | **PASS** |
| `tests/test_decoupled_pipeline.py` | Decoupled background workers and multi-threading safety | 4 | **PASS** |
| `tests/test_phase2_e2e.py` | Complete end-to-end Phase 2 clinical intelligence integration | 1 | **PASS** |
| **TOTAL** | **Full System Flight Certification Matrix** | **254** | **100% PASS** |

---

## 🎨 Design System & Color Tokens (WCAG 2.2 AA)

Every clinical status color is paired with a distinct geometric icon and explicit text label to satisfy WCAG 2.2 SC 1.4.1 (Color Independence):

| Clinical Tier | HEX Code | Tailwind Token | Redundant Geometric Shape | IEC 60601-1-8 & Clinical Meaning |
|:---:|:---:|:---|:---:|:---|
| **NOMINAL** | `#00E676` | `text-emerald-400 bg-emerald-500/15 border-emerald-500/30` | **Circle (●)** | All parameters within $\pm 1.5\sigma$ of astronaut's baseline. |
| **ADVISORY (LOW)** | `#00E5FF` | `text-cyan-400 bg-cyan-500/15 border-cyan-500/30` | **Diamond (◆)** | Minor sensor drift or informational advisory; operator awareness only. |
| **CAUTION (MEDIUM)** | `#FFB300` | `text-amber-400 bg-amber-500/15 border-amber-500/30` | **Triangle (▲)** | Moderate strain (Stress 50–70%, $\text{CO}_2 > 3.0\text{ mmHg}$, or HRV drop $>30\%$). Prompt response required. |
| **WARNING (HIGH)** | `#FF1744` | `text-rose-400 bg-rose-500/20 border-rose-500/50` | **Octagon (⯄)** | Acute life/mission threat (Hypoxia $\text{SpO}_2<90\%$, severe arrhythmia, toxic leak). Immediate action required. |

---

## 🛡️ Flight Certification & Air-Gapped Security

* **Zero Cloud Dependence:** No CDNs, no remote fonts (`@fontsource` self-hosted), no external APIs.
* **Hardware Resilience:** Gracefully degrades across absent webcams, lost microphone permissions, and CPU throttling.
* **Deterministic Fallbacks:** Fallback from ONNX to FACS geometric rules, and standalone Piper TTS synthesis ensuring voice talkback is never lost.
* **Tamper-Evident Security:** All database tables sealed with continuous SHA-256 hash chaining detecting unauthorized modifications.
* **Backward Compatibility:** Original Streamlit dashboard remains 100% intact and functional via `streamlit run app.py`.

---

<div align="center">

**Developed with Pride for Human Spaceflight Research**  
*Project MAITRI 2.0 — Annasaheb Dange College of Engineering and Technology, Ashta*

</div>
