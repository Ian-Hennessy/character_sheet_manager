"""
An Object class for items in a player inventory 
"""

"""
Item initialization: 
Item class is managed by a dict: 
dict itemData {
"type": str type of item (Weapon, Armor, Potion, Wondrous, etc.)
"
}
Rarities: 
0 common
1 uncommon
2 rare
3 very rare 
4 Legendary 
5 artifact
6 other/unknown
"""
class Item:
    def __init__(self, name: str = "Unknown Item", description: str = "No description", item_type: str = "Miscellaneous", rarity: int = 0):
        self._name = name
        self._description = description
        self._item_type = item_type
        self._rarity = rarity

    # Getters
    def get_name(self) -> str:
        return self._name

    def get_description(self) -> str:
        return self._description

    def get_item_type(self) -> str:
        return self._item_type

    def get_rarity(self) -> str:
        return self._rarity

    # Setters
    def set_name(self, name: str):
        self._name = name

    def set_description(self, description: str):
        self._description = description

    def set_item_type(self, item_type: str):
        self._item_type = item_type
    
    def set_item_rarity(self, rarity: int):
        if 

    # Edit functionality
    def edit_item(self, name: str = None, description: str = None, item_type: str = None):
        if name:
            self.set_name(name)
        if description:
            self.set_description(description)
        if item_type:
            self.set_item_type(item_type)

    def __str__(self):
        return f"{self._name} ({self._item_type}): {self._description}"


class Weapon(Item):
    def __init__(self, name="Unknown Weapon", description="No description", damage="1d6"):
        super().__init__(name, description, "Weapon")
        self._damage = damage

    def get_damage(self) -> str:
        return self._damage

    def set_damage(self, damage: str):
        self._damage = damage
    


class Armor(Item):
    def __init__(self, name="Unknown Armor", description="No description", armor_class=10):
        super().__init__(name, description, "Armor")
        self._armor_class = armor_class

    def get_armor_class(self) -> int:
        return self._armor_class

    def set_armor_class(self, armor_class: int):
        self._armor_class = armor_class


class Potion(Item):
    def __init__(self, name="Unknown Potion", description="No description", effect="Healing"):
        super().__init__(name, description, "Potion")
        self._effect = effect

    def get_effect(self) -> str:
        return self._effect

    def set_effect(self, effect: str):
        self._effect = effect


class Wondrous(Item):
    def __init__(self, name="Unknown Wondrous Item", description="No description"):
        super().__init__(name, description, "Wondrous")



class Miscellaneous(Item):
    def __init__(self, name="Unknown Item", description="No description"):
        super().__init__(name, description, "Miscellaneous")
        