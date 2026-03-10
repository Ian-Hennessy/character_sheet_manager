"""
D&D 5e Character Object

Manages all aspects of a Dungeons and Dragons 5th edition character.
Provides validated setters, calculated properties, and utility methods.

All character state is stored in the data dict for easy serialization to database/JSON.
"""

import random
from typing import Dict, List, Optional, Any
from flaskr import objects as obj

"""
Standard ability order in D&D 5e: 
STR, 
DEX, 
CON, 
INT, 
WIS, 
CHA
"""
ABILITY_ORDER = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']

"""
Map skill names to their associated ability index
"""
SKILL_ABILITY_MAP = {
    'acrobatics': 1,  # DEX
    'animal_handling': 4,  # WIS
    'arcana': 3,  # INT
    'athletics': 0,  # STR
    'deception': 5,  # CHA
    'history': 3,  # INT
    'insight': 4,  # WIS
    'intimidation': 5,  # CHA
    'investigation': 3,  # INT
    'medicine': 4,  # WIS
    'nature': 3,  # INT
    'perception': 4,  # WIS
    'performance': 5,  # CHA
    'persuasion': 5,  # CHA
    'religion': 3,  # INT
    'sleight_of_hand': 1,  # DEX
    'stealth': 1,  # DEX
    'survival': 4,  # WIS
}


class Character:
    """
    D&D 5e Character wrapper.
    Support for validation of inputs, 
    updating statistics, classes, inventory etc. 
    
    Keeps all character state info in self.data 
    dictionary for easy serialization.
    Provides validated setters and calculated properties.

    Character data from the 5e SRD is managed by cals to the official 
    DnD 5e API. All other data is managed directly by 
    Character class
    """
    
    def __init__(self, data: Dict[str, Any]):
        """
        Initialize a character.
        
        Args:
            data: Character data dict with all character information
        """
        object.__setattr__(self, 'data', data)
    
    # Getters n setters
    
    def get(self, attr: str, default=None):
        """
        Safely retrieve character attribute.
        
        Args:
            attr: Attribute name
            default: Default value if not found
        
        Returns:
            Attribute value or default
        """
        return self.data.get(attr, default)
    
    def set(self, attr: str, val: Any, check_type: bool = False) -> None:
        """
        Set character attribute with type checking.
        
        Args:
            attr: Attribute name
            val: New value
            check_type: If True, verify type matches existing value
        
        Raises:
            KeyError: If attribute doesn't exist in data
            ValueError: If type doesn't match (when check_type=True)
        """
        if attr not in self.data:
            raise KeyError(f"❌ '{attr}' is not a valid character attribute")
        
        if check_type and type(self.data[attr]) is not type(val):
            raise ValueError(
                f"❌ '{attr}' must be {type(self.data[attr]).__name__}, "
                f"got {type(val).__name__}"
            )
        
        self.data[attr] = val
    
    """
    Manage character hit points:
    update_hp updates hp value 
    spend hit die: spend a hit die to heal 


    """
    
    def update_hp(self, damage: bool = True, amount: int = 0) -> None:
        """
        Update character hit points.
        
        Args:
            damage: If True, subtract HP (take damage). If False, add HP (heal).
            amount: Amount to change by
        
        Note:
            HP never goes below 0 or above max.
        """
        current_hp = self.data.get("hit_points", 0)
        max_hp = self.data.get("max_hit_points", current_hp)
        
        if damage:
            current_hp = max(0, current_hp - amount)
        else:
            current_hp = min(max_hp, current_hp + amount)
        
        self.data["hit_points"] = current_hp
    
    def spend_hit_die(self) -> int:
        """
        Spend a hit die to recover hit points during a short rest.
        
        Rolls hit die and adds CON modifier. Minimum 1 HP recovered.
        
        Returns:
            Amount healed
        
        Raises:
            RuntimeError: If no hit dice remaining
        """
        hit_die = self.data.get("hit_die", 8)
        hit_dice_used = self.data.get("hit_dice_used", 0)
        level = self.data.get("level", 1)
        
        if hit_dice_used >= level:
            raise RuntimeError("❌ No hit dice remaining")
        
        # Roll hit die
        roll = random.randint(1, hit_die)
        con_mod = self.data["modifiers"][2]  # CON is index 2
        heal_amount = max(1, roll + con_mod)  # Minimum 1 HP healed
        
        # Update HP and hit dice used
        self.update_hp(damage=False, amount=heal_amount)
        self.data["hit_dice_used"] += 1
        
        return heal_amount
    
    """
    Calculate character's armor class 
    """
    
    def calculate_ac(self) -> int:
        """
        Calculate current armor class.
        
        Logic:
        1. If armor equipped: Use armor's AC
        2. If no armor: Use 10 + DEX modifier
        
        Additional modifiers (shields, special abilities) handled separately.
        
        Returns:
            Current AC value
        """
        armor = self.data.get("inventory", {}).get("armor")
        
        if armor:
            return armor.get_armor_class()
        else:
            dex_mod = self.data["modifiers"][1]  # DEX is index 1
            return 10 + dex_mod
    """
    AC override method to manually override AC 
    in case of unarmored defense, magic bonuses like Mage Armor, etc.
    """
    def override_ac(self, val: int, source: str = None):
        """
        Override Armor Class with an input value 
        This method used when character AC is updated with vals or 
        sources outside of armor, i.e. Unarmored Defenses, Mage Armor,
        Magic bonuses or detriments 
        """
        if source is not None:
            return (val, source)
        else:
            return val
        
            
    
    """
    Methods for setting and managing skill proficiencies 
    """
    
    def set_skill_proficiency(self, skill_name: str, proficient: bool = False) -> None:
        """
        Set proficiency for a specific skill.
        
        Args:
            skill_name: Skill name (e.g., 'acrobatics', 'arcana')
            proficient: Whether character is proficient in this skill
        
        Updates:
            - skills[skill_name]: (is_proficient, modifier) tuple
        
        Raises:
            KeyError: If skill_name is invalid
        """
        if skill_name.lower() not in SKILL_ABILITY_MAP:
            raise KeyError(f"❌ Unknown skill: {skill_name}")
        
        skills = self.data.get("skills", {})
        ability_idx = SKILL_ABILITY_MAP[skill_name.lower()]
        ability_mod = self.data["modifiers"][ability_idx]
        prof_bonus = self.data.get("proficiency_bonus", 0)
        
        # Store as (is_proficient, modifier)
        final_mod = ability_mod + (prof_bonus if proficient else 0)
        skills[skill_name.lower()] = (proficient, final_mod)
        self.data["skills"] = skills
    
    def set_saving_throw_proficiency(self, ability: str, proficient: bool = False) -> None:
        """
        Set proficiency for a saving throw.
        
        Args:
            ability: Ability name (e.g., 'wisdom', 'constitution')
            proficient: Whether character is proficient
        
        Updates:
            - saving_throws[ability]: (is_proficient, modifier) tuple
        
        Raises:
            KeyError: If ability name is invalid
        """
        ability_idx = self._get_ability_index(ability)
        if ability_idx is None:
            raise KeyError(f"❌ Unknown ability: {ability}")
        
        saving_throws = self.data.get("saving_throws", {})
        ability_mod = self.data["modifiers"][ability_idx]
        prof_bonus = self.data.get("proficiency_bonus", 0)
        
        # Store as (is_proficient, modifier)
        final_mod = ability_mod + (prof_bonus if proficient else 0)
        saving_throws[ability.lower()] = (proficient, final_mod)
        self.data["saving_throws"] = saving_throws
    
    """
    Inventory management methods
    """
    
    def add_inventory_item(self, item: "obj.Item", equipped: bool = False, attuned: bool = False) -> None:
        """
        Add item to character inventory.
        
        Args:
            item: Item object to add
            equipped: Whether item is currently equipped/in use
            attuned: Whether character is attuned to item (magic items only)
        
        Raises:
            RuntimeError: If trying to attune when already at max attunement
        
        Note:
            - Armor: Only one can be equipped at a time
            - Weapons: Can equip up to 2 (dual wield or one two-handed)
            - Other items: Go to backpack by default
        """
        inv = self.data["inventory"]
        item_type = item.get_item_type()
        
        if item_type == "Armor":
            if equipped:
                inv["armor"] = item
            else:
                inv["backpack"].append(item)
        
        elif item_type == "Weapon":
            if equipped:
                # Equip weapon (max 2)
                if len(inv["weapons"]) < 2:
                    inv["weapons"].append(item)
                else:
                    print(f"⚠️  Cannot equip {item.get_name()} - both weapon slots full")
                    inv["backpack"].append(item)
            else:
                inv["backpack"].append(item)
        
        else:
            # Wondrous items, potions, etc.
            if equipped:
                inv["equipped_items"].append(item)
            else:
                inv["backpack"].append(item)
        
        # Handle attunement
        if attuned:
            max_attunement = self.data.get("attunement_slots", 3)
            if len(self.data["attuned_items"]) >= max_attunement:
                raise RuntimeError(
                    f"❌ Already attuned to {max_attunement} items (max)"
                )
            self.data["attuned_items"].append(item)
    
    def remove_inventory_item(self, item: "obj.Item") -> bool:
        """
        Remove item from character inventory.
        
        Args:
            item: Item object to remove
        
        Returns:
            True if item was found and removed, False otherwise
        """
        inv = self.data["inventory"]
        
        # Check all containers
        for container in [inv["weapons"], inv["equipped_items"], inv["backpack"]]:
            if item in container:
                container.remove(item)
                return True
        
        # Check if it's the equipped armor
        if inv.get("armor") == item:
            inv["armor"] = None
            return True
        
        # Check attuned items
        if item in self.data.get("attuned_items", []):
            self.data["attuned_items"].remove(item)
        
        return False
    
    def unattune_item(self, item: "obj.Item")-> bool:
        """
        Unattune the character from an item in their attuned inventory slots

        Args: 
            obj.Item: item to unattune
        
        Returns:
            True if item found and unattuned successfully
            False if item not found and not unattuned
        
        Raises: 
            RuntimeError if item not in player inventory or obj id is invalid
        """
        attuned = self.data.get("attuned_items")
        if item in attuned:
            attuned.remove(item)
        else:
            raise RuntimeError(f"Item {item._name} is not attuned!")

            
    
    """
    helpers for getting and calculating ability scores, modifiers etc 
    """
    
    def _get_ability_index(self, ability: str) -> Optional[int]:
        """
        Map ability name to index in modifiers/ability_scores array.
        
        Args:
            ability: Ability name (case-insensitive)
        
        Returns:
            Index (0-5) or None if invalid
        """
        ability_map = {
            'strength': 0,
            'dexterity': 1,
            'constitution': 2,
            'intelligence': 3,
            'wisdom': 4,
            'charisma': 5
        }
        return ability_map.get(ability.lower())
    
    def calculate_modifiers(self) -> List[int]:
        """
        Calculate ability modifiers from ability scores.
        
        D&D formula: (ability_score - 10) // 2
        
        Returns:
            List of 6 modifiers [STR, DEX, CON, INT, WIS, CHA]
        """
        return [
            (score - 10) // 2
            for score in self.data.get("ability_scores", [10, 10, 10, 10, 10, 10])
        ]
    
    def calculate_proficiency_bonus(self) -> int:
        """
        Calculate proficiency bonus from character level.
        
        D&D 5e formula:
        - Levels 1-4: +2
        - Levels 5-8: +3
        - Levels 9-12: +4
        - Levels 13-16: +5
        - Levels 17-20: +6
        
        Returns:
            Proficiency bonus
        """
        level = self.data.get("level", 1)
        return ((level - 1) // 4) + 2
    
    def is_alive(self) -> bool:
        """Check if character has HP > 0"""
        return self.data.get("hit_points", 0) > 0






