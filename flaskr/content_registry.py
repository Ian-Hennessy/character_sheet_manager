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

    @staticmethod
    def get_level_data(class_name: str, level: int, user_id: int = None) -> Dict[str, Any]:
        """
        Return level data for a class at the given level.

        Checks homebrew level tables first (if user_id provided), then falls back
        to the official SRD API. Returns a dict with keys: level, prof_bonus,
        features, class_specific, ability_score_bonuses.
        """
        from flaskr.db import get_db
        from . import utils

        db = get_db()

        if user_id:
            row = db.execute(
                'SELECT data FROM homebrew_class_levels WHERE user_id = ? AND class_name = ? AND level = ?',
                (user_id, class_name, level)
            ).fetchone()
            if row:
                return json.loads(row['data'])

        shared = db.execute(
            'SELECT data FROM homebrew_class_levels WHERE is_public = TRUE AND class_name = ? AND level = ?',
            (class_name, level)
        ).fetchone()
        if shared:
            return json.loads(shared['data'])

        return utils._get_class_level_data(class_name, level)
