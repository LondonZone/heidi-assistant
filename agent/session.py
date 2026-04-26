"""
Session state — holds the active jurisdiction and conversation history.
In-memory for MVP. Production would persist to user account.
"""

import uuid
from datetime import datetime

# Valid jurisdictions for this MVP
VALID_JURISDICTIONS = {
    'AUS_RCH_MELBOURNE': "Royal Children's Hospital Melbourne (paediatric)",
    'AUS_TG':             "Therapeutic Guidelines Australia (adult)",
    'CAN_CHEO_OTTAWA':    "CHEO Ottawa (paediatric)",
    'CAN_CPS':            "Canadian Paediatric Society",
    'UK_NICE':            "NICE UK",
    'INTERNATIONAL':      "International consensus (e.g. anaphylaxis)",
}


class Session:
    """Holds state for one clinician session."""

    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.started_at = datetime.utcnow().isoformat() + 'Z'
        self.jurisdiction = None
        self.jurisdiction_set_at = None
        self.jurisdiction_history = []  # track overrides for audit
        self.conversation = []  # list of {role, content} dicts

    def set_jurisdiction(self, jurisdiction_code, reason='user_selection'):
        """Set or change the active jurisdiction."""
        if jurisdiction_code not in VALID_JURISDICTIONS:
            raise ValueError(
                f"Invalid jurisdiction: {jurisdiction_code}. "
                f"Valid options: {list(VALID_JURISDICTIONS.keys())}"
            )

        previous = self.jurisdiction
        self.jurisdiction = jurisdiction_code
        self.jurisdiction_set_at = datetime.utcnow().isoformat() + 'Z'
        self.jurisdiction_history.append({
            'timestamp': self.jurisdiction_set_at,
            'previous':  previous,
            'new':       jurisdiction_code,
            'reason':    reason,
        })

        return {
            'success':      True,
            'jurisdiction': jurisdiction_code,
            'label':        VALID_JURISDICTIONS[jurisdiction_code],
            'previous':     previous,
        }

    def get_jurisdiction(self):
        """Return current jurisdiction or None."""
        if not self.jurisdiction:
            return {
                'jurisdiction': None,
                'is_set':       False,
                'message':      (
                    "No jurisdiction set for this session. "
                    "Clinician must select a jurisdiction before any "
                    "guideline-based recommendations can be made. "
                    f"Valid options: {list(VALID_JURISDICTIONS.keys())}"
                ),
            }

        return {
            'jurisdiction': self.jurisdiction,
            'label':        VALID_JURISDICTIONS[self.jurisdiction],
            'is_set':       True,
            'set_at':       self.jurisdiction_set_at,
        }

    def add_message(self, role, content):
        """Append a message to conversation history."""
        self.conversation.append({
            'role':      role,
            'content':   content,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
        })

    def get_conversation_for_claude(self):
        """Return conversation in Claude API format (strip timestamps)."""
        return [
            {'role': m['role'], 'content': m['content']}
            for m in self.conversation
        ]


# Module-level singleton for CLI/streamlit — one session per process
_active_session = None


def get_active_session():
    """Get or create the active session."""
    global _active_session
    if _active_session is None:
        _active_session = Session()
    return _active_session


def reset_session():
    """Start a new session — used for testing and session restart."""
    global _active_session
    _active_session = Session()
    return _active_session
