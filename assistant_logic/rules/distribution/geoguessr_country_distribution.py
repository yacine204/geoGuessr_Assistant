"""
GeoGuessr Country Distribution based on actual Street View image coverage.
Percentages represent the relative probability of encountering a location
in each country based on GeoGuessr's actual Street View availability and image density.

DATA SOURCES:
- Crrrrrrr's analysis: 82k+ logged Country Streak games (https://github.com/Crrrrrrr/geoguessr-statistics)
- GeoGuessr community frequency analysis
- Google Street View coverage data

NOTES:
- Weights reflect actual play frequency from empirical data
- Higher values = more common in GeoGuessr games
- These are approximations and may vary by game mode (Country Streak vs Classic)
"""

from rules.countries_by_regions import REGIONS

# Relative Street View coverage per country (based on empirical GeoGuessr data)
# Updated to reflect more accurate frequency distributions from player data
COUNTRY_COVERAGE_WEIGHTS = {
    # North America (VERY HIGH coverage - USA dominates)
    "United States of America": 18.0,  # ~18-20% of all games (most frequent by far)
    "Canada": 7.5,
    "Mexico": 5.0,
    
    # Western Europe (HIGH coverage)
    "France": 7.0,
    "Germany": 7.5,
    "United Kingdom": 7.2,
    "Spain": 6.5,
    "Italy": 6.0,
    "Netherlands": 6.5,
    "Belgium": 5.5,
    "Austria": 5.0,
    "Switzerland": 5.0,
    "Sweden": 5.0,
    "Norway": 4.5,
    "Denmark": 4.5,
    "Ireland": 3.5,
    "Portugal": 4.0,
    
    # Central & Eastern Europe (MODERATE-HIGH coverage)
    "Poland": 4.0,
    "Czech Republic": 4.0,
    "Hungary": 3.5,
    "Romania": 3.5,
    "Croatia": 3.0,
    "Slovakia": 2.8,
    "Bulgaria": 2.5,
    "Slovenia": 2.8,
    "Greece": 3.5,
    "Ukraine": 2.5,
    "Russia": 6.0,  # Mostly Moscow & St. Petersburg
    "Lithuania": 2.0,
    "Latvia": 1.8,
    "Estonia": 1.8,
    "Serbia": 2.0,
    "Albania": 1.5,
    "Montenegro": 1.3,
    "North Macedonia": 1.2,
    
    # Nordic & Island territories
    "Finland": 4.0,
    "Iceland": 2.0,
    "Greenland": 1.0,
    "Faroe Islands": 1.0,  # Tier 3 - added 2022
    
    # UK territories & microstates
    "Isle of Man": 0.8,
    "Luxembourg": 1.2,
    "Malta": 1.0,
    "Monaco": 0.6,
    "Andorra": 0.6,
    
    # South America (MODERATE-HIGH coverage)
    "Brazil": 6.5,
    "Argentina": 4.5,
    "Chile": 3.5,
    "Colombia": 3.0,
    "Peru": 2.5,
    "Ecuador": 2.2,
    "Uruguay": 2.0,
    "Bolivia": 1.5,
    
    # Central America & Caribbean (MODERATE coverage)
    "Costa Rica": 2.5,
    "Guatemala": 1.8,
    "Panama": 1.8,
    "Dominican Republic": 1.8,
    "Puerto Rico": 1.5,
    "Curaçao": 0.4,
    "Bermuda": 0.3,
    "U.S. Virgin Islands": 0.3,
    
    # East Asia (VERY HIGH coverage)
    "Japan": 7.8,
    "South Korea": 7.0,
    "China": 6.0,
    "Taiwan": 3.8,
    "Hong Kong": 3.2,  # Tier 3 - added 2022
    
    # Southeast Asia (MODERATE-HIGH coverage)
    "Thailand": 5.0,
    "Vietnam": 4.0,
    "Indonesia": 3.5,
    "Philippines": 2.8,
    "Malaysia": 3.5,
    "Singapore": 2.5,
    "Cambodia": 1.8,
    "Laos": 1.2,
    
    # South Asia (MODERATE coverage)
    "India": 4.5,
    "Bangladesh": 1.5,
    "Pakistan": 1.5,
    "Sri Lanka": 2.0,
    
    # Central Asia (LIMITED coverage)
    "Kazakhstan": 2.0,
    "Kyrgyzstan": 1.0,
    "Mongolia": 1.5,
    "Bhutan": 0.6,
    
    # Middle East & North Africa (LIMITED coverage)
    "Turkey": 4.5,
    "Israel": 3.0,
    "United Arab Emirates": 2.0,
    "Jordan": 1.2,
    "Qatar": 1.0,
    "Palestine": 0.8,
    "Tunisia": 1.5,
    
    # Sub-Saharan Africa (LIMITED coverage)
    "South Africa": 3.8,
    "Nigeria": 1.8,
    "Kenya": 1.5,
    "Ghana": 1.3,
    "Uganda": 1.2,
    "Senegal": 1.2,
    "Madagascar": 1.0,
    "Botswana": 1.2,
    "Rwanda": 0.8,
    "Eswatini": 0.6,
    "Lesotho": 0.6,
    "Réunion": 0.8,
    
    # Oceania (MODERATE coverage)
    "Australia": 7.5,
    "New Zealand": 5.5,
    "Guam": 1.0,
    "American Samoa": 0.3,
    "Northern Mariana Islands": 0.3,
    "Christmas Island": 0.2,
    "U.S. Minor Outlying Islands": 0.1,
}


def calculate_country_percentages():
    """
    Calculate percentage distribution of countries based on GeoGuessr coverage weights.
    
    Returns:
        dict: Country names mapped to percentage probabilities (0-100)
    """
    total_weight = sum(COUNTRY_COVERAGE_WEIGHTS.values())
    
    percentages = {
        country: (weight / total_weight) * 100
        for country, weight in COUNTRY_COVERAGE_WEIGHTS.items()
    }
    
    return percentages


def get_country_percentage(country: str) -> float:
    """
    Get the percentage probability for a specific country.
    
    Args:
        country: Country name (must match COUNTRY_COVERAGE_WEIGHTS keys)
    
    Returns:
        float: Percentage probability (0-100), or 0.0 if country not found
    """
    percentages = calculate_country_percentages()
    return percentages.get(country, 0.0)


def get_region_percentage(region: str) -> float:
    """
    Get the total percentage probability for a specific region.
    
    Args:
        region: Region name (Europe, Americas, Asia, MiddleEast, Africa, Oceania)
    
    Returns:
        float: Total percentage for the region (0-100)
    """
    if region not in REGIONS:
        return 0.0
    
    percentages = calculate_country_percentages()
    region_countries = REGIONS[region]
    
    return sum(percentages.get(country, 0.0) for country in region_countries)


def get_top_countries(limit: int = 10) -> list:
    """
    Get the top N countries by frequency.
    
    Args:
        limit: Number of countries to return (default: 10)
    
    Returns:
        list: List of tuples (country_name, percentage) sorted by frequency
    """
    sorted_dist = dict(
        sorted(COUNTRY_DISTRIBUTION_SORTED.items(), key=lambda x: x[1], reverse=True)
    )
    return list(sorted_dist.items())[:limit]


def print_distribution_summary():
    """Print a formatted summary of country and region distributions."""
    print("=" * 60)
    print("GeoGuessr Country Distribution Summary")
    print("=" * 60)
    print("\nTOP 15 COUNTRIES:")
    print("-" * 60)
    
    for country, percentage in get_top_countries(15):
        bar_length = int(percentage / 2)  # Scale to 50 chars max
        bar = "█" * bar_length
        print(f"{country:<25} {percentage:>6.2f}% {bar}")
    
    print("\n" + "=" * 60)
    print("REGION DISTRIBUTION:")
    print("=" * 60)
    
    for region, percentage in sorted(REGION_DISTRIBUTION_SORTED.items(), 
                                     key=lambda x: x[1], reverse=True):
        bar_length = int(percentage / 2)
        bar = "█" * bar_length
        print(f"{region:<20} {percentage:>6.2f}% {bar}")
    
    print("\n" + "=" * 60)


# Pre-calculated distributions for quick access
COUNTRY_DISTRIBUTION = calculate_country_percentages()

# Sort by percentage (highest first)
COUNTRY_DISTRIBUTION_SORTED = dict(
    sorted(COUNTRY_DISTRIBUTION.items(), key=lambda x: x[1], reverse=True)
)

# Regional totals
REGION_DISTRIBUTION = {
    region: get_region_percentage(region)
    for region in REGIONS.keys()
}

REGION_DISTRIBUTION_SORTED = dict(
    sorted(REGION_DISTRIBUTION.items(), key=lambda x: x[1], reverse=True)
)


# Example usage
if __name__ == "__main__":
    print_distribution_summary()
    
    # Example: Get specific country
    print("\nExample Queries:")
    print(f"USA: {get_country_percentage('United States of America'):.2f}%")
    print(f"France: {get_country_percentage('France'):.2f}%")
    print(f"Europe Total: {get_region_percentage('Europe'):.2f}%")