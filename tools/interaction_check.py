"""
Drug interaction check — validates proposed drug against current medications.

Maintains a matrix of clinically significant interactions. Production would
use a verified pharmacological database (BNF, Micromedex, Lexicomp). MVP
demonstrates the pattern with a curated set covering the conditions in the
demo (croup, anaphylaxis, hypertension) plus common real-world interactions.
"""


# Severity: HIGH = block or require specialist review, MODERATE = warn,
# LOW = note but proceed
INTERACTIONS = [
    # ACE inhibitor + NSAID — triple whammy risk with diuretic
    {
        'drugs':     ['ramipril', 'lisinopril', 'enalapril', 'perindopril', 'captopril',
                      'candesartan', 'losartan', 'irbesartan'],
        'with':      ['ibuprofen', 'naproxen', 'diclofenac', 'aspirin', 'celecoxib', 'indomethacin'],
        'severity':  'HIGH',
        'effect':    'NSAIDs reduce antihypertensive effect and increase renal injury risk. If combined with a diuretic this is the classic "triple whammy" causing acute kidney injury.',
        'action':    'Recommend paracetamol for analgesia instead of NSAIDs. If NSAID essential, monitor U&Es closely and avoid in patients with existing renal impairment or concurrent diuretic.',
    },

    # Anticoagulants + NSAIDs
    {
        'drugs':     ['warfarin', 'apixaban', 'rivaroxaban', 'dabigatran', 'heparin', 'enoxaparin'],
        'with':      ['ibuprofen', 'naproxen', 'diclofenac', 'aspirin'],
        'severity':  'HIGH',
        'effect':    'Increased bleeding risk, particularly GI bleeding. Additive antiplatelet/anticoagulant effect.',
        'action':    'Avoid combination where possible. If essential, use shortest course with PPI cover and monitor for bleeding.',
    },

    # Corticosteroids + NSAIDs
    {
        'drugs':     ['dexamethasone', 'prednisolone', 'prednisone', 'hydrocortisone', 'methylprednisolone'],
        'with':      ['ibuprofen', 'naproxen', 'diclofenac', 'aspirin'],
        'severity':  'MODERATE',
        'effect':    'Increased risk of GI ulceration and bleeding when combined.',
        'action':    'Consider PPI cover if combination is necessary. Shortest duration possible.',
    },

    # Corticosteroids — duplicate therapy
    {
        'drugs':     ['dexamethasone'],
        'with':      ['prednisolone', 'prednisone', 'hydrocortisone', 'methylprednisolone', 'betamethasone'],
        'severity':  'MODERATE',
        'effect':    'Cumulative corticosteroid exposure. In short-term single-dose scenarios (e.g. croup) this is usually manageable, but increases risk of adrenal suppression, hyperglycaemia, and immunosuppression with repeated doses.',
        'action':    'Document rationale. Consider specialist consultation (e.g. nephrology if patient on chronic steroid). Monitor blood glucose if diabetic.',
    },

    # Aspirin in children — Reye syndrome
    {
        'drugs':     ['aspirin', 'salicylate'],
        'with':      [],  # applies to any paediatric use, flagged by age not co-med
        'severity':  'HIGH',
        'effect':    'Aspirin in children under 16 years with viral illness carries risk of Reye syndrome (acute hepatic failure + encephalopathy).',
        'action':    'Avoid aspirin in paediatric viral illnesses unless specifically indicated (e.g. Kawasaki disease). Use paracetamol or ibuprofen for fever/pain instead.',
        'age_based': True,
        'age_max':   16,
    },

    # Beta-blockers + bronchodilators
    {
        'drugs':     ['salbutamol', 'albuterol', 'terbutaline', 'formoterol', 'salmeterol'],
        'with':      ['propranolol', 'atenolol', 'bisoprolol', 'metoprolol'],
        'severity':  'MODERATE',
        'effect':    'Non-selective beta-blockers antagonise bronchodilator effect. Can precipitate bronchospasm in asthma/COPD.',
        'action':    'Use cardioselective beta-blocker (bisoprolol preferred) if essential. Avoid non-selective agents in asthma.',
    },

    # Opioids + benzodiazepines — respiratory depression
    {
        'drugs':     ['morphine', 'oxycodone', 'codeine', 'fentanyl', 'tramadol', 'hydromorphone'],
        'with':      ['diazepam', 'lorazepam', 'midazolam', 'temazepam', 'clonazepam', 'alprazolam'],
        'severity':  'HIGH',
        'effect':    'Synergistic CNS and respiratory depression. Black-box warning.',
        'action':    'Avoid combination. If clinically necessary, use lowest effective doses of both, monitor closely, and counsel on sedation and overdose risk.',
    },
]


def _normalise(s: str) -> str:
    return (s or '').lower().strip()


def check_interactions(proposed_drug: str, current_medications, age_years: float = None) -> dict:
    """
    Tool: check for clinically significant interactions between a proposed drug
    and the patient's current medications.

    current_medications can be a list of drug names or a comma-separated string.
    age_years enables age-based interaction flagging (e.g. aspirin in children).
    """
    proposed_clean = _normalise(proposed_drug)

    # Normalise current medications
    if current_medications is None:
        meds_list = []
    elif isinstance(current_medications, str):
        m = _normalise(current_medications)
        if m in ('', 'none', 'nil', 'no medications', 'no current medications'):
            meds_list = []
        else:
            meds_list = [x.strip() for x in m.replace(';', ',').split(',') if x.strip()]
    elif isinstance(current_medications, list):
        meds_list = [_normalise(x) for x in current_medications if x]
    else:
        meds_list = []

    # Strip dosage info from medication names (e.g. "aspirin 75mg daily" -> "aspirin")
    meds_list_clean = []
    for m in meds_list:
        # Take first word as drug name
        first_word = m.split()[0] if m.split() else m
        meds_list_clean.append(first_word)

    flagged = []

    for interaction in INTERACTIONS:
        # Check if proposed drug is in the trigger list
        proposed_matches = any(d in proposed_clean or proposed_clean in d for d in interaction['drugs'])

        # Age-based interactions (e.g. aspirin in children)
        if interaction.get('age_based') and proposed_matches:
            age_max = interaction.get('age_max')
            if age_years is not None and age_years < age_max:
                flagged.append({
                    'severity':  interaction['severity'],
                    'trigger':   proposed_clean,
                    'reason':    f'age-based ({age_years} years < {age_max})',
                    'effect':    interaction['effect'],
                    'action':    interaction['action'],
                })
            continue

        if not proposed_matches:
            continue

        # Check current meds against 'with' list
        for med in meds_list_clean:
            for interacting in interaction['with']:
                if med == interacting or interacting in med or med in interacting:
                    flagged.append({
                        'severity':  interaction['severity'],
                        'proposed':  proposed_clean,
                        'current':   med,
                        'effect':    interaction['effect'],
                        'action':    interaction['action'],
                    })
                    break

    high_severity = [f for f in flagged if f['severity'] == 'HIGH']
    moderate_severity = [f for f in flagged if f['severity'] == 'MODERATE']
    low_severity = [f for f in flagged if f['severity'] == 'LOW']

    if high_severity:
        status = 'high_severity_interaction'
        message = f'{len(high_severity)} HIGH severity interaction(s) detected. Review required before proceeding.'
    elif moderate_severity:
        status = 'moderate_severity_interaction'
        message = f'{len(moderate_severity)} MODERATE severity interaction(s) detected. Consider alternative or add mitigation.'
    elif low_severity:
        status = 'low_severity_interaction'
        message = f'{len(low_severity)} LOW severity interaction(s) noted. Document and monitor.'
    elif meds_list_clean:
        status = 'cleared'
        message = f'No significant interactions between {proposed_clean} and current medications: {meds_list_clean}'
    else:
        status = 'cleared'
        message = f'No current medications on file. {proposed_clean} cleared from an interaction standpoint.'

    return {
        'status':               status,
        'proposed_drug':        proposed_clean,
        'current_medications':  meds_list_clean,
        'interactions_flagged': flagged,
        'high_severity_count':  len(high_severity),
        'moderate_severity_count': len(moderate_severity),
        'low_severity_count':   len(low_severity),
        'message':              message,
    }
