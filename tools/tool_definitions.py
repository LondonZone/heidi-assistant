"""
Tool definitions — JSON schemas for the Anthropic tool_use API.

Each tool we've built needs a matching schema here so Claude knows:
- What the tool is called
- What it does
- What parameters it takes (with types and descriptions)
- Which parameters are required

These schemas are passed to Claude in the API call. When Claude decides
to use a tool, it returns a tool_use block with matching parameters,
which the agent loop dispatches to the actual Python function.
"""


TOOLS = [

    # --- Jurisdiction management ---
    {
        "name": "set_jurisdiction",
        "description": (
            "Set the clinical guideline jurisdiction for the current session. "
            "This must be called before any guideline retrieval or dose calculation "
            "can happen. Jurisdiction determines which institution's protocols are used."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "jurisdiction": {
                    "type": "string",
                    "enum": [
                        "AUS_RCH_MELBOURNE",
                        "AUS_TG",
                        "CAN_CHEO_OTTAWA",
                        "CAN_CPS",
                        "UK_NICE",
                        "INTERNATIONAL",
                    ],
                    "description": (
                        "The jurisdiction code. AUS_RCH_MELBOURNE for Royal Children's Hospital Melbourne paediatrics. "
                        "AUS_TG for Therapeutic Guidelines Australia adult. CAN_CHEO_OTTAWA for CHEO paediatrics. "
                        "CAN_CPS for Canadian Paediatric Society. UK_NICE for NICE UK. "
                        "INTERNATIONAL for conditions with international consensus guidelines like anaphylaxis."
                    ),
                },
            },
            "required": ["jurisdiction"],
        },
    },
    {
        "name": "get_jurisdiction",
        "description": (
            "Check the current session jurisdiction. Returns is_set=false if no "
            "jurisdiction has been selected yet. Always call this before recommending "
            "anything guideline-based — if not set, you must ask the clinician to "
            "set it before proceeding."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "list_valid_jurisdictions",
        "description": "List all jurisdictions the system supports with human-readable labels.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },

    # --- Guideline retrieval ---
    {
        "name": "retrieve_guideline",
        "description": (
            "Retrieve the full clinical guideline for a specific condition in the "
            "current session jurisdiction (or an explicitly specified one). Returns "
            "guideline text, institution, version, review date, and staleness warning. "
            "Refuses if jurisdiction is not set or no matching guideline exists."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "condition": {
                    "type": "string",
                    "description": (
                        "The clinical condition. Examples: croup, hypertension, anaphylaxis. "
                        "Lowercase, no qualifiers."
                    ),
                },
                "jurisdiction": {
                    "type": "string",
                    "description": (
                        "Optional: explicit jurisdiction to use for THIS query only (does not "
                        "change session jurisdiction). If omitted, uses session jurisdiction."
                    ),
                },
            },
            "required": ["condition"],
        },
    },
    {
        "name": "list_available_guidelines",
        "description": (
            "List all locally available guidelines grouped by jurisdiction. Call this "
            "when you need to know what conditions are supported, or when the clinician "
            "asks about a condition you're unsure is covered."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },

    # --- Drug class safety ---
    {
        "name": "get_drug_class_safety",
        "description": (
            "Return the safety context required before recommending a drug or drug class. "
            "Use this BEFORE recommending any medication to find out what context you need "
            "to gather from the clinician (weight, age, allergies, renal function, etc.). "
            "Accepts either a specific drug name (e.g. 'dexamethasone', 'ramipril') or "
            "a drug class (e.g. 'paediatric_corticosteroid', 'nsaid', 'antihypertensive')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "drug_or_class": {
                    "type": "string",
                    "description": "The drug name or drug class to look up.",
                },
                "age_years": {
                    "type": "number",
                    "description": (
                        "Patient age in years. Required for drugs with paediatric/adult splits "
                        "like dexamethasone."
                    ),
                },
            },
            "required": ["drug_or_class"],
        },
    },
    {
        "name": "check_required_context",
        "description": (
            "Given a drug class and the context you've gathered so far, return what's "
            "still missing. Call this before dose_calculator to verify you have all the "
            "required context, and ask the clinician for anything missing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "drug_class": {
                    "type": "string",
                    "description": "The drug class (e.g. paediatric_corticosteroid).",
                },
                "provided_context": {
                    "type": "object",
                    "description": (
                        "Dictionary of context items the clinician has provided. Keys are "
                        "context names (weight_kg, age_years, allergies, current_medications, etc.) "
                        "and values are the actual values. Use 'none' for explicitly-stated absence."
                    ),
                },
            },
            "required": ["drug_class", "provided_context"],
        },
    },

    # --- Severity assessment ---
    {
        "name": "assess_severity",
        "description": (
            "Apply a validated clinical severity scoring instrument for a condition. "
            "Currently implements Westley Croup Score. Only call this for conditions "
            "that have a registered scorer — if none exists, the tool returns "
            "no_scorer_available and you should proceed without forcing a score. "
            "Most conditions do not need formal severity scoring."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "condition": {
                    "type": "string",
                    "description": "The condition to score (e.g. croup). Lowercase.",
                },
                "findings": {
                    "type": "object",
                    "description": (
                        "Clinical findings. Can include examination_text (free text of exam "
                        "findings), history_text (free text of history), spo2, or structured "
                        "Westley parameters (consciousness, cyanosis, stridor, air_entry, "
                        "retractions) as integers."
                    ),
                },
            },
            "required": ["condition", "findings"],
        },
    },
    {
        "name": "list_available_scorers",
        "description": "List all severity scoring instruments the system supports.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },

    # --- Dose calculator ---
    {
        "name": "calculate_dose",
        "description": (
            "Calculate medication dose for a condition based on jurisdiction, severity, "
            "weight, and age. THIS IS THE CLINICAL SAFETY BOUNDARY — the tool refuses "
            "to calculate if required parameters are missing or implausible, or if no "
            "dose rule exists for this (jurisdiction, condition, severity) combination. "
            "Always cite the returned guideline_ref in your response. Never calculate "
            "doses yourself — always use this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "condition": {
                    "type": "string",
                    "description": "Condition (croup, anaphylaxis, hypertension).",
                },
                "severity": {
                    "type": "string",
                    "description": (
                        "Severity label. For croup: mild, moderate, severe. "
                        "For hypertension: stage_1_under_55_non_afrocaribbean, "
                        "stage_1_over_55_or_afrocaribbean, adult_first_line_acei. "
                        "For anaphylaxis: leave blank — age determines dosing."
                    ),
                },
                "weight_kg": {
                    "type": "number",
                    "description": "Patient weight in kg. Required for weight-based dosing.",
                },
                "age_years": {
                    "type": "number",
                    "description": "Patient age in years. Required for all dose calculations.",
                },
                "jurisdiction": {
                    "type": "string",
                    "description": "Optional: override session jurisdiction for this calculation.",
                },
            },
            "required": ["condition", "age_years"],
        },
    },

    # --- Allergy check ---
    {
        "name": "check_allergies",
        "description": (
            "Check whether a proposed drug would conflict with the patient's known "
            "allergies. Call this BEFORE recommending any medication. Returns 'refused' "
            "if a hard allergy contraindication is detected, 'warning' for partial "
            "cross-reactivity, or 'cleared' if safe."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "proposed_drug": {
                    "type": "string",
                    "description": "The drug you are considering recommending.",
                },
                "known_allergies": {
                    "type": "string",
                    "description": (
                        "The patient's known allergies. Can be a string like 'penicillin, sulfa' "
                        "or 'none' / 'NKDA' if no allergies."
                    ),
                },
            },
            "required": ["proposed_drug", "known_allergies"],
        },
    },

    # --- Interaction check ---
    {
        "name": "check_interactions",
        "description": (
            "Check for clinically significant drug interactions between a proposed drug "
            "and the patient's current medications. Also flags age-based contraindications "
            "like aspirin in children under 16 (Reye syndrome risk). Call this before "
            "finalising any medication recommendation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "proposed_drug": {
                    "type": "string",
                    "description": "The drug you are considering recommending.",
                },
                "current_medications": {
                    "type": "string",
                    "description": (
                        "Current medications as a comma-separated string, or 'none' if "
                        "no current medications. Example: 'ramipril 2.5mg daily, ibuprofen 400mg PRN'."
                    ),
                },
                "age_years": {
                    "type": "number",
                    "description": "Patient age — enables age-based interaction flagging.",
                },
            },
            "required": ["proposed_drug", "current_medications"],
        },
    },

    # --- Escalation check ---
    {
        "name": "check_escalation",
        "description": (
            "Determine whether patient findings meet emergency escalation criteria for "
            "the condition. Call this early — before discussing routine management — "
            "especially for respiratory conditions, anaphylaxis, or any presentation "
            "where deterioration is possible. Returns ESCALATE or NO_ESCALATION with "
            "specific triggers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "condition": {
                    "type": "string",
                    "description": "Condition (croup, anaphylaxis).",
                },
                "findings": {
                    "type": "object",
                    "description": (
                        "Clinical findings. Include examination_text, history_text, spo2, "
                        "or structured findings. The tool scans for escalation triggers in "
                        "the text and applies negation handling."
                    ),
                },
            },
            "required": ["condition", "findings"],
        },
    },

    # --- Audit logger ---
    {
        "name": "log_event",
        "description": (
            "Log a clinically significant event to the audit trail. Use this for "
            "decisions that aren't automatically captured — e.g. you made a clinical "
            "recommendation outside the tools' scope, or you flagged a safety concern "
            "the tools didn't raise. Routine tool calls are auto-logged."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_type": {
                    "type": "string",
                    "description": "Short name for the event, e.g. 'safety_concern', 'out_of_scope_query', 'clinician_override'.",
                },
                "details": {
                    "type": "object",
                    "description": "Freeform dict of relevant context about the event.",
                },
            },
            "required": ["event_type"],
        },
    },
]


# Dispatch table: tool name → the Python function that implements it
# Used by the agent loop to actually call the tool when Claude requests it
def get_tool_dispatch():
    """Return the tool_name → function map. Imported here to avoid circular imports."""
    from tools.jurisdiction        import set_jurisdiction, get_jurisdiction, list_valid_jurisdictions
    from tools.guideline_retrieval import retrieve_guideline, list_available_guidelines
    from tools.drug_class_safety   import get_drug_class_safety, check_required_context
    from tools.severity_assessment import assess_severity, list_available_scorers
    from tools.dose_calculator     import calculate_dose
    from tools.allergy_check       import check_allergies
    from tools.interaction_check   import check_interactions
    from tools.escalation_check    import check_escalation
    from tools.audit_logger        import log_event

    return {
        'set_jurisdiction':          set_jurisdiction,
        'get_jurisdiction':          get_jurisdiction,
        'list_valid_jurisdictions':  list_valid_jurisdictions,
        'retrieve_guideline':        retrieve_guideline,
        'list_available_guidelines': list_available_guidelines,
        'get_drug_class_safety':     get_drug_class_safety,
        'check_required_context':    check_required_context,
        'assess_severity':           assess_severity,
        'list_available_scorers':    list_available_scorers,
        'calculate_dose':            calculate_dose,
        'check_allergies':           check_allergies,
        'check_interactions':        check_interactions,
        'check_escalation':          check_escalation,
        'log_event':                 log_event,
    }
