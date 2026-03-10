"""
D&D 5e Species (Races) fetched from official D&D 5e API.
Transforms API data to match character.py expectations.

Applies ability modifiers, languages, and speed to characters.
Caches data locally to minimize API calls.

API Reference: https://www.dnd5eapi.co/docs/api/races
"""

from typing import Dict, List, Optional, Any
from flaskr.data.api_utils import get_cached_or_fetch, get_all_available_species


# Map API ability shorthand to full names
ABILITY_MAP = {
    'str': 'strength',
    'dex': 'dexterity',
    'con': 'constitution',
    'int': 'intelligence',
    'wis': 'wisdom',
    'cha': 'charisma'
}

# Standard ability order in character sheets
ABILITY_ORDER = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']


class DndSpecies:
    """
    Represents a D&D 5e Character Species (Race).
    
    Fetches from official D&D 5e API and caches locally.
    Provides ability modifiers, traits, languages, and speed.
    """
    
    def __init__(self, name: str):
        """
        Initialize a D&D species.
        
        Args:
            name: Species name (e.g., "Tiefling", "Half-Orc")
            
        Raises:
            ValueError: If species not found in API
        """
        # Fetch from API (with local caching)
        self.api_data = get_cached_or_fetch('race', name.lower(), f'races/{name.lower()}')
        
        if not self.api_data:
            raise ValueError(f"❌ Species '{name}' not found (API error or not yet in D&D 5e SRD)")
        
        self.name = self.api_data.get('name', name)
        self.index = self.api_data.get('index', name.lower())
    
    def get_ability_modifiers(self) -> Dict[str, int]:
        """
        Get ability score modifiers for this species.
        
        Returns:
            Dict mapping ability names to modifiers:
            {'strength': 2, 'charisma': 2, ...}
        """
        mods = {}
        
        for ability_set in self.api_data.get('ability_bonuses', []):
            ability_name = ability_set.get('ability_score', {}).get('name', '')
            ability_name_lower = ability_name.lower()
            
            if ability_name_lower in ABILITY_MAP.values():
                mods[ability_name_lower] = ability_set.get('bonus', 0)
        
        return mods
    
    def get_speed(self) -> int:
        """
        Get base walking speed in feet.
        
        Returns:
            Speed value (typically 30)
        """
        return self.api_data.get('speed', 30)
    
    def get_languages(self) -> List[str]:
        """
        Get starting languages for this species.
        
        Returns:
            List of language names (e.g., ['Common', 'Infernal'])
        """
        languages = []
        
        for lang in self.api_data.get('languages', []):
            languages.append(lang.get('name', ''))
        
        return [lang for lang in languages if lang]  # Filter empty strings
    
    def get_traits(self) -> List[Dict[str, str]]:
        """
        Get species traits (darkvision, special abilities, etc).
        
        Returns:
            List of trait dicts with 'name' and 'desc'
        """
        traits = []
        
        for trait in self.api_data.get('traits', []):
            traits.append({
                'name': trait.get('name', 'Unknown Trait'),
                'desc': trait.get('desc', '')
            })
        
        return traits
    
    def apply_to_character(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply species modifiers to character data dict.
        
        Modifies:
        - ability_scores: Adds species modifiers
        - speed: Sets to species base speed
        - languages: Adds species starting languages
        
        Args:
            character_data: Character dict to modify
        
        Returns:
            Modified character_data dict
        """
        # Apply ability modifiers
        mods = self.get_ability_modifiers()
        for ability, mod in mods.items():
            idx = ABILITY_ORDER.index(ability)
            character_data['ability_scores'][idx] += mod
        
        # Set speed
        character_data['speed'] = self.get_speed()
        
        # Add languages
        character_data['languages'] = self.get_languages()
        
        # Store species info
        character_data['species'] = self.name
        character_data['species_traits'] = self.get_traits()
        
        return character_data
    
    def to_character_dict(self) -> Dict[str, Any]:
        """
        Convert species data to format for character initialization.
        
        Returns:
            Dict with species, ability mods, and traits
        """
        return {
            'species': self.name,
            'ability_modifiers': self.get_ability_modifiers(),
            'speed': self.get_speed(),
            'languages': self.get_languages(),
            'traits': self.get_traits()
        }
    
    @staticmethod
    def get_available_species() -> List[str]:
        """
        Get list of all available D&D 5e species.
        
        Returns:
            List of species names
        """
        return get_all_available_species()


# Convenience function for getting a species
def load_species(name: str) -> DndSpecies:
    """Load a D&D species by name"""
    return DndSpecies(name)
