""" Handful of utility methods for reuse in several areas """


import enum

import requests
from typing import Dict, List, Optional, Any
from enum import Enum
import werkzeug
import flask

"""
Enum to pass to specified_api_request to specify which
field to generate a request for an API response.
"""

class ApiField(Enum):
    CLASSES = "classes"
    RACES = 'races'
    SUBCLASSES = 'classes/subclasses'
    SUBRACES = 'races/subraces'


def _normalize_class_index(class_name: str) -> str:
    """Convert a class display name to the API index format (e.g. 'Blood Hunter' -> 'blood-hunter')."""
    return class_name.lower().replace(' ', '-')





"""
_api_request formulates an API GET request to the dnd5e api, returning the payload from the 
https action. 
"""
def _api_request(field: ApiField, secondary_field: str=None, tertiary_field: str=None) -> Dict[str, Any]:
    """
    Generate and send a GET request for the input field to the API. 
    Input: field string to request from API 
    Output: Output of a GET request to the API for the requested field 
    """
    base_url = "https://www.dnd5eapi.co/api/2014/"
    if secondary_field:
        request_url = base_url + field.value + secondary_field
        if tertiary_field:
            request_url += f"/{tertiary_field}"
    else:
        request_url = base_url + field.value
    payload = {}
    headers = {
        'Accept': 'application/json'
    }
    try:
        response = requests.request("GET", request_url, headers=headers, data=payload)
    except requests.RequestException as e:
        print(f"Error fetching API data: {e}")
        return {}
    ## Convert response to dict and return 
    response = response.json()
    return response


""" 
Extract item extracts the specified dict key:val item from a list of dicts 
and returns as a list of the dtype of the value at that index in the dict
"""
def _extract_index(data: dict, tgt: str) -> list:
    """
    Extract the specified dict key:val item from a list of dicts and 
    return as a list of the dtype of the value at that index in the dict
    Input: data: dict containing list of dicts to extract from 
    tgt: string key to extract from
    Output: list of the dtype of the value at that index in the dict
    """
    return [item[tgt] for item in data['results']]


def _specified_api_request(base_field: ApiField, tgt_field: str, ) -> list:
    base_response = _api_request(base_field)
    return _extract_index(base_response, tgt_field)

def _get_class_level_data(class_name: str, level: int) -> Dict[str, Any]:
    """
    Fetch the full level data object for a class at a specific level (cached).

    Returns a dict with keys: level, prof_bonus, features, class_specific,
    ability_score_bonuses, etc. Returns {} on error.
    """
    from flaskr.data.api_utils import get_class_level_data
    index = _normalize_class_index(class_name)
    return get_class_level_data(index, level) or {}
