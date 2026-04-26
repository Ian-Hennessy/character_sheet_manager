"""
Content Registry manages the sourcing of content 
for character creation and management. 

Will allow for creation and use of custom ("homebrew")
DnD materials such as homebrew 
classes
subclasses
items
spells
etc.
"""
import json
from typing import Dict, List, Optional, Any
import requests

url = "https://www.dnd5eapi.co/api/2014/"

class ContentRegistry:
    """
    Interface for official and homebrew content

    Check sources: 
    1. Users custom homebrew (with user_id)
    2. Shared homebrew 
    3. Official SRD (API)
    """

    @staticmethod
    def get_class(class_name: str, user_id: int = None) -> Dict[str, Any]:
        """Load from any source"""
        from flaskr.data.base_classes import DndClass
        from flaskr.db import get_db
        db = get_db()
        # prioritize user's homebrew 
        # if user_id is input
        if user_id:
            
            homebrew = db.execute(
                'SELECT data FROM homebrew_classes WHERE user_id = ? AND name = ?',
                (user_id, class_name)
            ).fetchone()

            if homebrew: 
                return DndClass.from_dict(json.loads(homebrew['data']))

        # fetch from shared homebrew if not user_id 
        shared = db.execute(
             'SELECT data FROM homebrew_classes WHERE is_public = TRUE AND name = ?',
             (class_name,)
        ).fetchone()
        if shared:
                return DndClass.from_dict(json.loads(shared['data']))
        
        # default to official SRD if not homebrew

        try: 
            dnd_class = DndClass(class_name)
            return dnd_class
        except ValueError:
            raise ValueError(f"Class '{class_name}' was not found in any source."
                            + "Would you like to create it?")
        

    @staticmethod
    def get_species(species_name: str, user_id: int = None) -> Dict[str, Any]:
        pass
