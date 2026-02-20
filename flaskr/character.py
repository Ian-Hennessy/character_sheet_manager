"""
"Character" Object with 
functionality for managing all aspects of a Dungeons and Dragons 
5th edition character
"""

"""
Data: A dict in the following format:
{
    "name": "Jester Lavorre",
    "species": "Tiefling",
    "level": 1,
    "Class": "Cleric",
    "base_armor_class": 10,
    "initiative": 0,
    "speed": list[Walk, Climb, Fly],
    "hit_points": 10,
    "hit_dice": 8,
    "ability_scores": [str, dex, con, int, wis, cha],
    "modifiers": [str, dex, con, int, wis, cha],
    "proficiency_bonus": 2,
    "skills": {
        "acrobatics": (False, mod)
        "animal_handling": (False, mod)
        "arcana": False, mod
        "athletics": False, mod
        "deception": False, mod
        "history": False, mod
        "insight": False, mod
        "intimidation": False, mod
        "investigation": False, mod
        "medicine": False, mod
        "nature": False, mod
        "perception": False, mod
        "performance": False, mod
        "persuasion": False, mod
        "religion": False, mod
        "sleight_of_hand": False, mod
        "stealth": False, mod
        "survival": False, mod
    },
    "saving_throws": {
        "strength": False, mod
        "dexterity": False, mod
        "constitution": False, mod
        "intelligence": False, mod
        "wisdom": False, mod
        "charisma": False mod
    },
    "inventory": list[equipped: dict{armor: 
    Armor, weapons: list[Weapon], 
    items: list[Item], misc:list[Item]}],
    "actions": list[dict1(attack), dict2(spell), dict3(ability), ...],
    "bonus_actions: list[dict1(attack), dict2(spell), dict3(ability), ...],
    "reactions": list[dict1(attack), dict2(spell), dict3(ability), ...],
    "save_dc": 8 + proficiency_bonus + relevant_ability_modifier,
    "spellcasting_ability": "intelligence",
    "spell_slots": {
        "level_1": 2,
        "level_2": 0,
        "level_3": 0,
        "level_4": 0,
        "level_5": 0,
        "level_6": 0,
        "level_7": 0,
        "level_8": 0,
        "level_9": 0
    },
    "spells": list[dict1(spell1), dict2(spell2), dict3(spell3), ...]
    "info": list[backstory: str, allies: str, 
    enemies: str, appearance: str, 
    personality_traits: str, ideals: str, 
    bonds: str, flaws: str]



}
"""
import objects as obj
import classes as c
import species as s
import numpy as np
class Character():
    def __init__(self, data: dict):
        self.data = data
    """
    Retrieves an attribute from data

    """
    def __getattribute__(self, attr: str):
        if attr not in self.data:
            raise KeyError(f"{attr} is not a valid query to the character dict.")
        else:
            return self.data["attr"]
    """
    #TODO
    Sets an attribute in data. 
    Does not permit setting of new attributes, 
    and requires that the type of the value 
    being set matches the type of the existing value.
    """
    def __setattr__(self, attr:str, val):
        if attr not in self.data:
            raise KeyError(f"{attr} is not a valid query to the character dict.")
        elif type(self.data["attr"]) is not type(val):
            raise ValueError(f"Sorry, entries to {attr} must be of type {type(self.data["attr"])}. Your entry is of type {type(val)}.")
        
    """
    #TODO
    Update hit points. Damage=True subtracts hp. 
    damage=False adds hp (healing)
    if character is dead: keeps hp at 0
    """
    def update_hp(self, damage: bool = True, amt:int = 0):
        if damage:
            #harming
            self.__setattr__("hp", self.data["hp"] - amt)
            if self.data["hp"] <= 0:
                self.__setattr__("hp", 0)
        elif not damage:
            # healing
            self.__setattr__("hp", self.data["hp"] + amt)

    """
    Calculates Armor Class based on the following:
    #TODO: 1. species (Special Case)
    Certain species provide additional base armor

    2. Armor Type: 
    - Heavy [Plate, Chain Mail, Ring Mail, Splint]: 18 (flat)
    - Medium: [Hide, Chain Shirt, Scale Mail, ]
    """
    def calculate_ac(self):
        raise NotImplementedError("Hey dummy! Write your code!")
    
    """
    #TODO
    Sets skill modifier and proficiency boolean according to the 
    input skill_mods list which is a tuple of (bool,int). bool = proficient (y/n)
    int = modifier (skill mod + Proficiency if proficient)
    """
    def set_skills(self, skill_mods: list[tuple: (bool, int)]):
        raise NotImplementedError("Hey dummy! Write your code!")
    
    """
    #TODO
    Sets saving throw modifier and proficiency boolean according to 
    the input save_mods list which is a tuple of (bool,int) where bool is 
    proficiency (true = y, false = n), 
    int is modifier (skill mod + Proficiency if proficient)
    """
    def set_saving_throws(self, save_mods: list[tuple: (bool, int)]):
        raise NotImplementedError("Hey dummy! Write your code!")
    
    """
    #TODO
    adds an item to player inventory. Defaults to not equipped 
    and not Attuned unless requested
    """
    def add_inventory_item(self, 
                           item:obj.item, 
                           equip: bool = False, 
                           attune: bool = False):
        raise NotImplementedError("Hey dummy! Write your code!")
    """
    Simple functioon to restore Hit Dice to the character 
    """
    def spend_hit_die(self)->None:
        # heal by rolled die + CON modifier
        heal_amt = int(np.random(1,int(self.data["hit_dice"])) 
        + int(self.data["modifiers"][2]))
        # update hp
        self.update_hp(damage=False, amt=heal_amt)
    
    """
    
    """


        

            
