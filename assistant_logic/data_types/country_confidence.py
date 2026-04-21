"""
Country with confidence score data type.
Represents a country and its confidence/probability in GeoGuessr.
"""

from dataclasses import dataclass
from typing import List
from rules.distribution.geoguessr_country_distribution import (
    COUNTRY_DISTRIBUTION_SORTED,
    calculate_country_percentages,
)


@dataclass
class CountryConfidence:
    """
    Represents a country with its confidence score.
    
    Attributes:
        country: Country name
        confidence: Percentage confidence (0-100) based on GeoGuessr coverage
    """
    country: str
    confidence: float

    def __str__(self) -> str:
        return f"{self.country}: {self.confidence:.2f}%"

    def __repr__(self) -> str:
        return f"CountryConfidence(country='{self.country}', confidence={self.confidence:.2f})"


def load_all_countries_with_confidence() -> List[CountryConfidence]:
    """
    Load all countries with their confidence scores, sorted by confidence (highest first).
    
    Returns:
        List of CountryConfidence objects sorted by confidence descending
    """
    countries_with_confidence = [
        CountryConfidence(country=country, confidence=confidence)
        for country, confidence in COUNTRY_DISTRIBUTION_SORTED.items()
    ]
    return countries_with_confidence


def get_country_confidence(country: str) -> CountryConfidence:
    """
    Get a single country with its confidence score.
    
    Args:
        country: Country name
    
    Returns:
        CountryConfidence object for the country, or None if not found
    """
    percentages = calculate_country_percentages()
    confidence = percentages.get(country)
    
    if confidence is None:
        return None
    
    return CountryConfidence(country=country, confidence=confidence)


def get_top_countries(n: int = 10) -> List[CountryConfidence]:
    """
    Get the top N countries by confidence.
    
    Args:
        n: Number of countries to return (default: 10)
    
    Returns:
        List of top N countries with confidence
    """
    all_countries = load_all_countries_with_confidence()
    return all_countries[:n]


# Pre-load for quick access
ALL_COUNTRIES_WITH_CONFIDENCE = load_all_countries_with_confidence()
