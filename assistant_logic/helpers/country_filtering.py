"""
Country filtering pipeline with three stages:
1. Initialize countries from distribution
2. Filter by convention (Vienna vs MUTCD)
3. Augment by language detection
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass
from data_types.country_confidence import CountryConfidence, ALL_COUNTRIES_WITH_CONFIDENCE
from rules.convention.country_distribution import CONVENTIONS
from helpers.language_filtering import adjust_confidence_by_language, LanguageResult


@dataclass
class CountryFilteringResult:
    """Result of country filtering pipeline"""
    filtered_countries: List[CountryConfidence]
    top_countries: List[CountryConfidence]
    convention: str
    language_result: Optional[LanguageResult] = None
    explanation: str = ""


def initialize_countries(show_details: bool = False) -> List[CountryConfidence]:
    """
    Stage 1: Initialize countries from distribution.
    
    Args:
        show_details: Whether to print country details
    
    Returns:
        List of all available countries with confidence scores
    """
    countries = ALL_COUNTRIES_WITH_CONFIDENCE.copy()
    
    if show_details:
        print("\n" + "="*70)
        print("STAGE 1: INITIAL COUNTRY CONFIDENCE")
        print("="*70)
        print(f"Total countries: {len(countries)}\n")
        for i, country in enumerate(countries[:15], 1):
            print(f"  {i:2d}. {country.country:20s} | Confidence: {country.confidence:6.2f}%")
        if len(countries) > 15:
            print(f"  ... and {len(countries) - 15} more countries")
        print("="*70)
    
    return countries


def filter_by_convention(countries: List[CountryConfidence],
                        convention: str,
                        show_details: bool = False) -> List[CountryConfidence]:
    """
    Stage 2: Filter countries by road sign convention.
    
    Args:
        countries: List of countries to filter
        convention: Convention type ('vienna', 'mutcd', or 'hybrid')
        show_details: Whether to print country details
    
    Returns:
        Filtered list of countries
    """
    
    print(f"\nFiltering countries by convention: {convention.upper()}...")
    
    if convention == 'vienna':
        vienna_countries = set(CONVENTIONS.get('vienna', []))
        print(f"  Vienna countries in mapping: {len(vienna_countries)}")
        filtered = [c for c in countries if c.country in vienna_countries]
        print(f"  Matched: {len(filtered)}")
    
    elif convention == 'mutcd':
        mutcd_countries = set(CONVENTIONS.get('mutcd', []))
        print(f"  MUTCD countries in mapping: {len(mutcd_countries)}")
        filtered = [c for c in countries if c.country in mutcd_countries]
        print(f"  Matched: {len(filtered)}")
    
    else:  # hybrid
        print(f"  Using all {len(countries)} countries (hybrid mode)")
        filtered = countries.copy()
    
    # Sort by confidence (highest first)
    filtered.sort(key=lambda x: x.confidence, reverse=True)
    
    if show_details:
        print("\n" + "="*70)
        print(f"STAGE 2: AFTER {convention.upper()} CONVENTION FILTERING")
        print("="*70)
        print(f"Total countries: {len(countries)} → {len(filtered)}\n")
        for i, country in enumerate(filtered[:15], 1):
            print(f"  {i:2d}. {country.country:20s} | Confidence: {country.confidence:6.2f}%")
        if len(filtered) > 15:
            print(f"  ... and {len(filtered) - 15} more countries")
        print("="*70)
    
    return filtered


def augment_by_language(countries: List[CountryConfidence],
                       ocr_text: str,
                       boost_multiplier: float = 3.0,
                       show_details: bool = False) -> Tuple[List[CountryConfidence], Optional[LanguageResult]]:
    """
    Stage 3: Augment country confidences by detected language.
    
    Args:
        countries: List of countries to augment
        ocr_text: Text extracted from OCR
        boost_multiplier: Maximum boost multiplier (3.0 = up to 3x for very specific languages)
                         IMPORTANT: This should be 3.0+, NOT a small decimal like 0.15
        show_details: Whether to print country details
    
    Returns:
        Tuple of (augmented_countries, language_result)
    """
    
    if not ocr_text or len(ocr_text.strip()) < 3:
        print("\n⚠ No valid OCR text for language detection, skipping language filtering")
        return countries, None
    
    print(f"\nDetecting language from OCR text...")
    
    augmented_countries, lang_result = adjust_confidence_by_language(
        countries,
        ocr_text,
        boost_multiplier=boost_multiplier
    )
    
    if not lang_result or lang_result.language == 'unknown':
        print("  ⚠ Language not detected")
        return countries, lang_result
    
    if show_details:
        print("\n" + "="*70)
        print(f"STAGE 3: AFTER LANGUAGE FILTERING ({lang_result.language.upper()})")
        print("="*70)
        print(f"Language: {lang_result.language} (confidence: {lang_result.language_confidence:.1%})")
        print(f"Language specificity: {lang_result.language_specificity:.1%}")
        print(f"Boost multiplier: {boost_multiplier:.1f}x\n")
        
        # Sort by confidence to show changes
        augmented_countries.sort(key=lambda x: x.confidence, reverse=True)
        for i, country in enumerate(augmented_countries[:15], 1):
            print(f"  {i:2d}. {country.country:20s} | Confidence: {country.confidence:6.2f}%")
        if len(augmented_countries) > 15:
            print(f"  ... and {len(augmented_countries) - 15} more countries")
        print("="*70)
    
    return augmented_countries, lang_result


def filter_countries(convention: str,
                    ocr_text: Optional[str] = None,
                    boost_multiplier: float = 3.0,
                    show_details: bool = True) -> CountryFilteringResult:
    """
    Complete country filtering pipeline:
    1. Initialize countries from distribution
    2. Filter by convention (Vienna vs MUTCD)
    3. Augment by language detection
    
    Args:
        convention: Convention type ('vienna', 'mutcd', or 'hybrid')
        ocr_text: Optional OCR text for language detection
        boost_multiplier: Maximum boost multiplier for language filtering (3.0 is default)
                         Higher = more aggressive language-based boosting
                         Lower specificity languages get proportionally lower boosts
        show_details: Whether to show detailed country confidence progression
    
    Returns:
        CountryFilteringResult with filtered countries and metadata
    
    Example:
        # Simple usage
        result = filter_countries('vienna')
        
        # With language
        result = filter_countries('vienna', ocr_text="Bonjour, bienvenue à Paris", boost_multiplier=3.0)
        print(result.top_countries[0].country)  # Should be France
    """
    
    print("\n" + "="*70)
    print("COUNTRY FILTERING PIPELINE")
    print("="*70)
    
    # Stage 1: Initialize
    countries = initialize_countries(show_details=show_details)
    
    # Stage 2: Filter by convention
    convention_filtered = filter_by_convention(countries, convention, show_details=show_details)
    
    # Stage 3: Augment by language (if OCR text provided)
    language_result = None
    if ocr_text:
        convention_filtered, language_result = augment_by_language(
            convention_filtered,
            ocr_text,
            boost_multiplier=boost_multiplier,  # FIXED: Pass proper multiplier here
            show_details=show_details
        )
    
    # Get top 10
    convention_filtered.sort(key=lambda x: x.confidence, reverse=True)
    top_countries = convention_filtered[:10]
    
    # Build explanation
    top_country = top_countries[0] if top_countries else None
    explanation = f"""
Pipeline Summary:
- Convention filtered: {len(convention_filtered)} countries ({convention.upper()})
- Language detected: {language_result.language if language_result else 'None'}
- Top prediction: {top_country.country if top_country else 'Unknown'} ({top_country.confidence:.2f}% if top_country else 'N/A')
    """
    
    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    print(f"Top 10 Countries:")
    for i, country in enumerate(top_countries, 1):
        print(f"  {i:2d}. {country.country:20s} | {country.confidence:6.2f}%")
    print("="*70)
    
    return CountryFilteringResult(
        filtered_countries=convention_filtered,
        top_countries=top_countries,
        convention=convention,
        language_result=language_result,
        explanation=explanation
    )