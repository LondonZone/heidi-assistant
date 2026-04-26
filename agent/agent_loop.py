"""
Agent loop — orchestrates the Claude tool_use conversation.

This is where the agent becomes real. It:
1. Takes a clinician query
2. Sends it to Claude with the system prompt, conversation history, and tool definitions
3. When Claude returns a tool_use block, dispatches to the matching Python function
4. Returns the tool result to Claude
5. Loops until Claude returns a final text response
6. Logs the entire exchange to the audit trail
"""

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

from agent.session       import get_active_session
from agent.system_prompt import get_system_prompt
from tools.tool_definitions import TOOLS, get_tool_dispatch
from tools.audit_logger  import log_tool_call, log_clinician_turn, log_safety_event


load_dotenv()


# Anthropic client — lazy-initialised so tests can run without API key
_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not found in environment. "
                "Set it in .env or export it before running the agent."
            )
        _client = Anthropic(api_key=api_key)
    return _client


MODEL = 'claude-sonnet-4-5-20250929'
MAX_TOKENS_PER_TURN = 2000
MAX_TOOL_ITERATIONS = 15  # safety limit on tool_use loops


def _dispatch_tool_call(tool_name: str, tool_input: dict) -> dict:
    """Look up the Python function for a tool name and invoke it with the given input."""
    dispatch = get_tool_dispatch()

    if tool_name not in dispatch:
        return {
            'status':  'error',
            'message': f"Unknown tool: {tool_name}. Known tools: {list(dispatch.keys())}",
        }

    fn = dispatch[tool_name]
    try:
        result = fn(**tool_input)
    except TypeError as e:
        return {
            'status':  'error',
            'message': f"Tool {tool_name} rejected inputs: {e}",
            'inputs':  tool_input,
        }
    except Exception as e:
        return {
            'status':  'error',
            'message': f"Tool {tool_name} raised {type(e).__name__}: {e}",
            'inputs':  tool_input,
        }

    return result


def _format_tool_result_for_claude(tool_use_id: str, result) -> dict:
    """Convert a Python tool return value into the format Claude expects."""
    # Claude expects content as string or list of blocks
    if isinstance(result, (dict, list)):
        content = json.dumps(result, default=str)
    else:
        content = str(result)

    return {
        'type':        'tool_result',
        'tool_use_id': tool_use_id,
        'content':     content,
    }


def run_agent_turn(clinician_message: str, max_iterations: int = MAX_TOOL_ITERATIONS) -> dict:
    """
    Run one full agent turn:
    - Add clinician message to conversation
    - Call Claude with tools
    - Handle tool_use iterations
    - Add final assistant response to conversation
    - Log everything
    """
    session = get_active_session()
    client  = _get_client()

    # Add the clinician message to the session conversation
    session.add_message('user', clinician_message)

    # Build the system prompt with current session context
    system_prompt = get_system_prompt(session=session)

    # Tools metadata tracking
    tools_called_this_turn = []
    final_text_response = None
    iteration = 0

    # Conversation for Claude API — history + current message
    api_messages = session.get_conversation_for_claude()

    while iteration < max_iterations:
        iteration += 1

        # Call Claude
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS_PER_TURN,
                system=system_prompt,
                tools=TOOLS,
                messages=api_messages,
            )
        except Exception as e:
            error_msg = f"API call failed: {type(e).__name__}: {e}"
            log_safety_event('api_error', {'error': error_msg, 'iteration': iteration})
            session.add_message('assistant', f"Error: {error_msg}")
            return {
                'status':  'error',
                'message': error_msg,
                'response_text': None,
                'tools_called':  tools_called_this_turn,
            }

        # Claude's response is a list of content blocks (text and/or tool_use)
        stop_reason = response.stop_reason
        content_blocks = response.content

        # Check if Claude wants to use tools
        tool_use_blocks = [b for b in content_blocks if b.type == 'tool_use']
        text_blocks     = [b for b in content_blocks if b.type == 'text']

        if stop_reason == 'tool_use' and tool_use_blocks:
            # Append Claude's partial response (containing tool_use) to messages
            api_messages.append({
                'role':    'assistant',
                'content': [b.model_dump() for b in content_blocks],
            })

            # Execute each tool and collect results
            tool_results = []
            for tool_block in tool_use_blocks:
                tool_name  = tool_block.name
                tool_input = tool_block.input
                tool_id    = tool_block.id

                # Dispatch the tool
                result = _dispatch_tool_call(tool_name, tool_input)

                # Log the tool call
                log_tool_call(tool_name, tool_input, result)
                tools_called_this_turn.append({
                    'tool':   tool_name,
                    'input':  tool_input,
                    'status': result.get('status') if isinstance(result, dict) else 'raw',
                })

                tool_results.append(_format_tool_result_for_claude(tool_id, result))

            # Append tool results as the next user message
            api_messages.append({
                'role':    'user',
                'content': tool_results,
            })

            # Loop again — Claude may want to call more tools or give final response
            continue

        # No tool_use — Claude has produced a final response
        if text_blocks:
            final_text_response = ''.join(b.text for b in text_blocks)
        else:
            final_text_response = '(No response text returned.)'

        # Append final assistant message to session
        session.add_message('assistant', final_text_response)

        break

    else:
        # Hit max iterations without Claude finishing
        warning = (
            f"Agent hit max tool iterations ({max_iterations}) without final response. "
            f"This may indicate a tool loop issue."
        )
        log_safety_event('max_iterations_hit', {
            'iterations':    iteration,
            'tools_called':  tools_called_this_turn,
        })
        final_text_response = (
            "I apologise — I wasn't able to complete this request within the tool-use budget. "
            "Please try rephrasing or breaking the question into smaller parts."
        )
        session.add_message('assistant', final_text_response)

    # Log the full turn
    log_clinician_turn(
        query=clinician_message,
        response=final_text_response,
        tools_called=[t['tool'] for t in tools_called_this_turn],
    )

    return {
        'status':        'success',
        'response_text': final_text_response,
        'tools_called':  tools_called_this_turn,
        'iterations':    iteration,
    }


def reset_agent():
    """Reset the session — used for starting a new clinical case or testing."""
    from agent.session import reset_session
    reset_session()
