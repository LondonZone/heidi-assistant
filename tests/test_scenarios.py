"""
Comprehensive scenario tests — every demo path the Loom will show.

Run with: python3 tests/test_scenarios.py

Each scenario tests a specific architectural feature:
1. Paediatric croup happy path — full safety chain
2. Jurisdiction variance — same patient, different region, different dose
3. Adult hypertension with NSAID interaction — drug-class safety
4. Missing jurisdiction refusal — first safety gate
5. Anaphylaxis emergency — escalation priority
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.session import reset_session
from tools.jurisdiction import set_jurisdiction
from agent.agent_loop import run_agent_turn


def divider(title=''):
    print()
    print('=' * 70)
    if title:
        print(title)
        print('=' * 70)


def show_result(scenario, result):
    print()
    print('RESPONSE:')
    print(result['response_text'])
    print()
    tools = [t['tool'] for t in result['tools_called']]
    statuses = [t['status'] for t in result['tools_called']]
    print(f'Tools called ({len(tools)}): {tools}')
    print(f'Tool statuses: {statuses}')
    print(f'Iterations: {result["iterations"]}')


def scenario_1_paediatric_croup_happy_path():
    divider('SCENARIO 1: Paediatric croup happy path (CHEO Ottawa)')
    reset_session()
    set_jurisdiction('CAN_CHEO_OTTAWA')

    query = (
        '3-year-old, 14kg, presents with barky cough and stridor at rest. '
        'Mild suprasternal recession, SpO2 97% room air. '
        'No allergies, no current medications. '
        'What is the management?'
    )
    print(f'QUERY: {query}')
    result = run_agent_turn(query)
    show_result(1, result)
    return result


def scenario_2_jurisdiction_variance():
    divider('SCENARIO 2: Same case, UK NICE jurisdiction (different dose expected)')
    reset_session()
    set_jurisdiction('UK_NICE')

    query = (
        '3-year-old, 14kg, moderate croup with stridor at rest. '
        'No allergies, no current medications. '
        'What dose of dexamethasone should I give?'
    )
    print(f'QUERY: {query}')
    result = run_agent_turn(query)
    show_result(2, result)
    return result


def scenario_3_hypertension_with_interaction():
    divider('SCENARIO 3: Adult hypertension with NSAID interaction (UK NICE)')
    reset_session()
    set_jurisdiction('UK_NICE')

    query = (
        '52-year-old male, BP 165/95 confirmed with ABPM. '
        'No previous CKD, takes ibuprofen 400mg PRN for knee pain. '
        'No known drug allergies. '
        'Starting first-line antihypertensive — what should I prescribe and what should I tell the patient about the ibuprofen?'
    )
    print(f'QUERY: {query}')
    result = run_agent_turn(query)
    show_result(3, result)
    return result


def scenario_4_missing_jurisdiction_refusal():
    divider('SCENARIO 4: No jurisdiction set — safety gate refusal')
    reset_session()
    # Deliberately no set_jurisdiction call

    query = 'Give me the dexamethasone dose for a 3-year-old with moderate croup.'
    print(f'QUERY: {query}')
    result = run_agent_turn(query)
    show_result(4, result)
    return result


def scenario_5_anaphylaxis_emergency():
    divider('SCENARIO 5: Anaphylaxis emergency (international consensus)')
    reset_session()
    set_jurisdiction('INTERNATIONAL')

    query = (
        'Adult patient just collapsed after suspected nut exposure. '
        'Tongue swelling, audible stridor, BP 80/50, weak pulse. '
        'What do I do RIGHT NOW?'
    )
    print(f'QUERY: {query}')
    result = run_agent_turn(query)
    show_result(5, result)
    return result


def main():
    print()
    print('HEIDI CLINICAL DECISION SUPPORT — END-TO-END SCENARIO TESTS')
    print('Approximate total cost: $0.15 (5 agent turns, average 3 iterations each)')
    print()

    results = {}
    results[1] = scenario_1_paediatric_croup_happy_path()
    results[2] = scenario_2_jurisdiction_variance()
    results[3] = scenario_3_hypertension_with_interaction()
    results[4] = scenario_4_missing_jurisdiction_refusal()
    results[5] = scenario_5_anaphylaxis_emergency()

    # Summary
    divider('SUMMARY')
    print()
    print(f"{'Scenario':<10} {'Iterations':<12} {'Tools called':<14} {'Response length'}")
    print('-' * 70)
    for n, r in results.items():
        if r:
            print(
                f"{n:<10} "
                f"{r['iterations']:<12} "
                f"{len(r['tools_called']):<14} "
                f"{len(r['response_text']) if r['response_text'] else 0} chars"
            )
    print()
    print('All scenarios complete. Review the responses above to confirm:')
    print('- Scenario 1: 8.4mg oral dex per CHEO, full management plan')
    print('- Scenario 2: 2.1mg oral dex per NICE (different dose, same patient)')
    print('- Scenario 3: ACE inhibitor recommended, NSAID interaction flagged')
    print('- Scenario 4: Refusal asking for jurisdiction, no clinical content')
    print('- Scenario 5: Adrenaline 0.5mg IM, escalation priority, no dosing prelude')


if __name__ == '__main__':
    main()
