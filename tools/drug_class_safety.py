"""
Drug-class safety matrix — tells the agent what context must be gathered
before recommending any drug in a given class. This is the second
architectural safety gate: no medication recommendation proceeds without
the drug-class-specific context being satisfied.
"""


# Each entry defines what safety context is required before recommending
# any drug in that class. Required = hard block. Recommended = warn if absent.
DRUG_CLASS_SAFETY_MATRIX = {

    'paediatric_corticosteroid': {
        'description':       'Oral/IV corticosteroids in paediatric patients (e.g. dexamethasone, prednisolone for croup, asthma, etc.)',
        'required_context':  ['weight_kg', 'age_years', 'allergies', 'current_medications'],
        'recommended_context': ['recent_steroid_use', 'immunosuppression', 'active_infection'],
        'warnings_to_surface': [
            'Behavioural changes and sleep disturbance common 24-48 hours post-dose',
            'Single-dose dexamethasone is safe in immunocompetent children; caution if immunosuppressed',
        ],
        'absolute_contraindications': ['known_steroid_allergy', 'live_vaccine_within_2_weeks'],
    },

    'adult_corticosteroid': {
        'description':       'Oral/IV corticosteroids in adults',
        'required_context':  ['weight_kg', 'allergies', 'current_medications'],
        'recommended_context': ['diabetes_status', 'hypertension', 'peptic_ulcer_history', 'immunosuppression'],
        'warnings_to_surface': [
            'Increases blood glucose — monitor in diabetic patients',
            'Long-term use risks: osteoporosis, adrenal suppression, immunosuppression',
            'Consider PPI cover if concurrent NSAID use',
        ],
        'absolute_contraindications': ['systemic_fungal_infection', 'live_vaccine_within_4_weeks'],
    },

    'antibiotic': {
        'description':       'Antibacterial agents (all routes)',
        'required_context':  ['allergies', 'renal_function', 'age_years'],
        'recommended_context': ['pregnancy_status', 'current_medications', 'weight_kg_for_paediatric', 'recent_antibiotic_use'],
        'warnings_to_surface': [
            'Penicillin allergy cross-reactivity with cephalosporins (<1% with 3rd gen)',
            'Dose adjustment often required in renal impairment',
            'Risk of C. difficile, especially with broad-spectrum agents',
            'Check antimicrobial stewardship guidelines',
        ],
        'absolute_contraindications': ['documented_class_allergy'],
    },

    'nsaid': {
        'description':       'Non-steroidal anti-inflammatory drugs (ibuprofen, naproxen, diclofenac, etc.)',
        'required_context':  ['renal_function', 'current_medications', 'age_years'],
        'recommended_context': ['gi_history', 'cardiovascular_disease', 'pregnancy_status', 'asthma'],
        'warnings_to_surface': [
            'Triple whammy: NSAID + ACEi/ARB + diuretic — high risk of acute kidney injury',
            'Increased cardiovascular risk with long-term use',
            'GI bleeding risk — consider PPI in high-risk patients',
            'Avoid in third trimester of pregnancy',
            'Can precipitate asthma in NSAID-sensitive patients',
        ],
        'absolute_contraindications': ['active_gi_bleed', 'severe_renal_impairment', 'known_nsaid_hypersensitivity'],
    },

    'antihypertensive': {
        'description':       'Medications for hypertension (ACEi, ARBs, CCBs, diuretics, beta-blockers)',
        'required_context':  ['renal_function', 'pregnancy_status', 'current_medications'],
        'recommended_context': ['electrolytes', 'cardiac_history', 'diabetes_status', 'ethnicity'],
        'warnings_to_surface': [
            'ACE inhibitors and ARBs are contraindicated in pregnancy (teratogenic)',
            'Check U&Es and eGFR before starting and within 1-2 weeks',
            'ACEi/ARB + NSAID increases AKI risk significantly',
            'Beta-blockers avoided in asthma',
            'First-line drug class may vary by age and ethnicity',
        ],
        'absolute_contraindications': ['pregnancy_for_acei_arb', 'angioedema_history_for_acei'],
    },

    'anticoagulant': {
        'description':       'Anticoagulant medications (warfarin, DOACs, heparin, LMWH)',
        'required_context':  ['current_medications', 'bleeding_history', 'renal_function', 'weight_kg'],
        'recommended_context': ['pregnancy_status', 'planned_procedures', 'age_years', 'falls_risk'],
        'warnings_to_surface': [
            'Bleeding risk — assess HAS-BLED or equivalent',
            'Drug interactions common, especially with antibiotics and NSAIDs',
            'DOAC dose adjustment required in renal impairment',
            'Warfarin requires INR monitoring and dietary consistency',
            'Bridging strategy needed for procedures',
        ],
        'absolute_contraindications': ['active_major_bleeding', 'severe_thrombocytopaenia'],
    },

    'opioid': {
        'description':       'Opioid analgesics',
        'required_context':  ['current_medications', 'respiratory_function', 'age_years'],
        'recommended_context': ['renal_function', 'hepatic_function', 'history_of_substance_use', 'pregnancy_status'],
        'warnings_to_surface': [
            'Respiratory depression risk, especially with benzodiazepines',
            'Dose reduction needed in elderly, renal or hepatic impairment',
            'Naloxone availability for patients on chronic opioids',
            'Constipation prophylaxis',
            'Risk of dependence and tolerance',
        ],
        'absolute_contraindications': ['severe_respiratory_depression', 'paralytic_ileus'],
    },

    'adrenaline_emergency': {
        'description':       'Adrenaline (epinephrine) for anaphylaxis or cardiac arrest',
        'required_context':  ['weight_kg_or_age_band'],
        'recommended_context': ['known_cardiac_history_for_post_event_monitoring'],
        'warnings_to_surface': [
            'NO absolute contraindications in anaphylaxis',
            'IM route (anterolateral thigh) — NEVER subcutaneous for anaphylaxis',
            'IV only in monitored settings by experienced clinicians',
            'Withholding adrenaline in anaphylaxis is more dangerous than giving it',
        ],
        'absolute_contraindications': [],
    },

    'bronchodilator': {
        'description':       'Short-acting and long-acting bronchodilators',
        'required_context':  ['age_years', 'cardiac_history'],
        'recommended_context': ['current_medications', 'severity_of_reaction', 'previous_response_to_treatment'],
        'warnings_to_surface': [
            'Tachycardia and tremor common side effects',
            'Caution with beta-blockers (reduces effect)',
            'LABA monotherapy avoided in asthma (add ICS)',
        ],
        'absolute_contraindications': [],
    },
}


# Maps specific drugs to their class for lookup
DRUG_TO_CLASS = {
    # Paediatric steroids
    'dexamethasone_paediatric': 'paediatric_corticosteroid',
    'prednisolone_paediatric':  'paediatric_corticosteroid',
    # Adult steroids
    'dexamethasone_adult':      'adult_corticosteroid',
    'prednisolone_adult':       'adult_corticosteroid',
    'hydrocortisone':           'adult_corticosteroid',
    # Antibiotics
    'amoxicillin':              'antibiotic',
    'cefalexin':                'antibiotic',
    'ceftriaxone':              'antibiotic',
    'flucloxacillin':           'antibiotic',
    # NSAIDs
    'ibuprofen':                'nsaid',
    'naproxen':                 'nsaid',
    'diclofenac':               'nsaid',
    # Antihypertensives
    'ramipril':                 'antihypertensive',
    'perindopril':              'antihypertensive',
    'lisinopril':               'antihypertensive',
    'candesartan':              'antihypertensive',
    'losartan':                 'antihypertensive',
    'amlodipine':               'antihypertensive',
    'indapamide':               'antihypertensive',
    # Anticoagulants
    'warfarin':                 'anticoagulant',
    'apixaban':                 'anticoagulant',
    'rivaroxaban':              'anticoagulant',
    # Opioids
    'morphine':                 'opioid',
    'oxycodone':                'opioid',
    'codeine':                  'opioid',
    # Emergency
    'adrenaline':               'adrenaline_emergency',
    'epinephrine':              'adrenaline_emergency',
    # Bronchodilators
    'salbutamol':               'bronchodilator',
    'albuterol':                'bronchodilator',
}


def get_drug_class_safety(drug_or_class: str, age_years: float = None) -> dict:
    """
    Tool: return the safety context required before recommending this drug or drug class.

    Accepts either a specific drug name or a drug class directly.
    If a drug is paediatric (age < 18) and has an adult/paediatric split class,
    the age parameter routes to the correct class.
    """
    key = drug_or_class.lower().strip()

    # Direct class match
    if key in DRUG_CLASS_SAFETY_MATRIX:
        return _format_response(key, DRUG_CLASS_SAFETY_MATRIX[key])

    # Specific drug with paediatric/adult split
    if key in ('dexamethasone', 'prednisolone'):
        if age_years is not None:
            sub_key = f'{key}_paediatric' if age_years < 18 else f'{key}_adult'
            drug_class = DRUG_TO_CLASS[sub_key]
            return _format_response(drug_class, DRUG_CLASS_SAFETY_MATRIX[drug_class])
        else:
            return {
                'status':  'ambiguous',
                'message': (
                    f"Drug '{key}' has different safety considerations for paediatric "
                    f"vs adult patients. Provide age_years to get the correct class."
                ),
                'drug':    key,
            }

    # Specific drug lookup
    if key in DRUG_TO_CLASS:
        drug_class = DRUG_TO_CLASS[key]
        return _format_response(drug_class, DRUG_CLASS_SAFETY_MATRIX[drug_class], drug=key)

    # Not found
    return {
        'status':  'not_in_library',
        'message': (
            f"Drug or class '{key}' is not in the MVP safety matrix. "
            f"For production this would use a verified pharmacological database. "
            f"Proceed with caution: gather age, weight, allergies, current medications, "
            f"renal function, and pregnancy status as baseline safety context."
        ),
        'drug_queried':     key,
        'known_classes':    list(DRUG_CLASS_SAFETY_MATRIX.keys()),
        'fallback_context': ['age_years', 'weight_kg', 'allergies', 'current_medications', 'renal_function', 'pregnancy_status'],
    }


def _format_response(drug_class, class_info, drug=None):
    return {
        'status':                      'success',
        'drug_class':                  drug_class,
        'description':                 class_info['description'],
        'required_context':            class_info['required_context'],
        'recommended_context':         class_info['recommended_context'],
        'warnings_to_surface':         class_info['warnings_to_surface'],
        'absolute_contraindications':  class_info['absolute_contraindications'],
        'drug_queried':                drug,
    }


def check_required_context(drug_class: str, provided_context: dict) -> dict:
    """
    Tool: given a drug class and what context the agent has gathered,
    return what's still missing. Agent calls this before dose calculation
    to confirm it has what it needs.
    """
    if drug_class not in DRUG_CLASS_SAFETY_MATRIX:
        return {
            'status':  'unknown_class',
            'message': f"Drug class '{drug_class}' not in safety matrix.",
        }

    class_info = DRUG_CLASS_SAFETY_MATRIX[drug_class]
    required = class_info['required_context']
    missing_required = [r for r in required if r not in provided_context or provided_context.get(r) in (None, '', 'unknown')]

    recommended = class_info['recommended_context']
    missing_recommended = [r for r in recommended if r not in provided_context or provided_context.get(r) in (None, '', 'unknown')]

    return {
        'status':              'complete' if not missing_required else 'incomplete',
        'drug_class':          drug_class,
        'missing_required':    missing_required,
        'missing_recommended': missing_recommended,
        'can_proceed':         not missing_required,
        'message': (
            f"Cannot proceed — missing required context: {missing_required}"
            if missing_required
            else f"Required context satisfied. Missing recommended (warn only): {missing_recommended}"
        ),
    }
