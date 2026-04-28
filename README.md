# Heidi Clinical Decision Support

**Candidate:** David London — HBSc CS, MScPT, PT (Registered Physiotherapist + Computer Scientist)
**Role:** Medical AI Specialist — Heidi Health
**Submission:** Technical Take-Home Assignment

---

## Live Demo

https://heidi-assistant-demo.streamlit.app

Select a jurisdiction in the sidebar before submitting a note. No setup required.

---

## What This Is

An agentic, jurisdiction-aware clinical decision support assistant that surfaces evidence-aligned treatment recommendations within the flow of care.

The system addresses the three problems in the brief:

1. **Guidelines vary across regions and hospitals** — explicit jurisdiction selection enforced at the tool level. The same 14kg child with moderate croup receives 8.4mg at CHEO Ottawa, 4.2mg at RCH Melbourne, and 2.1mg at NICE UK. Different doses because the guidelines are genuinely different.

2. **Clinicians face cognitive load** — a conversational agent reads the clinical note, identifies what is relevant, asks for what is missing, and returns a focused recommendation grounded in a specific named guideline version.

3. **Heidi as an intelligent assistant in the flow of care** — Claude orchestrates 14 deterministic clinical tools in real time. Every dose calculation, every safety check, every guideline lookup is auditable and cited.

---

## Two Fundamental Design Principles

**1. Agentic orchestration, deterministic execution.**
Claude decides which tools to call. Code does the calculation. A dose calculation done by Claude from its training data is an AI guess that could vary between runs. A dose calculation done by a Python function keyed to a specific guideline version is the same answer every time.

**2. Explicit over implicit for safety-critical context.**
Every safety-critical decision is visible — which jurisdiction is active, which guideline was used, which version, which dose rule applied. Nothing is assumed silently. If jurisdiction is not set, the system refuses. If weight is missing, the system asks.

---

## Three Safety Gates

| Gate | Location | What it enforces |
|---|---|---|
| Gate 1 — Jurisdiction | tools/jurisdiction.py + UI | Analyse note button disabled until jurisdiction set. Tool-level refusal if bypassed. |
| Gate 2 — Drug class safety | tools/drug_class_safety.py | Required context (weight, age, allergies, current medications) gathered before any dose calculation. Agent stops and asks if missing. |
| Gate 3 — Dose calculator | tools/dose_calculator.py | Deterministic Python, no AI. Same input always produces same output. Refuses without weight, age, severity, jurisdiction. |

---

## Jurisdiction Variance

Same patient (14kg child, moderate croup), different institutions, different doses:

| Jurisdiction | Guideline | mg/kg | Dose |
|---|---|---|---|
| RCH Melbourne | Croup v3.2 | 0.30 | 4.2mg oral |
| CHEO Ottawa | Croup Pathway v2.1 | 0.60 | 8.4mg oral |
| NICE UK | CKS Croup 2023 | 0.15 | 2.1mg oral |

---

## Using the Live App

**Step 1 — Set jurisdiction**
Select your institution in the left sidebar. The Analyse note button is disabled until jurisdiction is set.

**Step 2 — Paste a clinical note**
Paste any clinical note into the text area on the left, or use one of the four quick example buttons.

**Step 3 — Analyse**
Click Analyse note. The agent runs through the full tool chain and returns a recommendation with guideline citation and jurisdiction footer.

**Step 4 — Follow up**
Ask follow-up questions in the chat input. The agent maintains conversation history for the session.

### Demo Notes to Try

**Moderate croup — set jurisdiction to CAN_CHEO_OTTAWA:**
```
Patient: 3yo, weight 14kg
Presents with 2-day barky cough and hoarse voice. Stridor at rest
this morning with mild suprasternal and intercostal recession.
RR 32, HR 124, SpO2 97% room air, T 37.9C.
Clear air entry bilaterally. No cyanosis.
No known drug allergies. No current medications.
Assessment: Moderate viral croup.
```

**Switch jurisdiction to UK_NICE and re-analyse the same note.**
Dose changes from 8.4mg to 2.1mg. Same patient, different guideline, different dose.

**Adult hypertension — set jurisdiction to UK_NICE:**
```
Patient: 58yo male
Stage 1 hypertension confirmed on ABPM (average 148/92).
No history of CKD, diabetes, or cardiovascular disease.
Current medications: ibuprofen 400mg PRN for knee osteoarthritis.
No known drug allergies.
Assessment: Considering starting antihypertensive therapy.
```

**Safety gate demo — jurisdiction set, incomplete note:**
```
Child with barky cough and stridor at rest. Moderate croup.
No allergies. No current medications. What is the dose?
```
Agent stops and asks for weight and age before proceeding. No dose given.

**Anaphylaxis emergency — set jurisdiction to INTERNATIONAL:**
```
Adult patient approx 35yo. Collapsed 10 minutes after eating
at a restaurant. Urticaria over trunk and arms, tongue swelling,
audible stridor developing. BP 75/45, HR 132, SpO2 93%.
Suspected anaphylaxis. Known nut allergy documented in records.
```

---

## Local Setup (macOS, under 10 minutes)

```bash
git clone https://github.com/LondonZone/heidi-assistant.git
cd heidi-assistant
pip3 install anthropic python-dotenv streamlit
cp .env.example .env
nano .env   # paste your Anthropic API key, Ctrl+X to save
streamlit run streamlit_chat.py
```

Opens at http://localhost:8501

---

## Running the Tests

### End-to-end scenario tests (requires API key, costs approx $0.15)

```bash
python3 tests/test_scenarios.py
```

Six full agent turns:

| Scenario | What it tests |
|---|---|
| 1. Paediatric croup happy path | Full tool chain, CHEO Ottawa, 8.4mg dose delivered |
| 2. Jurisdiction variance | Same note, UK NICE, 2.1mg — different guidelines, different doses |
| 3. Adult hypertension with NSAID | NICE NG136, ramipril recommended, ibuprofen interaction flagged |
| 4. Missing jurisdiction refusal | Agent refuses, lists valid jurisdictions, no clinical content given |
| 5. Anaphylaxis emergency | Escalation priority, age-banded adrenaline dose, IM route |
| 6. Incomplete note safety refusal | No dose given without weight and age, agent asks for missing context |

Scenario 6 programmatically checks that no dose number appears in the response before weight is provided. This is a safety validation, not just a functional test.

### Testing individual tools without an API key

All 14 deterministic tools can be tested without any API calls:

```bash
python3 -c "
from agent.session import reset_session
from tools.jurisdiction import set_jurisdiction
from tools.dose_calculator import calculate_dose

reset_session()
set_jurisdiction('CAN_CHEO_OTTAWA')
result = calculate_dose(condition='croup', severity='moderate', weight_kg=14, age_years=3)
print(result)
"
```

Expected output: 8.4mg oral dexamethasone per CHEO Croup Pathway v2.1.

---

## Project Structure

```
heidi_assistant/
├── streamlit_chat.py          # Streamlit chat UI
├── .env.example               # API key template
├── requirements.txt
├── README.md
│
├── agent/
│   ├── session.py             # Session state, jurisdiction, conversation history
│   ├── agent_loop.py          # Claude tool_use orchestration
│   └── system_prompt.py       # 12 safety rules injected into every API call
│
├── tools/
│   ├── tool_definitions.py    # 14 JSON schemas + dispatch table
│   ├── jurisdiction.py        # Set / get / validate jurisdiction
│   ├── guideline_retrieval.py # Load guideline by (jurisdiction, condition)
│   ├── drug_class_safety.py   # Required context matrix per drug class
│   ├── severity_assessment.py # Westley Croup Score + extensible scorer registry
│   ├── dose_calculator.py     # Deterministic dose calculator
│   ├── allergy_check.py       # Cross-reactivity matrix
│   ├── interaction_check.py   # Drug interaction matrix
│   ├── escalation_check.py    # Emergency criteria checker
│   └── audit_logger.py        # Append-only JSONL audit trail
│
├── guidelines/                # 6 curated guideline files
├── tests/
│   └── test_scenarios.py      # Six end-to-end scenario tests
└── logs/
    └── audit_log.jsonl        # Append-only run log (gitignored)
```

---

## Supported Conditions and Jurisdictions

| Condition | AUS RCH | AUS TG | CAN CHEO | UK NICE | International |
|---|---|---|---|---|---|
| Croup (paediatric) | Yes | | Yes | Yes | |
| Hypertension (adult) | | Yes | | Yes | |
| Anaphylaxis (all ages) | | | | | Yes |

---

## Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| UI | Streamlit 1.x | Fastest path to clinical-grade chat UI with Python session state |
| Agent | Anthropic Python SDK | tool_use API keeps Claude in orchestration role, not calculation role |
| LLM | claude-sonnet-4-5, temp=0 | Temperature 0 — same clinical input must produce the same plan |
| Tools | Pure Python | Deterministic execution. No AI in safety-critical calculations |
| Guidelines | Local .txt files | Reliable for demo. Production: licensed source API + vector DB |
| Audit | Append-only JSONL | Regulatory traceability from day one |

---

## Known Limitations and Production Roadmap

| Dimension | MVP | Production |
|---|---|---|
| Guideline source | 6 curated local files | Daily sync from licensed sources, vector DB, hospital API |
| Drug interactions | Curated Python matrix | BNF / Lexicomp / Micromedex API |
| Severity scoring | Westley only | CURB-65, Wells, Centor, structured EMR input |
| Authentication | None | OAuth / SSO with institution |
| EMR integration | None | FHIR R4 bidirectional |
| Conditions | Three | Full formulary via condition router |
| Audit storage | Local JSONL | Centralised audit DB with regulatory reporting |

The agentic pattern, safety gates, and audit trail are identical at MVP and production scale. Only the data layer changes.
