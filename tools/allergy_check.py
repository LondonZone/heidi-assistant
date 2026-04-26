"""
Allergy check — validates that a proposed drug does not conflict with
the patient's known allergies. Refuses if allergy would be a hard
contraindication.

This is a deterministic lookup, not AI. The matrix below maps drug
families to related drugs so that a penicillin allergy blocks ALL
penicillins, a sulfa allergy flags sulfa-containing agents, etc.
"""


# Drug family cross-reactivity map
# Key = allergy name normalised, Value = list of drugs that would conflict
CROSS_REACTIVITY_MAP = {
    'penicillin': [
        'amoxicillin', 'ampicillin', 'flucloxacillin', 'benzylpenicillin',
        'phenoxymethylpenicillin', 'piperacillin', 'tazocin',
    ],
    'cephalosporin': [
        'cefalexin', 'cefazolin', 'cefuroxime', 'ceftriaxone', 'cefotaxime',
        'ceftazidime', 'cefepime',
    ],
    'sulfa': [
        'trimethoprim-sulfamethoxazole', 'sulfasalazine', 'sulfadiazine',
        'co-trimoxazole',
    ],
    'nsaid': [
        'ibuprofen', 'naproxen', 'diclofenac', 'aspirin', 'celecoxib',
        'indomethacin', 'ketorolac',
    ],
    'aspirin': [
        'aspirin', 'salicylate',
    ],
    'steroid': [
        'dexamethasone', 'prednisolone', 'prednisone', 'hydrocortisone',
        'methylprednisolone', 'betamethasone',
    ],
    'ace inhibitor': [
        'ramipril', 'lisinopril', 'enalapril', 'perindopril', 'captopril',
    ],
    'ace': [
        'ramipril', 'lisinopril', 'enalapril', 'perindopril', 'captopril',
    ],
    'macrolide': [
        'erythromycin', 'clarithromycin', 'azithromycin', 'roxithromycin',
    ],
    'opioid': [
        'morphine', 'oxycodone', 'codeine', 'fentanyl', 'tramadol', 'hydromorphone',
    ],
    'codeine': [
        'codeine', 'morphine',  # codeine allergy often reflects morphine allergy
    ],
}


# Partial cross-reactivity (clinical warning, not hard block)
PARTIAL_CROSS_REACTIVITY = {
    'penicillin': [
        {'drug_class': 'cephalosporin',
         'rate':       'approx 1-2% with 1st generation; <1% with 3rd generation',
         'action':     'Use with caution if penicillin allergy is non-severe (rash only). Avoid if previous anaphylaxis, Stevens-Johnson, or other severe reaction.'},
    ],
    'aspirin': [
        {'drug_class': 'nsaid',
         'rate':       'significant (~10-20% of aspirin-sensitive asthmatics react to NSAIDs)',
         'action':     'Avoid NSAIDs in aspirin-sensitive patients unless tolerance documented.'},
    ],
}


def _normalise(s: str) -> str:
    return (s or '').lower().strip()


def check_allergies(proposed_drug: str, known_allergies) -> dict:
    """
    Tool: check whether a proposed drug conflicts with the patient's known allergies.

    known_allergies can be:
    - a string like "penicillin" or "penicillin, sulfa"
    - a list like ['penicillin', 'sulfa']
    - 'none' / 'nil' / 'NKDA' / empty — means no known allergies
    """
    proposed_clean = _normalise(proposed_drug)

    # Normalise known_allergies to a list
    if known_allergies is None:
        allergies_list = []
    elif isinstance(known_allergies, str):
        a = _normalise(known_allergies)
        if a in ('', 'none', 'nil', 'nkda', 'nkfa', 'no known drug allergies', 'no allergies'):
            allergies_list = []
        else:
            # Split on common separators
            allergies_list = [x.strip() for x in a.replace(';', ',').split(',') if x.strip()]
    elif isinstance(known_allergies, list):
        allergies_list = [_normalise(a) for a in known_allergies if a]
    else:
        allergies_list = []

    if not allergies_list:
        return {
            'status':         'cleared',
            'proposed_drug':  proposed_clean,
            'message':        f'No known allergies on file. {proposed_clean} is safe from an allergy standpoint.',
            'hard_blocks':    [],
            'warnings':       [],
        }

    hard_blocks = []
    warnings = []

    for allergy in allergies_list:
        # Direct drug match
        if allergy == proposed_clean:
            hard_blocks.append({
                'allergy':     allergy,
                'proposed':    proposed_clean,
                'type':        'direct_match',
                'message':     f"Patient has documented {allergy} allergy — direct match for proposed {proposed_clean}. DO NOT ADMINISTER.",
            })
            continue

        # Cross-reactivity check — hard blocks
        for family, members in CROSS_REACTIVITY_MAP.items():
            if family in allergy or allergy == family:
                if proposed_clean in members or any(m in proposed_clean for m in members):
                    hard_blocks.append({
                        'allergy':     allergy,
                        'proposed':    proposed_clean,
                        'type':        'cross_reactivity',
                        'family':      family,
                        'message':     f"Patient has {allergy} allergy. {proposed_clean} is in the {family} family. DO NOT ADMINISTER.",
                    })

        # Partial cross-reactivity — warnings
        for family, partials in PARTIAL_CROSS_REACTIVITY.items():
            if family in allergy or allergy == family:
                for partial in partials:
                    partial_members = CROSS_REACTIVITY_MAP.get(partial['drug_class'], [])
                    if proposed_clean in partial_members or any(m in proposed_clean for m in partial_members):
                        warnings.append({
                            'allergy':     allergy,
                            'proposed':    proposed_clean,
                            'type':        'partial_cross_reactivity',
                            'rate':        partial['rate'],
                            'action':      partial['action'],
                        })

    if hard_blocks:
        return {
            'status':         'refused',
            'proposed_drug':  proposed_clean,
            'hard_blocks':    hard_blocks,
            'warnings':       warnings,
            'message':        'Hard allergy contraindication detected. Do not administer this drug. Consider alternative.',
        }

    if warnings:
        return {
            'status':         'warning',
            'proposed_drug':  proposed_clean,
            'hard_blocks':    [],
            'warnings':       warnings,
            'message':        'Partial cross-reactivity flagged. Review warnings with clinical judgment.',
        }

    return {
        'status':         'cleared',
        'proposed_drug':  proposed_clean,
        'hard_blocks':    [],
        'warnings':       [],
        'message':        f'No allergy contraindication between {proposed_clean} and known allergies: {allergies_list}',
        'allergies_checked': allergies_list,
    }
