"""
Guideline retrieval tool — reads a guideline file by condition + jurisdiction.
Enforces the jurisdiction gate: refuses if no jurisdiction set.
Parses metadata header, checks staleness, returns structured content.
"""

import os
from datetime import datetime
from agent.session import get_active_session, VALID_JURISDICTIONS

GUIDELINES_DIR = 'guidelines'

# Maps (jurisdiction, condition) to filename
# One jurisdiction can have multiple conditions; one condition can have multiple jurisdictions
GUIDELINE_INDEX = {
    ('AUS_RCH_MELBOURNE', 'croup'):       'AUS_RCH_croup.txt',
    ('CAN_CHEO_OTTAWA',   'croup'):       'CAN_CHEO_croup.txt',
    ('UK_NICE',           'croup'):       'UK_NICE_croup.txt',
    ('UK_NICE',           'hypertension'): 'UK_NICE_hypertension.txt',
    ('AUS_TG',            'hypertension'): 'AUS_TG_hypertension.txt',
    ('INTERNATIONAL',     'anaphylaxis'):  'INTERNATIONAL_anaphylaxis.txt',
}


def _parse_metadata(text):
    """Parse the header block of a guideline file."""
    metadata = {}
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith('---'):
            break
        if ':' in line:
            key, value = line.split(':', 1)
            metadata[key.strip().lower()] = value.strip()
    return metadata


def _check_staleness(review_date_str):
    """Return True if guideline past review date."""
    if not review_date_str or review_date_str.lower() == 'unknown':
        return False
    try:
        review_date = datetime.strptime(review_date_str, '%Y-%m-%d')
        return datetime.utcnow() > review_date
    except ValueError:
        return False


def _extract_content(text):
    """Return everything after the --- separator."""
    if '---' in text:
        return text.split('---', 1)[1].strip()
    return text.strip()


def retrieve_guideline(condition: str, jurisdiction: str = None) -> dict:
    """
    Tool: retrieve a guideline by condition. Uses session jurisdiction if not provided.

    Refuses if:
    - Jurisdiction not set (session) AND not supplied
    - Invalid jurisdiction
    - No guideline exists for this (jurisdiction, condition) pair
    - Guideline file missing from disk
    """
    session = get_active_session()

    # Determine effective jurisdiction
    effective_jurisdiction = jurisdiction or session.jurisdiction

    if not effective_jurisdiction:
        return {
            'status':  'refused',
            'reason':  'jurisdiction_not_set',
            'message': (
                "Cannot retrieve guideline — no jurisdiction set for this session. "
                "Guidelines vary significantly by region and using the wrong one is "
                "a patient safety risk. Please set a jurisdiction before requesting "
                "guideline content."
            ),
            'valid_jurisdictions': list(VALID_JURISDICTIONS.keys()),
        }

    if effective_jurisdiction not in VALID_JURISDICTIONS:
        return {
            'status':  'refused',
            'reason':  'invalid_jurisdiction',
            'message': f"Invalid jurisdiction: {effective_jurisdiction}",
            'valid_jurisdictions': list(VALID_JURISDICTIONS.keys()),
        }

    # Normalise condition
    condition_clean = condition.lower().strip()

    # Lookup filename
    key = (effective_jurisdiction, condition_clean)
    if key not in GUIDELINE_INDEX:
        # Find which conditions ARE available for this jurisdiction
        available = [c for (j, c) in GUIDELINE_INDEX.keys() if j == effective_jurisdiction]
        return {
            'status':  'not_found',
            'reason':  'no_matching_guideline',
            'message': (
                f"No local guideline for condition '{condition_clean}' in "
                f"jurisdiction '{effective_jurisdiction}'. "
                f"Available conditions for this jurisdiction: {available}"
            ),
            'condition':    condition_clean,
            'jurisdiction': effective_jurisdiction,
            'available_conditions_for_jurisdiction': available,
        }

    filename = GUIDELINE_INDEX[key]
    filepath = os.path.join(GUIDELINES_DIR, filename)

    if not os.path.exists(filepath):
        return {
            'status':  'error',
            'reason':  'file_missing',
            'message': f"Guideline file expected but not found: {filepath}",
        }

    # Read and parse
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    metadata = _parse_metadata(text)
    content = _extract_content(text)
    staleness = _check_staleness(metadata.get('review_date'))

    return {
        'status':         'success',
        'jurisdiction':   effective_jurisdiction,
        'jurisdiction_label': VALID_JURISDICTIONS[effective_jurisdiction],
        'condition':      condition_clean,
        'institution':    metadata.get('institution', 'Unknown'),
        'guideline_name': metadata.get('guideline_name', 'Unknown'),
        'version':        metadata.get('version', 'Unknown'),
        'last_updated':   metadata.get('last_updated', 'Unknown'),
        'review_date':    metadata.get('review_date', 'Unknown'),
        'evidence_level': metadata.get('evidence_level', 'Unknown'),
        'age_range':      metadata.get('age_range', 'Unknown'),
        'staleness_warning': staleness,
        'content':        content,
        'filepath':       filepath,
    }


def list_available_guidelines() -> dict:
    """Tool: list all locally available guidelines grouped by jurisdiction."""
    by_jurisdiction = {}
    for (jurisdiction, condition), filename in GUIDELINE_INDEX.items():
        if jurisdiction not in by_jurisdiction:
            by_jurisdiction[jurisdiction] = []
        by_jurisdiction[jurisdiction].append(condition)

    return {
        'by_jurisdiction': by_jurisdiction,
        'total_guidelines': len(GUIDELINE_INDEX),
        'jurisdictions_supported': list(by_jurisdiction.keys()),
    }
