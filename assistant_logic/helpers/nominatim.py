import asyncio
from geopy.geocoders import Nominatim
from geopy.exc import GeopyError
from dataclasses import dataclass, field
from typing import Optional, List, Dict

# Cache for search results to avoid duplicate queries
_search_cache: Dict[str, List['NominatimResult']] = {}

# Country bounding boxes for limiting searches
COUNTRY_BOUNDS = {
    'fr': {'south': 41.0, 'north': 51.1, 'west': -8.2, 'east': 8.3},
    'de': {'south': 47.3, 'north': 55.1, 'west': 5.9, 'east': 15.1},
    'es': {'south': 36.0, 'north': 43.8, 'west': -9.3, 'east': 3.3},
    'uk': {'south': 50.0, 'north': 58.6, 'west': -8.6, 'east': 1.8},
    'it': {'south': 36.6, 'north': 47.1, 'west': 6.6, 'east': 18.5},
    'us': {'south': 24.5, 'north': 49.4, 'west': -125.0, 'east': -66.9},
    'jp': {'south': 30.4, 'north': 45.6, 'west': 123.0, 'east': 145.8},
    'au': {'south': -44.0, 'north': -10.0, 'west': 113.0, 'east': 154.0},
    'br': {'south': -33.7, 'north': 5.2, 'west': -73.9, 'east': -34.8},
    'ca': {'south': 41.7, 'north': 83.1, 'west': -141.0, 'east': -52.6},
}

@dataclass
class NominatimResult:
    query: str
    latitude: float
    longitude: float
    address: str
    poi_type: Optional[str] = None      # 'shop', 'amenity', 'tourism', etc.
    poi_class: Optional[str] = None     # Specific class (e.g., 'bakery', 'restaurant')
    country: Optional[str] = None       # Country code (e.g., 'fr', 'de')
    country_name: Optional[str] = None  # Full country name
    state: Optional[str] = None         # State/Region
    city: Optional[str] = None          # City
    postcode: Optional[str] = None      # Postal code
    tags: Dict[str, str] = field(default_factory=dict)

# Create a Nominatim geocoder (non-blocking)
geolocator = Nominatim(user_agent="geogussr-assistant")

def _extract_poi_type(location) -> tuple[str, str]:
    """Extract POI type and class from Nominatim result."""
    raw = location.raw if hasattr(location, 'raw') else {}
    poi_type = raw.get('type', 'unknown')
    poi_class = raw.get('class', 'unknown')
    return poi_type, poi_class

def _extract_address_parts(location) -> Dict[str, str]:
    """Extract structured address components from Nominatim."""
    raw = location.raw if hasattr(location, 'raw') else {}
    address_parts = raw.get('address', {})
    
    return {
        'country': address_parts.get('country'),
        'country_code': address_parts.get('country_code'),
        'state': address_parts.get('state'),
        'city': address_parts.get('city'),
        'postcode': address_parts.get('postcode'),
        'shop': address_parts.get('shop'),
        'amenity': address_parts.get('amenity'),
        'tourism': address_parts.get('tourism'),
        'historic': address_parts.get('historic'),
    }

async def search(query: str, 
                language: str = 'en',
                top_countries: Optional[List[str]] = None) -> List[NominatimResult]:
    """
    Search for a location using Nominatim.
    
    Args:
        query: Search term (address, place name, POI)
        language: Language code for results (e.g., 'en', 'fr', 'de')
        top_countries: Optional list of country names to prioritize/filter by
                      (e.g., ['France', 'Germany']) - only returns results from these countries
    
    Returns:
        List of NominatimResult objects
    """
    
    # Check cache first
    cache_key = f"{query}_{language}_{','.join(sorted(top_countries or []))}"
    if cache_key in _search_cache:
        return _search_cache[cache_key]
    
    try:
        # Run geocoding in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        # Build the query with country hints if provided
        search_query = query
        if top_countries and len(top_countries) <= 3:
            # Add country hints to improve search accuracy
            hints = ", ".join(top_countries)
            search_query = f"{query}, {hints}"
            
        location = await loop.run_in_executor(
            None, 
            lambda: geolocator.geocode(
                search_query,
                language=language, 
                addressdetails=True, 
                timeout=10
            )
        )
        
        if not location:
            _search_cache[cache_key] = []
            return []
        
        # If top_countries specified, filter result by those countries
        poi_type, poi_class = _extract_poi_type(location)
        address_parts = _extract_address_parts(location)
        country_name = address_parts.get('country')
        
        # Filter by top_countries if specified
        if top_countries and country_name and country_name not in top_countries:
            _search_cache[cache_key] = []
            return []
        
        result = NominatimResult(
            query=query,
            latitude=location.latitude,
            longitude=location.longitude,
            address=location.address,
            poi_type=poi_type,
            poi_class=poi_class,
            country=address_parts.get('country_code'),
            country_name=country_name,
            state=address_parts.get('state'),
            city=address_parts.get('city'),
            postcode=address_parts.get('postcode'),
            tags=address_parts
        )
        
        # Cache result
        _search_cache[cache_key] = [result]
        return [result]
        
    except GeopyError as e:
        print(f"Nominatim error for '{query}': {e}")
        _search_cache[cache_key] = []
        return []
    except Exception as e:
        print(f"Error searching for {query}: {e}")
        _search_cache[cache_key] = []
        return []

def filter_by_country(results: List[NominatimResult], 
                      allowed_countries: List[str]) -> List[NominatimResult]:
    """Filter Nominatim results by country name or code."""
    return [r for r in results if (r.country_name and r.country_name in allowed_countries) or 
                                   (r.country and r.country.lower() in [c.lower() for c in allowed_countries])]

def group_by_type(results: List[NominatimResult]) -> Dict[str, List[NominatimResult]]:
    """Group Nominatim results by POI type."""
    grouped = {}
    for result in results:
        poi_type = result.poi_type or 'unknown'
        if poi_type not in grouped:
            grouped[poi_type] = []
        grouped[poi_type].append(result)
    return grouped

def get_top_countries_names(countries_list: List) -> List[str]:
    """
    Extract country names from CountryConfidence objects (top 5 for query hints).
    
    Args:
        countries_list: List of CountryConfidence objects (from country_filtering)
    
    Returns:
        List of top 5 country names as strings
    """
    if not countries_list:
        return []
    
    # Get top 5 countries
    top_5 = countries_list[:5] if len(countries_list) > 5 else countries_list
    
    # Extract country names
    country_names = []
    for country_conf in top_5:
        if hasattr(country_conf, 'country'):
            country_names.append(country_conf.country)
    
    return country_names

def clear_search_cache():
    """Clear the search results cache."""
    global _search_cache
    _search_cache.clear()