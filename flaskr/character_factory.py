"""
Character Factory - Builds properly initialized D&D 5e characters

Handles:
1. Class and Species selection from D&D 5e API
2. Ability score generation (or from user input)
3. Proficiency setup based on class/species
4. Default equipment and skill initialization
"""

from typing import Dict, Any, List, Optional
from flaskr.character import Character, SKILL_ABILITY_MAP
from flaskr.data.base_classes import DndClass
from flaskr.data.base_species import DndSpecies, ABILITY_ORDER
from content_registry import ContentRegistry

def create_character(
    name: str,
    class_name: str,
    species_name: str,
    ability_scores: Optional[List[int]] = None,
) -> Character:
    """
    Create a new D&D 5e character with proper initialization.
    
    Args:
        name: Character name
        class_name: D&D class (e.g., 'Cleric')
        species_name: D&D species/race (e.g., 'Tiefling')
        ability_scores: Optional [STR, DEX, CON, INT, WIS, CHA]. 
                       Defaults to [10, 10, 10, 10, 10, 10]
    
    Returns:
        Character object with all fields initialized
    
    Raises:
        ValueError: If class or species not found
    """
    
    # Load class and species from API/cache
    dnd_class = ContentRegistry.get_class(class_name)
    dnd_species = DndSpecies(species_name)
    
    # Default ability scores
    if ability_scores is None:
        ability_scores = [10, 10, 10, 10, 10, 10]
    
    # Create base character data
    character_data = {
        "name": name,
        "class": class_name,
        "species": species_name,
        "level": 1,
        "experience": 0,
        
        # Abilities
        "ability_scores": ability_scores.copy(),  # [STR, DEX, CON, INT, WIS, CHA]
        "modifiers": _calculate_modifiers(ability_scores),
        
        # Core stats
        "hit_die": dnd_class.hit_die,
        "max_hit_points": dnd_class.hit_die,
        "hit_points": dnd_class.hit_die,
        "hit_dice_used": 0,
        "armor_class": 10,
        "initiative": 0,
        "speed": 30,
        
        # Proficiencies
        "proficiency_bonus": 2,
        "proficiencies": dnd_class.get_starting_proficiencies(),
        "proficiency_choices": dnd_class.get_proficiency_choices(),
        
        # Skills (all unproficient initially)
        "skills": _initialize_skills(ability_scores),
        
        # Saving throws (all unproficient initially)
        "saving_throws": _initialize_saving_throws(ability_scores),
        
        # Spellcasting
        "spellcasting_ability": dnd_class.get_spellcasting_ability(),
        "spell_slots": {
            f"level_{i}": 0 for i in range(1, 10)
        },
        "spells": [],
        
        # Actions
        "actions": [],
        "bonus_actions": [],
        "reactions": [],
        
        # Inventory
        "inventory": {
            "armor": None,
            "weapons": [],
            "equipped_items": [],
            "backpack": []
        },
        "attunement_slots": 3,  # Standard, some classes scale this
        "attuned_items": [],
        
        # Character traits & info
        "languages": dnd_species.get_languages(),
        "personality_traits": "",
        "ideals": "",
        "bonds": "",
        "flaws": "",
        "backstory": "",
        "appearance": "",
        "allies": [],
        "enemies": [],
        
        # Metadata
        "version": "5e",
        "created_at": None,  # Set by database
    }
    
    # Apply species modifiers (ability scores, speed, languages)
    character_data = dnd_species.apply_to_character(character_data)
    
    # Recalculate after species modifiers
    character_data["modifiers"] = _calculate_modifiers(character_data["ability_scores"])
    character_data["max_hit_points"] = dnd_class.hit_die + character_data["modifiers"][2]  # HD + CON
    character_data["hit_points"] = character_data["max_hit_points"]
    
    # Recalculate skills and saves with updated modifiers
    character_data["skills"] = _initialize_skills(character_data["ability_scores"])
    character_data["saving_throws"] = _initialize_saving_throws(character_data["ability_scores"])
    
    return Character(character_data)


def _calculate_modifiers(ability_scores: List[int]) -> List[int]:
    """
    Calculate ability modifiers from scores.
    
    D&D 5e formula: (score - 10) // 2
    """
    return [
        (score - 10) // 2
        for score in ability_scores
    ]


def _initialize_skills(ability_scores: List[int]) -> Dict[str, tuple]:
    """
    Initialize all skills unproficient with correct modifiers.
    
    Args:
        ability_scores: [STR, DEX, CON, INT, WIS, CHA]
    
    Returns:
        Dict mapping skill names to (is_proficient, modifier) tuples
    """
    modifiers = _calculate_modifiers(ability_scores)
    return {
        skill: (False, modifiers[ability_idx])
        for skill, ability_idx in SKILL_ABILITY_MAP.items()
    }


def _initialize_saving_throws(ability_scores: List[int]) -> Dict[str, tuple]:
    """
    Initialize all saving throws unproficient with correct modifiers.
    
    Args:
        ability_scores: [STR, DEX, CON, INT, WIS, CHA]
    
    Returns:
        Dict mapping ability names to (is_proficient, modifier) tuples
    """
    modifiers = _calculate_modifiers(ability_scores)
    return {
        ability: (False, modifiers[idx])
        for idx, ability in enumerate(ABILITY_ORDER)
    }


def apply_class_proficiencies(character: Character, class_choices: Optional[Dict[str, List[str]]] = None) -> None:
    """
    Apply class proficiency selections to character.
    
    Handles proficiency choices that require user input (e.g., "Choose 2 skills").
    
    Args:
        character: Character object to update
        class_choices: Dict like:
            {
                'skill_choice_0': ['acrobatics', 'animal_handling'],  # User selected 2 skills
                'saving_throw_choice_0': ['wisdom'],
            }
    """
    if not class_choices:
        return
    
    # Process skill proficiency selections
    for choice_key, selected_skills in class_choices.items():
        if 'skill' in choice_key.lower():
            for skill in selected_skills:
                character.set_skill_proficiency(skill, proficient=True)
    
    # Process saving throw selections
    for choice_key, selected_abilities in class_choices.items():
        if 'save' in choice_key.lower() or 'throw' in choice_key.lower():
            for ability in selected_abilities:
                character.set_saving_throw_proficiency(ability, proficient=True)


def apply_species_proficiencies(character: Character, species_name: str) -> None:
    """
    Apply species proficiencies directly (they don't have choices).
    
    Args:
        character: Character object to update
        species_name: Species name (used to load from API)
    """
    # Most D&D 5e species don't grant skill proficiencies
    # This is a placeholder for futures (e.g., Half-Elf getting +2 to two abilities)
    pass


def level_up(character: Character) -> Dict[str, Any]:
    """
    Level up a character and return gained features/benefits.
    
    Args:
        character: Character to level up
    
    Returns:
        Dict with level-up information:
        {
            'old_level': 1,
            'new_level': 2,
            'hp_gained': 5,
            'proficiency_bonus_increased': False,
            'new_features': ['Fighting Style'],
        }
    """
    old_level = character.data['level']
    old_proficiency = character.calculate_proficiency_bonus()
    
    character.data['level'] += 1
    new_proficiency = character.calculate_proficiency_bonus()
    
    # Calculate HP gain
    hit_die = character.data['hit_die']
    con_mod = character.data['modifiers'][2]
    hp_gain = max(1, __import__('random').randint(1, hit_die) + con_mod)
    character.data['max_hit_points'] += hp_gain
    character.data['hit_points'] = character.data['max_hit_points']
    
    # Reset hit dice counter on long rest (not exactly here, but for MVP)
    total_hit_dice = old_level  # Can use 1 per level
    character.data['hit_dice_used'] = 0
    
    return {
        'old_level': old_level,
        'new_level': character.data['level'],
        'hp_gained': hp_gain,
        'proficiency_bonus_increased': new_proficiency > old_proficiency,
        'proficiency_bonus': new_proficiency,
        'new_features': [],  # Would fetch from class features API
    }
