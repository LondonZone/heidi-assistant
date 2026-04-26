"""
Dose calculator — CLINICAL SAFETY BOUNDARY, DETERMINISTIC ZONE.

This tool is the architectural core. It refuses to calculate if:
- Jurisdiction not set
- Required parameters missing (weight, age for paediatric)
- Weight or age implausible
- No dose rule exists for this drug/condition/severity/jurisdiction combination

Dose rules are keyed by (jurisdiction, condition, severity) and reflect
the actual guideline content in the guidelines/ folder. Changing jurisdiction
genuinely produces different doses — this is the variation the brief asks us
to handle.
"""

from agent.session import get_active_session, VALID_JURISDICTIONS


# ============================================================
# DOSE RULES — keyed by (jurisdiction, condition, severity)
# These reflect the content of the guideline files
# ============================================================

DOSE_RULES = {

    # Croup — AUS RCH Melbourne (tiered dosing)
    ('AUS_RCH_MELBOURNE', 'croup', 'mild'): {
        'drug':            'Dexamethasone',
        'mg_per_kg':       0.15,
        'max_dose_mg':     10,
        'route':           'Oral',
        'frequency':       'single dose',
        'guideline_ref':   'RCH Melbourne Croup Guideline v3.2',
    },
    ('AUS_RCH_MELBOURNE', 'croup', 'moderate'): {
        'drug':            'Dexamethasone',
        'mg_per_kg':       0.30,
        'max_dose_mg':     10,
        'route':           'Oral',
        'frequency':       'single dose',
        'guideline_ref':   'RCH Melbourne Croup Guideline v3.2',
    },
    ('AUS_RCH_MELBOURNE', 'croup', 'severe'): {
        'drug':            'Dexamethasone',
        'mg_per_kg':       0.60,
        'max_dose_mg':     10,
        'route':           'IV/IM',
        'frequency':       'single dose',
        'guideline_ref':   'RCH Melbourne Croup Guideline v3.2',
    },

    # Croup — CAN CHEO Ottawa (single-tier higher dosing)
    ('CAN_CHEO_OTTAWA', 'croup', 'mild'): {
        'drug':            'Dexamethasone',
        'mg_per_kg':       0.6,
        'max_dose_mg':     10,
        'route':           'Oral',
        'frequency':       'single dose',
        'guideline_ref':   'CHEO Croup Pathway v2.1',
    },
    ('CAN_CHEO_OTTAWA', 'croup', 'moderate'): {
        'drug':            'Dexamethasone',
        'mg_per_kg':       0.6,
        'max_dose_mg':     10,
        'route':           'Oral',
        'frequency':       'single dose',
        'guideline_ref':   'CHEO Croup Pathway v2.1',
    },
    ('CAN_CHEO_OTTAWA', 'croup', 'severe'): {
        'drug':            'Dexamethasone',
        'mg_per_kg':       0.6,
        'max_dose_mg':     10,
        'route':           'PO/IV/IM',
        'frequency':       'single dose',
        'guideline_ref':   'CHEO Croup Pathway v2.1',
    },

    # Croup — UK NICE (standard 0.15 mg/kg, higher IM for severe)
    ('UK_NICE', 'croup', 'mild'): {
        'drug':            'Dexamethasone',
        'mg_per_kg':       0.15,
        'max_dose_mg':     10,
        'route':           'Oral',
        'frequency':       'single dose',
        'guideline_ref':   'NICE CKS: Croup (2023)',
        'alternative':     'Prednisolone 1 mg/kg oral if dexamethasone unavailable',
    },
    ('UK_NICE', 'croup', 'moderate'): {
        'drug':            'Dexamethasone',
        'mg_per_kg':       0.15,
        'max_dose_mg':     10,
        'route':           'Oral',
        'frequency':       'single dose',
        'guideline_ref':   'NICE CKS: Croup (2023)',
    },
    ('UK_NICE', 'croup', 'severe'): {
        'drug':            'Dexamethasone',
        'mg_per_kg':       0.6,
        'max_dose_mg':     10,
        'route':           'IM (preferred if cannot tolerate oral)',
        'frequency':       'single dose',
        'guideline_ref':   'NICE CKS: Croup (2023)',
    },

    # Anaphylaxis — international consensus (IM adrenaline, age-banded)
    ('INTERNATIONAL', 'anaphylaxis', 'adult'): {
        'drug':            'Adrenaline (epinephrine)',
        'fixed_dose_mg':   0.5,
        'volume_1_1000':   '0.5 ml',
        'route':           'IM — anterolateral thigh',
        'frequency':       'repeat every 5 min if no improvement',
        'guideline_ref':   'WAO/ASCIA/Resus Council UK Anaphylaxis Guidelines',
        'age_band':        '>=12 years or >=50kg',
    },
    ('INTERNATIONAL', 'anaphylaxis', 'child_6_to_12'): {
        'drug':            'Adrenaline (epinephrine)',
        'fixed_dose_mg':   0.3,
        'volume_1_1000':   '0.3 ml',
        'route':           'IM — anterolateral thigh',
        'frequency':       'repeat every 5 min if no improvement',
        'guideline_ref':   'WAO/ASCIA/Resus Council UK Anaphylaxis Guidelines',
        'age_band':        '6-12 years',
    },
    ('INTERNATIONAL', 'anaphylaxis', 'child_6mo_to_6'): {
        'drug':            'Adrenaline (epinephrine)',
        'fixed_dose_mg':   0.15,
        'volume_1_1000':   '0.15 ml',
        'route':           'IM — anterolateral thigh',
        'frequency':       'repeat every 5 min if no improvement',
        'guideline_ref':   'WAO/ASCIA/Resus Council UK Anaphylaxis Guidelines',
        'age_band':        '6 months - 6 years',
    },

    # Hypertension — adult starting doses
    ('UK_NICE', 'hypertension', 'stage_1_under_55_non_afrocaribbean'): {
        'drug':            'Ramipril',
        'fixed_dose_mg':   2.5,
        'route':           'Oral',
        'frequency':       'once daily',
        'titration':       'up to 10 mg once daily based on response and tolerance',
        'guideline_ref':   'NICE NG136 Hypertension in adults',
        'first_line_class': 'ACE inhibitor',
    },
    ('UK_NICE', 'hypertension', 'stage_1_over_55_or_afrocaribbean'): {
        'drug':            'Amlodipine',
        'fixed_dose_mg':   5,
        'route':           'Oral',
        'frequency':       'once daily',
        'titration':       'up to 10 mg once daily based on response and tolerance',
        'guideline_ref':   'NICE NG136 Hypertension in adults',
        'first_line_class': 'Calcium channel blocker',
    },
    ('AUS_TG', 'hypertension', 'adult_first_line_acei'): {
        'drug':            'Perindopril',
        'fixed_dose_mg':   4,
        'route':           'Oral',
        'frequency':       'once daily',
        'titration':       'up to 8 mg once daily based on response',
        'guideline_ref':   'Therapeutic Guidelines Australia: Cardiovascular',
        'first_line_class': 'ACE inhibitor',
        'note':            'AUS TG permits any of 4 drug classes as first-line (ACEi, ARB, thiazide, CCB)',
    },
}


# ============================================================
# PARAMETER VALIDATION
# ============================================================

def _validate_weight(weight_kg) -> tuple:
    if weight_kg is None:
        return False, 'weight_kg is required for weight-based dosing'
    try:
        w = float(weight_kg)
    except (TypeError, ValueError):
        return False, f'weight_kg must be numeric, got: {weight_kg}'
    if w <= 0:
        return False, f'weight_kg must be positive, got: {w}'
    if w < 1 or w > 250:
        return False, f'weight_kg {w} is outside plausible range (1-250). Please verify.'
    return True, None


def _validate_age(age_years) -> tuple:
    if age_years is None:
        return False, 'age_years is required for safe dosing'
    try:
        a = float(age_years)
    except (TypeError, ValueError):
        return False, f'age_years must be numeric, got: {age_years}'
    if a < 0 or a > 120:
        return False, f'age_years {a} is outside plausible range (0-120). Please verify.'
    return True, None


def _check_age_weight_plausibility(age_years, weight_kg) -> list:
    warnings = []
    a, w = float(age_years), float(weight_kg)
    if a <= 1 and w > 15:
        warnings.append(f'Weight {w}kg unusually high for age {a} years — please verify')
    if 2 <= a <= 5 and w < 8:
        warnings.append(f'Weight {w}kg unusually low for age {a} years — please verify')
    if a >= 12 and w < 25:
        warnings.append(f'Weight {w}kg unusually low for age {a} years — please verify')
    return warnings


# ============================================================
# MAIN TOOL
# ============================================================

def calculate_dose(
    condition:    str,
    severity:     str = None,
    weight_kg:    float = None,
    age_years:    float = None,
    jurisdiction: str = None,
) -> dict:
    session = get_active_session()
    effective_jurisdiction = jurisdiction or session.jurisdiction

    if not effective_jurisdiction:
        return {
            'status':  'refused',
            'reason':  'jurisdiction_not_set',
            'message': (
                'Cannot calculate dose — jurisdiction not set. Different jurisdictions '
                'use different dosing regimens. This is a patient safety requirement.'
            ),
        }

    if effective_jurisdiction not in VALID_JURISDICTIONS:
        return {
            'status':  'refused',
            'reason':  'invalid_jurisdiction',
            'message': f'Invalid jurisdiction: {effective_jurisdiction}',
        }

    condition_clean = condition.lower().strip()
    severity_clean = severity.lower().strip() if severity else None

    age_ok, age_msg = _validate_age(age_years)
    if not age_ok:
        return {
            'status':  'refused',
            'reason':  'parameter_validation_failed',
            'message': age_msg,
            'missing_or_invalid': 'age_years',
        }

    # Anaphylaxis — age-banded
    if condition_clean == 'anaphylaxis':
        age = float(age_years)
        if age >= 12:
            age_band = 'adult'
        elif age >= 6:
            age_band = 'child_6_to_12'
        elif age >= 0.5:
            age_band = 'child_6mo_to_6'
        else:
            return {
                'status':  'refused',
                'reason':  'age_below_guideline_range',
                'message': (
                    f'Patient age {age} years is below the 6-month threshold for '
                    f'standard adrenaline dosing. Use 10 micrograms/kg IM with '
                    f'paediatric consultant oversight.'
                ),
            }

        key = (effective_jurisdiction, 'anaphylaxis', age_band)
        if key not in DOSE_RULES:
            return {
                'status':  'refused',
                'reason':  'no_dose_rule',
                'message': f'No anaphylaxis dose rule for jurisdiction {effective_jurisdiction}',
            }

        rule = DOSE_RULES[key]
        return {
            'status':         'success',
            'drug':           rule['drug'],
            'dose_mg':        rule['fixed_dose_mg'],
            'volume_1_1000':  rule.get('volume_1_1000'),
            'route':          rule['route'],
            'frequency':      rule['frequency'],
            'age_band_used':  age_band,
            'calculation':    f'Age-banded fixed dose — {age_band} = {rule["fixed_dose_mg"]} mg IM',
            'guideline_ref':  rule['guideline_ref'],
            'jurisdiction':   effective_jurisdiction,
            'condition':      condition_clean,
            'time_critical':  True,
            'notes':          ['NO contraindications in anaphylaxis', 'Repeat every 5 min if no improvement'],
        }

    # Weight-based paediatric dosing (croup)
    if condition_clean == 'croup':
        if severity_clean not in ('mild', 'moderate', 'severe'):
            return {
                'status':  'refused',
                'reason':  'severity_required',
                'message': f"Severity required for croup dosing. Must be 'mild', 'moderate', or 'severe'. Got: {severity_clean}",
            }

        weight_ok, weight_msg = _validate_weight(weight_kg)
        if not weight_ok:
            return {
                'status':  'refused',
                'reason':  'parameter_validation_failed',
                'message': weight_msg,
                'missing_or_invalid': 'weight_kg',
            }

        key = (effective_jurisdiction, condition_clean, severity_clean)
        if key not in DOSE_RULES:
            return {
                'status':  'refused',
                'reason':  'no_dose_rule',
                'message': (
                    f'No dose rule for {condition_clean} / {severity_clean} in '
                    f'jurisdiction {effective_jurisdiction}. Available jurisdictions '
                    f'for croup: AUS_RCH_MELBOURNE, CAN_CHEO_OTTAWA, UK_NICE.'
                ),
            }

        rule = DOSE_RULES[key]
        w = float(weight_kg)
        raw_dose = round(w * rule['mg_per_kg'], 2)
        max_dose = rule['max_dose_mg']
        cap_applied = raw_dose > max_dose
        final_dose = min(raw_dose, max_dose)

        warnings = _check_age_weight_plausibility(age_years, weight_kg)

        return {
            'status':              'success',
            'drug':                rule['drug'],
            'dose_mg':             final_dose,
            'raw_dose_mg':         raw_dose,
            'max_dose_cap_applied': cap_applied,
            'max_dose_mg':         max_dose,
            'route':               rule['route'],
            'frequency':           rule['frequency'],
            'calculation':         f'{w}kg x {rule["mg_per_kg"]}mg/kg = {raw_dose}mg' + (f' (capped at {max_dose}mg)' if cap_applied else ''),
            'guideline_ref':       rule['guideline_ref'],
            'jurisdiction':        effective_jurisdiction,
            'condition':           condition_clean,
            'severity':            severity_clean,
            'alternative':         rule.get('alternative'),
            'warnings':            warnings,
        }

    # Adult hypertension
    if condition_clean == 'hypertension':
        if severity_clean is None:
            return {
                'status':  'refused',
                'reason':  'severity_required',
                'message': (
                    'Hypertension dosing requires a staged category. For UK NICE: '
                    'stage_1_under_55_non_afrocaribbean or stage_1_over_55_or_afrocaribbean. '
                    'For AUS TG: adult_first_line_acei (or specify alternative class).'
                ),
            }

        key = (effective_jurisdiction, condition_clean, severity_clean)
        if key not in DOSE_RULES:
            return {
                'status':  'refused',
                'reason':  'no_dose_rule',
                'message': (
                    f'No hypertension dose rule for {severity_clean} in {effective_jurisdiction}. '
                    f'Review guideline for first-line drug class selection before dosing.'
                ),
            }

        rule = DOSE_RULES[key]
        return {
            'status':             'success',
            'drug':               rule['drug'],
            'dose_mg':            rule['fixed_dose_mg'],
            'route':              rule['route'],
            'frequency':          rule['frequency'],
            'titration':          rule.get('titration'),
            'first_line_class':   rule.get('first_line_class'),
            'calculation':        f'Fixed starting dose: {rule["fixed_dose_mg"]}mg (titrate per response)',
            'guideline_ref':      rule['guideline_ref'],
            'jurisdiction':       effective_jurisdiction,
            'condition':          condition_clean,
            'severity':           severity_clean,
            'note':               rule.get('note'),
        }

    return {
        'status':  'refused',
        'reason':  'condition_not_supported',
        'message': (
            f"No dose calculator available for condition '{condition_clean}'. "
            f"Supported: croup, anaphylaxis, hypertension."
        ),
    }
