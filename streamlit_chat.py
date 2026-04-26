"""
Streamlit chat UI for Heidi Clinical Decision Support.
Note-first flow: clinician pastes a clinical note, agent analyses proactively.
Conversational follow-ups supported after initial analysis.
"""

import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title='Heidi Clinical Decision Support',
    page_icon='🩺',
    layout='wide',
)

from agent.session import get_active_session, reset_session, VALID_JURISDICTIONS
from tools.jurisdiction import set_jurisdiction
from agent.agent_loop import run_agent_turn

# ============================================================
# SESSION STATE INITIALISATION
# ============================================================

if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'agent_initialised' not in st.session_state:
    reset_session()
    st.session_state.agent_initialised = True

if 'note_analysed' not in st.session_state:
    st.session_state.note_analysed = False

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown('## 🩺 Heidi CDS')
    st.caption('Clinical Decision Support — MVP')
    st.divider()

    # Jurisdiction selector
    st.markdown('### Jurisdiction')
    agent_session = get_active_session()
    current_jurisdiction = agent_session.jurisdiction

    if current_jurisdiction is None:
        st.warning('⚠️ Set jurisdiction to begin')
    else:
        st.success(f'✓ {VALID_JURISDICTIONS[current_jurisdiction]}')

    jurisdiction_options = [''] + list(VALID_JURISDICTIONS.keys())
    jurisdiction_labels = {
        '':                  '— Select —',
        'AUS_RCH_MELBOURNE': '🇦🇺 RCH Melbourne (paediatric)',
        'AUS_TG':            '🇦🇺 Therapeutic Guidelines AU (adult)',
        'CAN_CHEO_OTTAWA':   '🇨🇦 CHEO Ottawa (paediatric)',
        'CAN_CPS':           '🇨🇦 Canadian Paediatric Society',
        'UK_NICE':           '🇬🇧 NICE UK',
        'INTERNATIONAL':     '🌐 International consensus',
    }

    selected = st.selectbox(
        'Institution / region',
        options=jurisdiction_options,
        format_func=lambda x: jurisdiction_labels.get(x, x),
        index=0 if current_jurisdiction is None else jurisdiction_options.index(current_jurisdiction),
    )

    if selected and selected != current_jurisdiction:
        set_jurisdiction(selected, reason='ui_selection')
        st.rerun()

    st.divider()

    # Session info
    st.markdown('### Session')
    st.caption(f'Messages: {len(st.session_state.messages)}')
    if agent_session.jurisdiction:
        st.caption(f'Jurisdiction: {agent_session.jurisdiction}')
    st.caption(f'Session: `{agent_session.session_id[:8]}...`')

    if st.button('🔄 New session', use_container_width=True):
        reset_session()
        st.session_state.messages = []
        st.session_state.note_analysed = False
        st.session_state.agent_initialised = False
        st.rerun()

    st.divider()

    # Available guidelines
    st.markdown('### Available guidelines')
    st.markdown(
        '**Croup (paediatric)**\n'
        '- 🇦🇺 RCH Melbourne\n'
        '- 🇨🇦 CHEO Ottawa\n'
        '- 🇬🇧 NICE UK\n\n'
        '**Hypertension (adult)**\n'
        '- 🇦🇺 Therapeutic Guidelines AU\n'
        '- 🇬🇧 NICE UK\n\n'
        '**Anaphylaxis**\n'
        '- 🌐 International (WAO/ASCIA)'
    )

    st.divider()
    st.caption('Production would add: vector DB, hospital APIs, EMR integration, live guideline sync.')

# ============================================================
# MAIN PANEL
# ============================================================

st.markdown('# 🩺 Heidi Clinical Decision Support')
st.caption('Context-aware · Evidence-aligned · Jurisdiction-specific')

# Jurisdiction warning banner
if current_jurisdiction is None:
    st.warning(
        '**No jurisdiction selected.** Choose your institution in the sidebar before '
        'requesting clinical recommendations. Guidelines vary significantly by region — '
        'using the wrong one is a patient safety risk.'
    )

st.divider()

# Two-column layout: note input (left) + conversation (right)
col_note, col_chat = st.columns([1, 1], gap='large')

# ---- LEFT COLUMN: Clinical note input ----
with col_note:
    st.markdown('### Clinical note')
    st.caption('Paste a clinical note or describe the case. The agent will proactively surface relevant recommendations.')

    default_note = st.session_state.pop('_loaded_note', '')
    note_text = st.text_area(
        label='Clinical note',
        height=280,
        value=default_note,
        placeholder=(
            'Example:\n\n'
            '3-year-old, 14kg. Presents with 2-day barky cough and stridor at rest. '
            'Mild suprasternal recession. SpO2 97% room air. '
            'No known allergies, no current medications.\n\n'
            'Or paste a full clinical note...'
        ),
        label_visibility='collapsed',
    )

    analyse_disabled = current_jurisdiction is None or not note_text.strip()

    if st.button(
        '🔍 Analyse note',
        use_container_width=True,
        disabled=analyse_disabled,
        type='primary',
    ):
        with st.spinner('Analysing clinical note...'):
            prompt = (
                f'I am going to paste a clinical note. Please analyse it and '
                f'surface the relevant clinical decision support — identify the condition, '
                f'assess severity if applicable, check escalation criteria, and provide '
                f'a guideline-based recommendation including dose calculation where relevant. '
                f'Gather any safety context you need before recommending a medication.\n\n'
                f'CLINICAL NOTE:\n{note_text}'
            )

            result = run_agent_turn(prompt)

            # Clear previous messages — new note replaces old analysis
            # Follow-up questions accumulate after this point
            st.session_state.messages = []
            st.session_state.messages.append({
                'role':    'user',
                'content': '[Clinical note analysed]',
                'note':    note_text,
            })
            st.session_state.messages.append({
                'role':         'assistant',
                'content':      result['response_text'],
                'tools_called': [t['tool'] for t in result['tools_called']],
                'iterations':   result['iterations'],
            })
            st.session_state.note_analysed = True
            st.rerun()

    if analyse_disabled and current_jurisdiction is None:
        st.caption('⚠️ Set jurisdiction in sidebar first')
    elif analyse_disabled:
        st.caption('Enter a clinical note above')

    # Quick example buttons
    st.markdown('#### Quick examples')
    col_ex1, col_ex2 = st.columns(2)

    with col_ex1:
        if st.button('🧒 Croup (paediatric)', use_container_width=True):
            st.session_state['example_note'] = (
                'Patient: 3yo, weight 14kg\n'
                'Presenting with 2-day barky cough, hoarse voice. '
                'Stridor at rest this morning with mild suprasternal and intercostal recession. '
                'RR 32, HR 124, SpO2 97% room air, T 37.9C. '
                'Clear air entry bilaterally. No cyanosis.\n'
                'Assessment: Moderate viral croup.\n'
                'No known allergies, no current medications.'
            )
            st.rerun()

        if st.button('🚨 Anaphylaxis', use_container_width=True):
            st.session_state['example_note'] = (
                'Adult patient, approx 35yo. '
                'Collapsed 10 minutes after eating at a restaurant. '
                'Urticaria over trunk, tongue swelling, audible stridor. '
                'BP 75/45, HR 132, SpO2 93%. '
                'Suspected anaphylaxis — nut allergy documented.'
            )
            st.rerun()

    with col_ex2:
        if st.button('💊 Hypertension (adult)', use_container_width=True):
            st.session_state['example_note'] = (
                'Patient: 58yo male\n'
                'Stage 1 hypertension confirmed on ABPM (average 148/92).\n'
                'No CKD, no diabetes, no previous CVD.\n'
                'Current medications: ibuprofen 400mg PRN for knee osteoarthritis.\n'
                'No known drug allergies.\n'
                'Considering starting antihypertensive therapy.'
            )
            st.rerun()

        if st.button('⚠️ No jurisdiction', use_container_width=True):
            reset_session()
            st.session_state.messages = []
            st.session_state.note_analysed = False
            st.session_state.agent_initialised = False
            st.rerun()

    # Load example note if selected
    if 'example_note' in st.session_state and st.session_state['example_note']:
        loaded_note = st.session_state.pop('example_note')
        st.session_state['_loaded_note'] = loaded_note
        st.rerun()

# ---- RIGHT COLUMN: Conversation ----
with col_chat:
    st.markdown('### Decision support')
    st.caption('Agent responses appear here. Ask follow-up questions below.')

    # Message history
    chat_container = st.container(height=420)
    with chat_container:
        if not st.session_state.messages:
            if current_jurisdiction:
                st.info(
                    f'Ready. Using **{VALID_JURISDICTIONS[current_jurisdiction]}** guidelines.\n\n'
                    f'Paste a clinical note on the left and click **Analyse note** to begin, '
                    f'or type a question below.'
                )
            else:
                st.info('Select a jurisdiction in the sidebar to begin.')
        else:
            for msg in st.session_state.messages:
                if msg['role'] == 'user':
                    if msg.get('note'):
                        with st.chat_message('user', avatar='👩‍⚕️'):
                            st.caption('Clinical note submitted')
                            with st.expander('View note'):
                                st.text(msg.get('note', ''))
                    else:
                        with st.chat_message('user', avatar='👩‍⚕️'):
                            st.write(msg['content'])
                else:
                    with st.chat_message('assistant', avatar='🩺'):
                        st.markdown(msg['content'])
                        if msg.get('tools_called'):
                            with st.expander(f'🔧 {len(msg["tools_called"])} tool calls, {msg.get("iterations", "?")} iterations'):
                                st.caption('Tools used by agent:')
                                for tool in msg['tools_called']:
                                    st.caption(f'  • {tool}')

    # Follow-up input
    st.markdown('#### Follow-up question')
    follow_up = st.chat_input(
        placeholder='Ask a follow-up — e.g. "What if the child is allergic to dexamethasone?" or "What are the discharge criteria?"',
        disabled=current_jurisdiction is None,
    )

    if follow_up:
        with st.spinner('Thinking...'):
            result = run_agent_turn(follow_up)

            st.session_state.messages.append({
                'role':    'user',
                'content': follow_up,
            })
            st.session_state.messages.append({
                'role':         'assistant',
                'content':      result['response_text'],
                'tools_called': [t['tool'] for t in result['tools_called']],
                'iterations':   result['iterations'],
            })
            st.rerun()
