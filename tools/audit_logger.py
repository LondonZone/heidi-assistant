"""
Audit logger — exposes append-only logging as a tool the agent can call,
and provides internal logging for tool invocations throughout the system.

Every clinician query, every tool call, every response is captured. This
is the regulatory traceability layer — in production this would feed into
a centralised audit database. For the MVP it's append-only JSONL.
"""

import os
import json
from datetime import datetime
from agent.session import get_active_session


AUDIT_LOG_PATH = 'logs/audit_log.jsonl'


def _ensure_log_dir():
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)


def _write_entry(entry: dict) -> None:
    _ensure_log_dir()
    with open(AUDIT_LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, default=str) + '\n')


def log_event(event_type: str, details: dict = None, tool_name: str = None) -> dict:
    """
    Tool (and internal helper): write an audit entry.

    Called explicitly by the agent for significant clinical events,
    and internally by other tools when they make safety decisions.
    """
    session = get_active_session()

    entry = {
        'timestamp':    datetime.utcnow().isoformat() + 'Z',
        'session_id':   session.session_id,
        'jurisdiction': session.jurisdiction,
        'event_type':   event_type,
        'tool_name':    tool_name,
        'details':      details or {},
    }

    _write_entry(entry)

    return {
        'status':    'logged',
        'timestamp': entry['timestamp'],
        'event_type': event_type,
    }


def log_tool_call(tool_name: str, inputs: dict, outputs: dict) -> None:
    """Internal: record a single tool invocation for audit."""
    log_event(
        event_type='tool_call',
        tool_name=tool_name,
        details={
            'inputs':  inputs,
            'outputs': _summarise_for_audit(outputs),
        },
    )


def log_clinician_turn(query: str, response: str, tools_called: list = None) -> None:
    """Internal: record a full clinician exchange."""
    log_event(
        event_type='clinician_exchange',
        details={
            'query':         query[:500],   # truncate to avoid log bloat
            'response':      response[:2000],
            'tools_called':  tools_called or [],
            'tool_count':    len(tools_called) if tools_called else 0,
        },
    )


def log_safety_event(event: str, details: dict) -> None:
    """Internal: record a safety-gate decision (refusal, escalation, etc.)."""
    log_event(
        event_type=f'safety_{event}',
        details=details,
    )


def _summarise_for_audit(output) -> dict:
    """
    Produce a compact summary of a tool output for audit logging.
    Avoids logging entire guideline text blobs in every entry.
    """
    if not isinstance(output, dict):
        return {'raw': str(output)[:200]}

    summary = {}
    for key, value in output.items():
        # Skip large text fields
        if key == 'content' and isinstance(value, str):
            summary[key] = f'<content {len(value)} chars>'
        elif isinstance(value, str) and len(value) > 300:
            summary[key] = value[:300] + '...[truncated]'
        elif isinstance(value, (dict, list)) and len(str(value)) > 500:
            summary[key] = f'<{type(value).__name__} {len(str(value))} chars>'
        else:
            summary[key] = value
    return summary


def get_audit_log_summary(n_recent: int = 10) -> dict:
    """Tool: return a summary of recent audit entries. Useful for review and testing."""
    _ensure_log_dir()
    if not os.path.exists(AUDIT_LOG_PATH):
        return {
            'status':  'empty',
            'message': 'No audit log entries yet.',
            'entries': [],
        }

    with open(AUDIT_LOG_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    recent = lines[-n_recent:] if n_recent else lines

    parsed_entries = []
    for line in recent:
        line = line.strip()
        if not line:
            continue
        try:
            parsed_entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return {
        'status':        'success',
        'total_entries': len(lines),
        'returned':      len(parsed_entries),
        'entries':       parsed_entries,
    }


def clear_audit_log() -> dict:
    """Testing helper — wipe the audit log. Never exposed as agent tool."""
    _ensure_log_dir()
    if os.path.exists(AUDIT_LOG_PATH):
        os.remove(AUDIT_LOG_PATH)
    return {'status': 'cleared'}
