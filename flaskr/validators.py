from typing import Dict, All

HOMEBREW_CLASS_SCHEMA = {
    "name": str,
    "hit_die": int,  # 6, 8, 10, 12
    "proficiencies": dict,
    "proficiency_choices": list,
    "spellcasting_ability": str or None,
}

HOMEBREW_SPECIES_SCHEMA = {
    "name": str,
    "ability_modifiers": dict,  # {'strength': 2, ...}
    "speed": int,
    "languages": list,
    "traits": list,
}

def validate_homebrew_class(data: Dict) -> Tuple[bool, str]:
    """
    Returns: (is_valid, error_message_or_empty_string)
    """
    try:
        assert isinstance(data.get('name'), str), "Missing or invalid 'name'"
        assert isinstance(data.get('hit_die'), int), "Missing or invalid 'hit_die'"
        assert 6 <= data['hit_die'] <= 12, "Hit die must be 6-12"
        assert isinstance(data.get('proficiencies'), dict), "Missing or invalid 'proficiencies'"
        return True, ""
    except AssertionError as e:
        return False, str(e)

def sanitize_homebrew(data: Dict) -> Dict:
    """Remove/fix any dangerous or invalid data"""
    # Limit field lengths
    data['name'] = data['name'][:50]
    # Ensure proper types
    data['hit_die'] = min(max(int(data['hit_die']), 6), 12)
    # Remove unknown fields
    return {k: v for k, v in data.items() if k in HOMEBREW_CLASS_SCHEMA}