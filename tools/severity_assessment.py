"""
Severity assessment tool — applies a validated clinical scoring instrument
based on the condition. Currently implements Westley Croup Score.
Structured to be extensible: CURB-65, Wells Score, Centor, etc can be
added by registering new scorers in the SCORERS dict.
"""

# ============================================================
# NEGATION VOCABULARY — reused from previous build's work
# ============================================================

NEGATION_PREFIXES = [
    'no ', 'not ', 'without ', 'denies ', 'denied ',
    'no history of ', 'no evidence of ', 'no signs of ',
    'absent ', 'negative for ', 'rules out ',
    'family denies ', 'parent denies ', 'mother denies ', 'father denies ',
]

NEGATION_SUFFIXES = [
    ': absent', ': negative', ': nil', ': none',
    ' absent', ' negative', ' not present',
    ' not noted', ' not observed',
]


def _is_negated(text: str, finding: str) -> bool:
    """Check if a finding appears in a negated context in text."""
    text_lower = text.lower()
    finding_lower = finding.lower()

    idx = text_lower.find(finding_lower)
    if idx == -1:
        return False

    # Check window before finding for negation prefix
    window_start = max(0, idx - 50)
    window_before = text_lower[window_start:idx]
    for prefix in NEGATION_PREFIXES:
        if prefix in window_before:
            return True

    # Check window after finding for negation suffix
    window_end = min(len(text_lower), idx + len(finding_lower) + 30)
    window_after = text_lower[idx:window_end]
    for suffix in NEGATION_SUFFIXES:
        if suffix in window_after:
            return True

    return False


def _found(text: str, finding: str) -> bool:
    """Check if finding is present and not negated."""
    if finding.lower() not in text.lower():
        return False
    return not _is_negated(text, finding)


# ============================================================
# WESTLEY CROUP SCORE
# ============================================================

def westley_croup_score(findings: dict) -> dict:
    """
    Calculate Westley Croup Score from examination findings.

    Expected findings dict keys:
    - examination_text (str): raw examination section
    - OR structured keys: consciousness, cyanosis, stridor, air_entry, retractions

    Returns score, components, derived severity, and source flag.
    """
    # Allow structured input to short-circuit
    if all(k in findings for k in ('consciousness', 'cyanosis', 'stridor', 'air_entry', 'retractions')):
        components = {
            'consciousness': int(findings['consciousness']),
            'cyanosis':      int(findings['cyanosis']),
            'stridor':       int(findings['stridor']),
            'air_entry':     int(findings['air_entry']),
            'retractions':   int(findings['retractions']),
        }
        source = 'structured_input'
    else:
        exam = findings.get('examination_text', '') or findings.get('exam', '') or ''
        if not exam:
            return {
                'status':  'insufficient_data',
                'message': 'No examination text or structured findings provided for Westley scoring',
            }
        components = _score_westley_from_text(exam)
        source = 'text_extraction'

    total = sum(components.values())

    if total <= 2:
        severity = 'mild'
    elif total <= 7:
        severity = 'moderate'
    else:
        severity = 'severe'

    return {
        'status':     'success',
        'score_name': 'Westley Croup Score',
        'total':      total,
        'components': components,
        'severity':   severity,
        'source':     source,
        'thresholds': {
            'mild':     '0-2',
            'moderate': '3-7',
            'severe':   '8+',
        },
        'max_possible': 17,
    }


def _score_westley_from_text(text: str) -> dict:
    """Extract Westley components from examination text."""
    text_lower = text.lower()

    # Consciousness — altered counts as 5
    consciousness = 5 if _found(text, 'altered') or _found(text, 'lethargic') or _found(text, 'obtunded') else 0

    # Cyanosis — at rest=5, with agitation=4, none=0
    if _found(text, 'cyanosis at rest') or _found(text, 'cyanotic at rest'):
        cyanosis = 5
    elif _found(text, 'cyanosis with agitation') or _found(text, 'cyanotic with agitation'):
        cyanosis = 4
    elif _found(text, 'cyanosis') or _found(text, 'cyanotic'):
        cyanosis = 4
    else:
        cyanosis = 0

    # Stridor — at rest=2, with agitation=1, none=0
    if _found(text, 'stridor at rest') or _found(text, 'stridor present at rest'):
        stridor = 2
    elif _found(text, 'stridor with agitation') or _found(text, 'stridor on exertion'):
        stridor = 1
    elif _found(text, 'stridor'):
        # Default to 1 if stridor mentioned without qualifier
        stridor = 1
    else:
        stridor = 0

    # Air entry — markedly decreased=2, decreased=1, normal=0
    if _found(text, 'markedly decreased air entry') or _found(text, 'markedly reduced air entry'):
        air_entry = 2
    elif _found(text, 'decreased air entry') or _found(text, 'reduced air entry'):
        air_entry = 1
    else:
        air_entry = 0

    # Retractions — proximity-aware severity grading
    # Handles phrasing like "severe suprasternal and intercostal recession"
    # where qualifier and finding are separated by anatomical descriptors.
    retractions = _score_retractions_proximity(text)

    return {
        'consciousness': consciousness,
        'cyanosis':      cyanosis,
        'stridor':       stridor,
        'air_entry':     air_entry,
        'retractions':   retractions,
    }


def _score_retractions_proximity(text: str) -> int:
    """
    Score retractions/recession using proximity-aware matching.

    Looks for severity qualifiers (severe/marked/moderate/mild) within a
    window of the target word (recession/retractions/in-drawing), allowing
    for anatomical descriptors between them.

    Also checks for negation — "no recession" returns 0 regardless of qualifiers.
    """
    text_lower = text.lower()

    # Target words that indicate retractions/recession present
    target_words = ['recession', 'retractions', 'retraction', 'in-drawing', 'indrawing']

    # Find any target
    target_idx = -1
    target_word = None
    for word in target_words:
        idx = text_lower.find(word)
        if idx != -1:
            target_idx = idx
            target_word = word
            break

    if target_idx == -1:
        return 0

    # Check negation around the target word
    if _is_negated(text, target_word):
        return 0

    # Look backward up to 60 chars for severity qualifier
    window_start = max(0, target_idx - 60)
    window_before = text_lower[window_start:target_idx]

    # Also look forward a bit in case of "recession, severe"
    window_end = min(len(text_lower), target_idx + len(target_word) + 20)
    window_after = text_lower[target_idx + len(target_word):window_end]
    search_window = window_before + ' ' + window_after

    # Severity qualifiers — check in priority order (severe first)
    # "markedly" maps to severe, "moderately" to moderate, etc.
    if any(q in search_window for q in ['severe', 'severely', 'marked', 'markedly']):
        return 3
    if any(q in search_window for q in ['moderate', 'moderately']):
        return 2
    if any(q in search_window for q in ['mild', 'mildly', 'minimal', 'minor', 'slight']):
        return 1

    # Target word found without a qualifier — default to mild (present but ungraded)
    return 1


# ============================================================
# SCORER REGISTRY
# ============================================================

SCORERS = {
    'croup': {
        'name': 'Westley Croup Score',
        'function': westley_croup_score,
        'age_range': 'paediatric',
        'description': 'Validated severity score for paediatric croup (5 parameters)',
    },
    # Future scorers plug in here:
    # 'pneumonia_adult': { 'name': 'CURB-65', 'function': curb65_score, ... },
    # 'dvt':             { 'name': 'Wells Score', 'function': wells_score, ... },
    # 'pharyngitis':     { 'name': 'Centor Criteria', 'function': centor_score, ... },
}


def assess_severity(condition: str, findings: dict) -> dict:
    """
    Tool: apply the appropriate severity scorer for a condition.

    For croup, applies Westley Croup Score.
    For other conditions in the future, dispatch to the correct scorer.
    """
    condition_key = condition.lower().strip()

    if condition_key not in SCORERS:
        return {
            'status':  'no_scorer_available',
            'message': (
                f"No validated severity scorer available for '{condition_key}'. "
                f"Available scorers: {list(SCORERS.keys())}. "
                f"For production, additional scorers would be added (CURB-65 for pneumonia, "
                f"Wells for DVT, Centor for pharyngitis, etc.)"
            ),
            'condition': condition_key,
            'available_scorers': list(SCORERS.keys()),
        }

    scorer = SCORERS[condition_key]
    result = scorer['function'](findings)
    result['scorer_used'] = scorer['name']
    result['age_range'] = scorer['age_range']
    return result


def list_available_scorers() -> dict:
    """Tool: list all implemented severity scorers."""
    return {
        'scorers': [
            {
                'condition':   condition,
                'name':        info['name'],
                'age_range':   info['age_range'],
                'description': info['description'],
            }
            for condition, info in SCORERS.items()
        ],
        'total': len(SCORERS),
    }
