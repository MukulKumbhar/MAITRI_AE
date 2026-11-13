"""
MAITRI 2.0 — Curated Local Clinical Knowledge Base & Emergency Checklists
Offline Aerospace Medicine Reference Library with Verified PubMed and NASA Citations.

Grounds Phi-3-Mini to answer solely from validated spacecraft clinical knowledge
and explicitly refuse queries outside its local aerospace health scope.

References:
- NASA-STD-3001: NASA Space Flight Human-System Standard, Vol 1 & 2.
- Law J, Watkins S, Alexander D. J Occup Environ Med. 2014;56(5):477-483.
- Mader TH, et al. Ophthalmology. 2011;118(10):2058-2069.
- Barger LK, et al. Lancet Neurol. 2014;13(9):904-912.
- ISS Flight Operations Manual: Section 14 Emergency Protocols.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


# ── Decision Support Disclaimer ───────────────────────────────────────────────
DECISION_SUPPORT_NOTICE = (
    "CLINICAL DECISION SUPPORT NOTICE: MAITRI is an autonomous onboard decision "
    "support tool for crewed spaceflight, NOT an automated diagnostic medical device. "
    "All recommendations must be corroborated by the Crew Medical Officer (CMO) "
    "or Mission Control Flight Surgeon."
)

EXPLICIT_REFUSAL_MESSAGE = (
    "I am restricted to verified spacecraft clinical references and cannot diagnose, "
    "speculate, or advise outside my curated local aerospace knowledge base. "
    "Please consult the Flight Surgeon or Crew Medical Officer via DTN telemetry outbox."
)


# ── Curated Knowledge Base Articles ───────────────────────────────────────────
MEDICAL_ARTICLES: List[Dict[str, Any]] = [
    {
        "id": "KB_CO2_HYPERCAPNIA",
        "title": "Cabin Hypercapnia & Headache Hazard in Microgravity",
        "category": "Environmental Physiology",
        "keywords": ["co2", "carbon dioxide", "headache", "headaches", "hypercapnia", "scrubber", "law", "eclss", "ppm", "mmhg"],
        "citations": [
            "Law J, Watkins S, Alexander D. Relationship Between Carbon Dioxide Levels and Reported Headaches on the International Space Station. J Occup Environ Med. 2014;56(5):477-483. PMID: 24806563.",
            "NASA-STD-3001 Vol 2, Rev C: Section 6.2 Atmospheric Quality (CO2 limits).",
        ],
        "summary": (
            "In microgravity, absence of convective air currents allows localized pockets of expired CO2 to form "
            "around crew heads. Crew members exhibit doubled odds of reporting headaches for each 1 mm Hg increase "
            "in ambient PCO2 (Law et al. 2014). ISS operational limits maintain PCO2 < 3.0-4.0 mmHg."
        ),
        "clinical_management": (
            "1. Verify localized ventilation airflow (>15-40 ft/min) to dissipate stagnant CO2 pockets.\n"
            "2. Switch redundant ECLSS CO2 scrubbers (CDRA / METOX) to high-throughput desorption mode.\n"
            "3. Administer oral acetaminophen (650-1000 mg) or ibuprofen (400-600 mg) with water for acute cephalalgia.\n"
            "4. Monitor crew for somnolence, dyspnea, and cognitive slowing; execute cabin atmosphere grab sample."
        ),
    },
    {
        "id": "KB_SANS",
        "title": "Spaceflight Associated Neuro-ocular Syndrome (SANS)",
        "category": "Ophthalmic & Neurological",
        "keywords": ["sans", "vision", "eye", "eyes", "papilledema", "optic disc", "optic nerve", "choroidal folds", "hyperopic", "blur"],
        "citations": [
            "Mader TH, Gibson CR, Pass AF, et al. Optic disc edema, globe flattening, choroidal folds, and hyperopic shifts observed in astronauts after long-duration space flight. Ophthalmology. 2011;118(10):2058-2069. PMID: 21684605.",
            "Lee AG, Mader TH, Gibson CR, et al. Space flight-associated neuro-ocular syndrome (SANS). JAMA Ophthalmol. 2018;136(4):428-430.",
        ],
        "summary": (
            "SANS is characterized by unilateral or bilateral optic disc edema, globe flattening, choroidal folds, "
            "cotton wool spots, and hyperopic refractive shifts during long-duration spaceflight. Cephalad fluid shift "
            "and altered translaminar cribrosa pressure gradient are primary hypothesized etiologies."
        ),
        "clinical_management": (
            "1. Perform weekly optical coherence tomography (OCT) and fundoscopic retinal imaging.\n"
            "2. Assess visual acuity using logarithmic Snellen charts; provide adjustable 'Space Anticipation Glasses'.\n"
            "3. Utilize Lower Body Negative Pressure (LBNP) countermeasure protocols (20-30 mmHg for 2 hours daily) to redistribute fluid caudally.\n"
            "4. Monitor for secondary visual obscurations or scotomas; report changes to Flight Surgeon."
        ),
    },
    {
        "id": "KB_SMS",
        "title": "Space Motion Sickness (SMS) & Neurovestibular Adaptation",
        "category": "Neurovestibular",
        "keywords": ["sms", "motion sickness", "nausea", "vomiting", "vestibular", "dizzy", "dizziness", "neurovestibular", "adaptation", "otolith"],
        "citations": [
            "Oman CM, Lichtenberg BK, Money KE. Space motion sickness monitoring experiment: Spacelab 1. Science. 1986;231(4740):534-540.",
            "Reschke MF, Bloomberg JJ, Harm DL, et al. Posture and locomotion in astronauts. Brain Res Rev. 1998;28(1-2):102-116.",
        ],
        "summary": (
            "Affects 60-70% of crew during the first 48 to 72 hours of microgravity transition due to sensory conflict "
            "between visual, semicircular canal, and otolith signals. Characterized by stomach awareness, pallor, cold sweating, nausea, and emesis."
        ),
        "clinical_management": (
            "1. Limit abrupt head pitch and roll angular accelerations during initial 72 hours.\n"
            "2. Promethazine 25-50 mg IM or oral as first-line antiemetic countermeasure.\n"
            "3. Maintain hydration and electrolyte balance with oral rehydration solution.\n"
            "4. Delay non-critical EVA or complex procedural tasks until neurovestibular adaptation is established."
        ),
    },
    {
        "id": "KB_CIRCADIAN_SLEEP",
        "title": "Circadian Desynchrony & Sleep Deprivation in Microgravity",
        "category": "Circadian & Sleep",
        "keywords": ["sleep", "circadian", "insomnia", "fatigue", "melatonin", "light", "orbital cycle", "desynchrony", "rest"],
        "citations": [
            "Barger LK, Flynn-Evans EE, Kubey A, et al. Prevalence of sleep deficiency and pharmacotherapy use in astronauts. Lancet Neurol. 2014;13(9):904-912. PMID: 25113969.",
            "Van Dongen HPA, Maislin G, Mullington JM, Dinges DF. Sleep. 2003;26(2):117-126.",
        ],
        "summary": (
            "Astronauts average <6 hours of sleep per night in orbit due to environmental noise, microgravity posture "
            "discomfort, circadian disruption from 16 orbital sunrises daily, and mission stress. Cumulative sleep debt "
            "produces linear degradation in psychomotor vigilance and executive function."
        ),
        "clinical_management": (
            "1. Enforce strict 8.5-hour scheduled crew sleep opportunity in acoustic crew quarters.\n"
            "2. Utilize Dynamic Solid-State Lighting Assemblies (SSLA): blue-enriched morning light (>480nm) and blue-depleted evening light (<10 lux, 2700K).\n"
            "3. Conduct daily 3-minute PVT-B self-tests to monitor reaction time lapses (>355ms).\n"
            "4. Pharmacological adjuncts: Zolpidem (5-10 mg) or Melatonin (0.5-3.0 mg) timed 30 min before target sleep window."
        ),
    },
    {
        "id": "KB_DCS",
        "title": "Hypobaric Decompression Sickness (DCS) in EVA Operations",
        "category": "Operational Medicine",
        "keywords": ["dcs", "decompression", "bends", "eva", "suit", "nitrogen", "prebreathe", "hypobaric", "joint pain"],
        "citations": [
            "Conkin J, Gernhardt ML, Powell MR, Pollock NW. A probability model of decompression sickness in astronauts. Aviat Space Environ Med. 2004;75(10):871-881. PMID: 15497367.",
            "NASA TP-2017-219290: Decompression Sickness Risk Assessment for Exploration EVA.",
        ],
        "summary": (
            "Transition from 14.7 psi cabin pressure to 4.3 psi (or 8.2 psi Exploration EMU) suit pressure creates "
            "risk of inert nitrogen bubble formation in joints (bends), cutaneous capillaries (chokes), or central nervous system."
        ),
        "clinical_management": (
            "1. Complete mandatory 100% O2 pre-breathe protocol (e.g. 2-hour in-suit or campout protocol) before EVA hatch egress.\n"
            "2. If DCS joint pain or neurological deficits arise: immediately terminate EVA and repressurize airlock to 14.7 psi.\n"
            "3. Administer 100% O2 via aviator mask; initiate in-suit hyperbaric treatment protocol (Overpressurize suit to 8.0 psid).\n"
            "4. Keep crew recumbent; hydrate orally or IV to prevent circulatory hypovolemia."
        ),
    },
    {
        "id": "KB_RADIATION",
        "title": "Space Radiation Exposure & Solar Particle Event (SPE) Triage",
        "category": "Radiation Health",
        "keywords": ["radiation", "spe", "solar flare", "particle", "gcr", "dose", "sievert", "dosimeter", "storm shelter"],
        "citations": [
            "Cucinotta FA, Kim MY, Chappell LJ, Huff JL. How safe is safe enough? Radiation risk for a human mission to Mars. PLoS One. 2013;8(10):e74988. PMID: 24146746.",
            "NCRP Report No. 153: Information for Regulating Space Radiation Exposure to Astronauts.",
        ],
        "summary": (
            "Galactic Cosmic Rays (GCR) and Solar Particle Events (SPE) pose acute and chronic health hazards. "
            "Acute doses exceeding 250-500 mGy produce Acute Radiation Syndrome (ARS) prodromal nausea, fatigue, "
            "and hematopoietic lymphopenia. Crew career limits follow NASA REID <3% standards."
        ),
        "clinical_management": (
            "1. Upon automated SPE alarm trigger, immediately ingress designated storm shelter (central water-shielded module).\n"
            "2. Read personal and area passive/active dosimeters (RAD / Tissue Equivalent Proportional Counter).\n"
            "3. Administer prophylactic antiemetic (ondansetron 8 mg or promethazine 25 mg) if acute prodromal symptoms develop.\n"
            "4. Monitor absolute neutrophil and lymphocyte counts daily via onboard capillary blood analyzer."
        ),
    },
    {
        "id": "KB_PSYCH_ISOLATION",
        "title": "Behavioral Health, Confinement & Third-Quarter Effect",
        "category": "Behavioral Health",
        "keywords": ["psychology", "isolation", "confinement", "third-quarter", "depression", "anxiety", "mood", "conflict", "ice"],
        "citations": [
            "Bechtel RB, Berning A. The third-quarter phenomenon in isolated environments. Environ Behav. 1991;23(4):460-478.",
            "Kanas N, et al. Psychological characteristics of crew members during ISS missions. Aviat Space Environ Med. 2006;77(10):1083-1090. PMID: 17042588.",
        ],
        "summary": (
            "Long-duration isolated and confined extreme (ICE) space missions demonstrate vulnerability to asthenic syndrome, "
            "interpersonal friction, displacement of hostility onto ground control, and third-quarter mood/morale decrements."
        ),
        "clinical_management": (
            "1. Administer monthly validated psychometric screeners (PHQ-9, GAD-7, PSS-4).\n"
            "2. Provide weekly private psychological communications (PPC) with family and flight psychologist.\n"
            "3. Deploy Cognitive Behavioral Therapy (CBT) modules, 4-7-8 rhythmic breathing, and sensory enrichment (music, aroma, botanical growth).\n"
            "4. Safety gate: Any affirmative response to PHQ-9 Item 9 triggers immediate confidential CMO / Flight Surgeon direct link."
        ),
    },
]


# ── Emergency Step-by-Step Checklists ─────────────────────────────────────────
EMERGENCY_CHECKLISTS: Dict[str, Dict[str, Any]] = {
    "checklist_ammonia": {
        "id": "checklist_ammonia",
        "title": "Ammonia Leak Emergency Protocol (ECLSS / Thermal)",
        "priority": "CRITICAL",
        "source": "ISS Flight Operations Manual Section 14.2 / Emergency Checklist 1.101",
        "steps": [
            {
                "step_number": 1,
                "action": "DON EMERGENCY OXYGEN MASK",
                "instruction": "Immediately don Emergency Mask or Quick-Don O2 Mask on 100% emergency delivery. Do not inhale cabin atmosphere.",
                "critical": True,
            },
            {
                "step_number": 2,
                "action": "INGRESS SAFE HAVEN MODULE",
                "instruction": "Transit immediately to designated safe haven module (Russian Segment / Node 3 sealed compartment) and seal inter-module hatch.",
                "critical": True,
            },
            {
                "step_number": 3,
                "action": "VERIFY HATCH PRESSURE SEAL",
                "instruction": "Equalize and lock hatch dogs. Confirm delta-P gauge indicates positive pressure barrier against isolated contaminated section.",
                "critical": True,
            },
            {
                "step_number": 4,
                "action": "INITIATE ECLSS AMMONIA SCRUBBING",
                "instruction": "Activate Ammonia Scrubber Kits and configure environmental trace contaminant control (TCCS) to maximum catalytic scrub rate.",
                "critical": False,
            },
            {
                "step_number": 5,
                "action": "SKIN & OCULAR DECONTAMINATION",
                "instruction": "If liquid or vapor ammonia contacted crew eyes or skin, flush immediately with sterile water for minimum 15 continuous minutes.",
                "critical": True,
            },
            {
                "step_number": 6,
                "action": "ESTABLISH EMERGENCY DTN LINK",
                "instruction": "Contact Mission Control / Flight Surgeon via emergency communications loop. Await atmospheric Draeger tube clearance before hatch re-opening.",
                "critical": False,
            },
        ],
    },
    "checklist_trauma": {
        "id": "checklist_trauma",
        "title": "Acute Microgravity Hemorrhage & Trauma Protocol",
        "priority": "CRITICAL",
        "source": "NASA Crew Medical Officer Handbook / Advanced Trauma Life Support in Space",
        "steps": [
            {
                "step_number": 1,
                "action": "APPLY DIRECT PRESSURE & MICROGRAVITY GAUZE",
                "instruction": "Apply direct firm pressure over wound using sterile hemostatic combat gauze (QuikClot). Restrain free-floating blood droplets with suction.",
                "critical": True,
            },
            {
                "step_number": 2,
                "action": "APPLY TOURNIQUET IF MASSIVE EXTREMITY BLEEDING",
                "instruction": "If arterial hemorrhage persists on extremity, place Combat Application Tourniquet (CAT) 2-3 inches proximal to injury site; tighten until bleeding ceases.",
                "critical": True,
            },
            {
                "step_number": 3,
                "action": "STABILIZE CERVICAL SPINE & CREW RESTRAINT",
                "instruction": "Secure injured astronaut to Crew Medical Restraint System (CMRS) with 3-point harness to prevent kinematic drift during resuscitation.",
                "critical": False,
            },
            {
                "step_number": 4,
                "action": "ATTACH CARDIO-RESPIRATORY TELEMETRY",
                "instruction": "Attach Lead-II ECG electrodes and finger reflectance pulse oximeter. Verify heart rate, SpO2, and blood pressure via automated cuff.",
                "critical": False,
            },
            {
                "step_number": 5,
                "action": "ESTABLISH VASCULAR ACCESS IF HYPOVOLEMIC",
                "instruction": "If HR > 120 BPM or systolic BP < 90 mmHg (hypovolemic shock), place 18G peripheral IV or sternal intraosseous (IO) line. Administer warm IV normal saline bolus.",
                "critical": True,
            },
            {
                "step_number": 6,
                "action": "INITIATE TELEMEDICINE SURGICAL UPLINK",
                "instruction": "Open high-definition video telemedicine feed to Mission Control Houston / Flight Surgeon surgical team. Await surgical consultation.",
                "critical": False,
            },
        ],
    },
    "checklist_ocular_debris": {
        "id": "checklist_ocular_debris",
        "title": "Ocular Foreign Body & Corneal Debris Protocol",
        "priority": "MEDIUM",
        "source": "NASA Medical Operations Protocol 4.12 / Ophthalmic Emergency Procedures",
        "steps": [
            {
                "step_number": 1,
                "action": "INSTRUCT CREW: DO NOT RUB EYE",
                "instruction": "Strictly instruct patient NOT to rub affected eye. Microgravity particulate matter (metal shavings, skin flakes, food dust) creates high risk of corneal laceration.",
                "critical": True,
            },
            {
                "step_number": 2,
                "action": "POSITION CREW IN EXHAUST SLIPSTREAM",
                "instruction": "Position patient near cabin HEPA intake grille so free-floating debris drifts away from the orbital face.",
                "critical": False,
            },
            {
                "step_number": 3,
                "action": "IRRIGATE EYE WITH STERILE SALINE",
                "instruction": "Utilize Eye Irrigation Kit (Morgan Lens or saline syringe with soft catheter). Irrigate affected eye with 250-500 mL sterile saline from inner to outer canthus.",
                "critical": True,
            },
            {
                "step_number": 4,
                "action": "FLUORESCEIN STAINING & COBALT BLUE EXAM",
                "instruction": "Moisten fluorescein strip with saline and touch lower conjunctival sac. Inspect cornea using ophthalmoscope under cobalt blue filter for epithelial abrasion.",
                "critical": False,
            },
            {
                "step_number": 5,
                "action": "APPLY TOPICAL OPHTHALMIC ANTIBIOTIC",
                "instruction": "Instill 1 drop of 0.3% ciprofloxacin or erythromycin ophthalmic ointment into conjunctival fornix to prevent bacterial keratitis.",
                "critical": False,
            },
            {
                "step_number": 6,
                "action": "SECURE FOX EYE SHIELD & DOCUMENT ACUITY",
                "instruction": "Tape rigid perforated Fox eye shield over eye without pressure. Measure and log visual acuity in DTN medical log.",
                "critical": False,
            },
        ],
    },
}


# ── Search & Knowledge Retrieval Interface ───────────────────────────────────

STOP_WORDS = {
    "a", "about", "an", "and", "are", "as", "at", "be", "by", "can", "could",
    "do", "does", "for", "from", "have", "having", "how", "i", "if", "in", "is",
    "it", "me", "my", "no", "not", "of", "on", "or", "our", "should", "so", "that",
    "the", "this", "to", "use", "was", "we", "were", "what", "when", "where", "which",
    "who", "why", "will", "with", "would", "you", "your",
}


def search_medical_knowledge(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search the curated clinical reference library using token overlap and keyword matching.
    Filters out common stop words to prevent false-positive matches on general English terms.
    """
    raw_tokens = set(re.findall(r"\w+", query.lower()))
    query_tokens = {t for t in raw_tokens if t not in STOP_WORDS and len(t) >= 2}
    if not query_tokens:
        return []

    scored_articles = []
    for art in MEDICAL_ARTICLES:
        score = 0
        art_keywords = set(k.lower() for k in art["keywords"])
        art_title_tokens = set(re.findall(r"\w+", art["title"].lower())) - STOP_WORDS
        art_summary_tokens = set(re.findall(r"\w+", art["summary"].lower())) - STOP_WORDS

        kw_matches = query_tokens & art_keywords
        title_matches = query_tokens & art_title_tokens
        summary_matches = query_tokens & art_summary_tokens

        # Direct keyword matches weighted highest
        score += len(kw_matches) * 6
        score += len(title_matches) * 4
        score += len(summary_matches) * 1

        # Only count articles that actually match a designated topic keyword or title term
        if (kw_matches or title_matches) and score >= 4:
            scored_articles.append((score, art))

    scored_articles.sort(key=lambda x: x[0], reverse=True)
    return [art for _, art in scored_articles[:max_results]]


def get_emergency_checklist(checklist_id: str) -> Optional[Dict[str, Any]]:
    """Return emergency checklist by ID (e.g. 'checklist_ammonia', 'checklist_trauma')."""
    return EMERGENCY_CHECKLISTS.get(checklist_id.lower().strip())


def get_all_emergency_checklists() -> List[Dict[str, Any]]:
    """Return list of all available emergency checklists."""
    return list(EMERGENCY_CHECKLISTS.values())


def is_medical_inquiry(text: str) -> bool:
    """
    Checks if a query contains clinical, diagnostic, symptom, or treatment inquiries.
    """
    t = text.lower()
    clinical_markers = [
        "diagnos", "symptom", "treatment", "prescribe", "prescription", "disease",
        "illness", "pathology", "medication", "medicine", "drug", "cure", "therapy",
        "headache", "dizz", "nausea", "vomit", "bleeding", "wound", "trauma",
        "ammonia", "vision", "eye", "sans", "co2", "hypercapnia", "decompression",
        "bends", "radiation", "spe", "solar flare", "pain", "dose", "cancer",
        "diabetes", "fever", "cough", "fracture", "hypoxia"
    ]
    return any(marker in t for marker in clinical_markers)


def is_query_in_scope(query: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Determines if an astronaut inquiry falls within the validated aerospace clinical scope.
    Returns (in_scope, matched_primary_article).
    """
    matches = search_medical_knowledge(query, max_results=1)
    if matches:
        return True, matches[0]

    # Check emergency checklists
    q_lower = query.lower()
    for cl_id, cl in EMERGENCY_CHECKLISTS.items():
        if any(term in q_lower for term in [cl_id, cl["title"].lower(), "ammonia", "trauma", "bleeding", "debris", "foreign body"]):
            return True, {
                "id": cl["id"],
                "title": cl["title"],
                "citations": [cl["source"]],
                "summary": f"Emergency operational checklist for {cl['title']}.",
                "clinical_management": "\n".join(f"{s['step_number']}. {s['action']}: {s['instruction']}" for s in cl["steps"]),
            }

    return False, None


def get_curated_grounding_context(query: str) -> Tuple[str, bool]:
    """
    Returns structured aerospace clinical grounding text for LLM prompting.
    If the query is out of scope, returns explicit refusal text and in_scope=False.
    """
    in_scope, matched = is_query_in_scope(query)
    if not in_scope or not matched:
        return EXPLICIT_REFUSAL_MESSAGE, False

    citations_str = "\n".join(f"- {c}" for c in matched.get("citations", []))
    context = (
        f"Verified Aerospace Clinical Reference: {matched.get('title')}\n"
        f"Citations:\n{citations_str}\n\n"
        f"Clinical Evidence Summary:\n{matched.get('summary')}\n\n"
        f"Approved Clinical Management Protocol:\n{matched.get('clinical_management')}\n\n"
        f"{DECISION_SUPPORT_NOTICE}"
    )
    return context, True
