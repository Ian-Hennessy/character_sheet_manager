"""
D&D 5e Classes fetched from official D&D 5e API.
Transforms API data to match character.py expectations.

Maps API proficiencies to character abilities/skills.
Caches data locally to minimize API calls.

API Reference: https://www.dnd5eapi.co/docs/api/classes
"""

from typing import Dict, List, Tuple, Optional, Any
from flaskr.data.api_utils import get_cached_or_fetch, get_all_available_classes


# Map API proficiency index to character sheet field and value
PROFICIENCY_MAP = {
    # Armor proficiencies
    "light-armor": ("armor", "light"),
    "medium-armor": ("armor", "medium"),
    "heavy-armor": ("armor", "heavy"),
    "simple-weapons": ("weapons", "simple"),
    "martial-weapons": ("weapons", "martial"),
    "hand-crossbows": ("weapons", "hand-crossbow"),
    "greatswords": ("weapons", "greatsword"),
    
    # Saving throws (maps proficiency to ability)
    "saving-throws-dexterity": ("saving_throws", "dexterity"),
    "saving-throws-constitution": ("saving_throws", "constitution"),
    "saving-throws-intelligence": ("saving_throws", "intelligence"),
    "saving-throws-wisdom": ("saving_throws", "wisdom"),
    "saving-throws-charisma": ("saving_throws", "charisma"),
    "saving-throws-strength": ("saving_throws", "strength"),
    
    # Skills (proficiency to skill name)
    "skill-acrobatics": ("skills", "acrobatics"),
    "skill-animal-handling": ("skills", "animal_handling"),
    "skill-arcana": ("skills", "arcana"),
    "skill-athletics": ("skills", "athletics"),
    "skill-deception": ("skills", "deception"),
    "skill-history": ("skills", "history"),
    "skill-insight": ("skills", "insight"),
    "skill-intimidation": ("skills", "intimidation"),
    "skill-investigation": ("skills", "investigation"),
    "skill-medicine": ("skills", "medicine"),
    "skill-nature": ("skills", "nature"),
    "skill-perception": ("skills", "perception"),
    "skill-performance": ("skills", "performance"),
    "skill-persuasion": ("skills", "persuasion"),
    "skill-religion": ("skills", "religion"),
    "skill-sleight-of-hand": ("skills", "sleight_of_hand"),
    "skill-stealth": ("skills", "stealth"),
    "skill-survival": ("skills", "survival"),
}


class DndClass:
    """
    Represents a D&D 5e Character Class.
    
    Fetches from official D&D 5e API and caches locally.
    Transforms proficiencies and features to character sheet format.
    """
    
    def __init__(self, name: str):
        """
        Initialize a D&D class.
        
        Args:
            name: Class name (e.g., "Cleric", "Barbarian")
            
        Raises:
            ValueError: If class not found in API
        """
        # Fetch from API (with local caching)
        self.api_data = get_cached_or_fetch('class', name.lower(), f'classes/{name.lower()}')
        
        if not self.api_data:
            raise ValueError(f"❌ Class '{name}' not found (API error or not yet in D&D 5e SRD)")
        
        self.name = self.api_data.get('name', name)
        self.index = self.api_data.get('index', name.lower())
        self.hit_die = self.api_data.get('hit_die', 8)
    
    def get_starting_proficiencies(self) -> Dict[str, List[str]]:
        """
        Get proficiencies the character gains at class level 1.
        
        Returns:
            Dict mapping proficiency categories to learned proficiencies:
            {
                'armor': ['light', 'medium'],
                'weapons': ['simple', 'martial'],
                'skills': [],  # Empty - user must choose via proficiency_choices
                'saving_throws': ['strength']
            }
        """
        proficiencies = {
            'armor': [],
            'weapons': [],
            'tools': [],
            'skills': [],
            'saving_throws': []
        }
        
        # Map fixed proficiencies
        for prof in self.api_data.get('proficiencies', []):
            prof_index = prof.get('index', '')
            
            if prof_index in PROFICIENCY_MAP:
                category, value = PROFICIENCY_MAP[prof_index]
                proficiencies[category].append(value)
        
        return proficiencies
    
    def get_proficiency_choices(self) -> List[Dict[str, Any]]:
        """
        Get proficiency choices the player must make.
        
        Returns:
            List of choice objects:
            [
                {
                    'desc': 'Choose two from History, Insight, Medicine...',
                    'choose': 2,
                    'options': ['history', 'insight', 'medicine', ...]
                }
            ]
        """
        choices = []
        
        for choice in self.api_data.get('proficiency_choices', []):
            if choice.get('type') != 'proficiencies':
                continue
            
            # Extract skill/proficiency options
            options = []
            for option in choice.get('from', {}).get('options', []):
                if option.get('option_type') == 'reference':
                    item_index = option.get('item', {}).get('index', '')
                    if item_index in PROFICIENCY_MAP:
                        _, value = PROFICIENCY_MAP[item_index]
                        options.append(value)
            
            if options:
                choices.append({
                    'desc': choice.get('desc', ''),
                    'choose': choice.get('choose', 1),
                    'type': 'proficiencies',
                    'options': options
                })
        
        return choices
    
    def get_features_at_level(self, level: int) -> List[str]:
        """
        Get features granted at a specific character level.
        
        Args:
            level: Character level (1-20)
        
        Returns:
            List of feature names (e.g., ['Spellcasting', 'Channel Divinity'])
        """
        features = []
        
        # Features are in the 'class_levels' endpoint, but for MVP
        # we can use the 'features' array from the main class endpoint
        # This would require a separate API call per level for full accuracy
        
        return features
    
    def get_spellcasting_ability(self) -> Optional[str]:
        """
        Get the spellcasting ability for this class if applicable.
        
        Returns:
            Ability name ('wisdom', 'intelligence', 'charisma') or None
        """
        # Fetch from features - requires additional setup
        # For now, return None (will be added with feature expansion)
        return None
    
    def to_character_dict(self) -> Dict[str, Any]:
        """
        Convert class data to format needed for character initialization.
        
        Returns:
            Dict with 'class', 'hit_die', and proficiency info
        """
        return {
            'class': self.name,
            'hit_die': self.hit_die,
            'proficiencies': self.get_starting_proficiencies(),
            'proficiency_choices': self.get_proficiency_choices(),
        }
    
    @staticmethod
    def get_available_classes() -> List[str]:
        """
        Get list of all available D&D 5e classes.
        
        Returns:
            List of class names
        """
        return get_all_available_classes()


# Convenience function for getting a class
def load_class(name: str) -> DndClass:
    """Load a D&D class by name"""
    return DndClass(name)
