"""
Jurisdiction tool — Claude uses this to set and retrieve the session jurisdiction.
This is the foundation of the safety architecture. No guideline retrieval
works without jurisdiction set.
"""

from agent.session import get_active_session, VALID_JURISDICTIONS


def set_jurisdiction(jurisdiction: str, reason: str = 'user_selection') -> dict:
    """Tool: set the session jurisdiction."""
    session = get_active_session()

    try:
        result = session.set_jurisdiction(jurisdiction, reason=reason)
        return {
            'status':       'success',
            'jurisdiction': result['jurisdiction'],
            'label':        result['label'],
            'previous':     result['previous'],
            'message':      f"Jurisdiction set to {result['label']}.",
        }
    except ValueError as e:
        return {
            'status':           'error',
            'message':          str(e),
            'valid_options':    list(VALID_JURISDICTIONS.keys()),
            'valid_labels':     VALID_JURISDICTIONS,
        }


def get_jurisdiction() -> dict:
    """Tool: check the current session jurisdiction."""
    session = get_active_session()
    return session.get_jurisdiction()


def list_valid_jurisdictions() -> dict:
    """Tool: return all valid jurisdictions with human-readable labels."""
    return {
        'jurisdictions': VALID_JURISDICTIONS,
        'count':         len(VALID_JURISDICTIONS),
    }
