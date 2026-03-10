"""
Utilities for fetching and caching D&D 5e API data.
Implements local JSON caching to minimize API calls.
"""

import json
import urllib.request
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
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode())
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


def get_all_available_species() -> list[str]:
    """Get list of all available species/races"""
    data = get_cached_or_fetch('index', 'races', 'races')
    if data and 'results' in data:
        return [race['name'] for race in data['results']]
    return []
