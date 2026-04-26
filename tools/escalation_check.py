"""
Escalation check — determines whether patient findings meet emergency
escalation criteria for a given condition. Returns pass/fail with
triggers found.

This is a condition-aware safety gate. For croup, triggers include
hypoxia below threshold, impending airway obstruction, cyanosis at rest.
For anaphylaxis, the condition itself is the escalation — it's always
emergency priority.
"""

from tools.severity_assessment import _is_negated


# Escalation trigger patterns per condition
# Each trigger has a short name and a list of text patterns that would fire it
CROUP_ESCALATION_TRIGGERS = [
    {
        'name':     'cyanosis_at_rest',
        'patterns': ['cyanosis at rest', 'cyanotic at rest'],
        'clinical': 'Cyanosis at rest indicates severe hypoxaemia and impending respiratory failure.',
    },
    {
        'name':     'cyanosis_general',
        'patterns': ['cyanosis', 'cyanotic', 'blue lips', 'blue tongue'],
        'clinical': 'Any cyanosis in a child with respiratory distress is an emergency sign.',
    },
    {
        'name':     'apnoea',
        'patterns': ['apnoea', 'apnea', 'apneic episode', 'apnoeic episode'],
        'clinical': 'Apnoeic episodes indicate imminent respiratory arrest.',
    },
    {
        'name':     'drooling',
        'patterns': ['drooling', 'drools', 'unable to swallow saliva'],
        'clinical': 'Drooling may indicate epiglottitis or upper airway obstruction — consider alternative diagnosis urgently.',
    },
    {
        'name':     'tripod_position',
        'patterns': ['tripod position', 'tripoding', 'leaning forward to breathe'],
        'clinical': 'Tripod position suggests upper airway compromise.',
    },
    {
        'name':     'toxic_appearance',
        'patterns': ['toxic appearance', 'toxic-looking', 'appears toxic', 'septic appearance'],
        'clinical': 'Toxic appearance raises concern for bacterial tracheitis or sepsis.',
    },
    {
        'name':     'impending_obstruction',
        'patterns': ['impending airway obstruction', 'airway obstruction', 'exhaustion',
                     'decreased level of consciousness', 'obtunded', 'altered consciousness'],
        'clinical': 'Altered level of consciousness or exhaustion in croup indicates impending respiratory failure.',
    },
]


ANAPHYLAXIS_ESCALATION_TRIGGERS = [
    {
        'name':     'airway_compromise',
        'patterns': ['stridor', 'hoarse voice', 'throat tightness', 'tongue swelling',
                     'lip swelling', 'difficulty swallowing', 'drooling'],
        'clinical': 'Airway involvement in anaphylaxis — immediate IM adrenaline.',
    },
    {
        'name':     'breathing_compromise',
        'patterns': ['wheeze', 'wheezing', 'shortness of breath', 'respiratory distress', 'cyanosis'],
        'clinical': 'Respiratory involvement — immediate IM adrenaline.',
    },
    {
        'name':     'circulatory_compromise',
        'patterns': ['hypotension', 'collapse', 'syncope', 'loss of consciousness', 'pallor', 'weak pulse'],
        'clinical': 'Circulatory involvement — immediate IM adrenaline, lay flat, IV fluids.',
    },
]


def _check_patterns(text: str, patterns: list) -> list:
    """Return list of patterns found (not negated) in text."""
    text_lower = text.lower()
    hits = []
    for pattern in patterns:
        if pattern in text_lower:
            if not _is_negated(text, pattern):
                hits.append(pattern)
    return hits


def check_escalation(condition: str, findings: dict) -> dict:
    """
    Tool: check whether patient findings meet emergency escalation criteria.

    findings expected to contain 'examination_text' and/or 'history_text'.
    Also supports numeric 'spo2' and 'heart_rate' for threshold-based triggers.
    """
    condition_clean = condition.lower().strip()
    exam = findings.get('examination_text', '') or findings.get('exam', '') or ''
    hist = findings.get('history_text', '') or findings.get('history', '') or ''
    combined_text = f'{exam} {hist}'.strip()

    triggers_found = []

    # Condition-specific text-based triggers
    if condition_clean == 'croup':
        for trigger in CROUP_ESCALATION_TRIGGERS:
            hits = _check_patterns(combined_text, trigger['patterns'])
            if hits:
                triggers_found.append({
                    'trigger':  trigger['name'],
                    'matches':  hits,
                    'clinical_rationale': trigger['clinical'],
                })

    elif condition_clean == 'anaphylaxis':
        # Anaphylaxis is itself an emergency — always escalate
        for trigger in ANAPHYLAXIS_ESCALATION_TRIGGERS:
            hits = _check_patterns(combined_text, trigger['patterns'])
            if hits:
                triggers_found.append({
                    'trigger':  trigger['name'],
                    'matches':  hits,
                    'clinical_rationale': trigger['clinical'],
                })

    # SpO2 threshold — applies to any respiratory condition
    spo2 = findings.get('spo2') or findings.get('SpO2') or findings.get('oxygen_saturation')
    if spo2 is not None:
        try:
            spo2_val = float(spo2)
            if spo2_val < 92:
                triggers_found.append({
                    'trigger':  'hypoxia',
                    'matches':  [f'SpO2 {spo2_val}%'],
                    'clinical_rationale': f'SpO2 {spo2_val}% is below the 92% escalation threshold for respiratory emergencies.',
                })
        except (TypeError, ValueError):
            pass

    # Altered consciousness — applies across conditions
    consciousness_patterns = ['altered consciousness', 'unresponsive', 'unconscious',
                               'obtunded', 'not responding', 'gcs']
    hits = _check_patterns(combined_text, consciousness_patterns)
    if hits:
        triggers_found.append({
            'trigger':  'altered_consciousness',
            'matches':  hits,
            'clinical_rationale': 'Altered level of consciousness in the acute setting requires immediate senior review.',
        })

    escalate = bool(triggers_found)

    return {
        'condition':          condition_clean,
        'escalate':           escalate,
        'triggers_found':     triggers_found,
        'trigger_count':      len(triggers_found),
        'status':             'ESCALATE' if escalate else 'NO_ESCALATION',
        'message':            (
            f'ESCALATION REQUIRED — {len(triggers_found)} trigger(s) identified. '
            f'Activate emergency response and senior clinician review.'
            if escalate
            else f'No escalation triggers identified for {condition_clean}. Proceed with standard pathway.'
        ),
    }
