"""
Utilities for fetching and caching D&D 5e API data.
Implements local JSON caching to minimize API calls.
"""

import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional

API_BASE = "https://www.dnd5eapi.co/api"
CACHE_DIR = Path(__file__).parent / "cache"


def ensure_cache_dir():
    """Create cache directory if it doesn't exist"""
    CACHE_DIR.mkdir(exist_ok=True)


def get_cache_path(resource: str, identifier: str) -> Path:
    """Get the cache file path for a resource"""
    ensure_cache_dir()
    return CACHE_DIR / f"{resource}_{identifier}.json"


def fetch_from_api(endpoint: str) -> Optional[Dict[str, Any]]:
    """
    Fetch data from D&D 5e API.
    
    Args:
        endpoint: API endpoint (e.g., 'classes/cleric')
    
    Returns:
        Parsed JSON response or None if error
    """
    try:
        url = f"{API_BASE}/{endpoint}"
        response = requests.get(url, timeout=5, headers={'Accept': 'application/json'})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"⚠️  API Error fetching {endpoint}: {e}")
        return None


def get_cached_or_fetch(resource: str, identifier: str, endpoint: str) -> Optional[Dict[str, Any]]:
    """
    Get data from cache if it exists, otherwise fetch from API and cache it.
    
    Args:
        resource: Type of resource (e.g., 'class', 'race')
        identifier: Unique ID (e.g., 'cleric', 'tiefling')
        endpoint: API endpoint to fetch from
    
    Returns:
        Parsed JSON data or None if neither cache nor API available
    """
    cache_path = get_cache_path(resource, identifier)
    
    # Try to load from cache
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Cache read error for {identifier}: {e}")
    
    # Fetch from API
    data = fetch_from_api(endpoint)
    if data:
        # Save to cache
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Cache write error for {identifier}: {e}")
        return data
    
    return None


def clear_cache():
    """Clear all cached data"""
    import shutil
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
    ensure_cache_dir()
    print("✓ Cache cleared")


def get_all_available_classes() -> list[str]:
    """Get list of all available classes"""
    data = get_cached_or_fetch('index', 'classes', 'classes')
    if data and 'results' in data:
        return [cls['name'] for cls in data['results']]
    return []


def get_class_level_data(class_index: str, level: int) -> Optional[Dict[str, Any]]:
    """
    Fetch full level data for a class at a specific level (cached).

    class_index should be the lowercase API index (e.g. 'fighter').
    Returns the level object with keys: level, prof_bonus, features, class_specific, etc.
    """
    identifier = f"{class_index}_{level}"
    return get_cached_or_fetch('class_level', identifier, f'2014/classes/{class_index}/levels/{level}')


def get_feature_detail(feature_index: str) -> Optional[Dict[str, Any]]:
    """
    Fetch full details for a single class feature (including description).

    Uses the local cache; fetches from API on first access.
    The API response has a 'desc' key (list of strings) rather than 'description'.
    Returns None if both cache and API are unavailable.
    """
    return get_cached_or_fetch('feature', feature_index, f'2014/features/{feature_index}')


def get_all_available_species() -> list[str]:
    """Get list of all available species/races"""
    data = get_cached_or_fetch('index', 'races', 'races')
    if data and 'results' in data:
        return [race['name'] for race in data['results']]
    return []


def get_class_spells(class_index: str) -> list:
    """
    Fetch all spells available to a class (cached).
    Returns a list of {index, name, url} dicts, or [] for non-casters.
    """
    data = get_cached_or_fetch('class_spells', class_index, f'2014/classes/{class_index}/spells')
    if data and 'results' in data:
        return data['results']
    return []


def get_spell_detail(spell_index: str) -> Optional[Dict[str, Any]]:
    """Fetch full details for a single spell (cached)."""
    return get_cached_or_fetch('spell', spell_index, f'2014/spells/{spell_index}')
