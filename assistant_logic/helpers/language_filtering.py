"""
Language detection with confidence scoring - PROPERLY FIXED
Uses MULTIPLICATIVE boost (not additive or broken formula)
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass

try:
    from langdetect import detect, detect_langs, LangDetectException
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False


@dataclass
class LanguageResult:
    """Language detection result with confidence"""
    language: str
    language_confidence: float
    language_specificity: float
    countries: List[str]
    countries_count: int


LANGUAGE_TO_COUNTRIES = {
    'en': ['United Kingdom', 'Ireland'],
    'fr': ['France', 'Belgium', 'Switzerland', 'Luxembourg'],
    'de': ['Germany', 'Austria', 'Switzerland', 'Liechtenstein'],
    'es': ['Spain'],
    'pt': ['Portugal'],
    'it': ['Italy'],
    'nl': ['Netherlands', 'Belgium'],
    'pl': ['Poland'],
    'ru': ['Russia', 'Belarus', 'Kazakhstan'],
    'uk': ['Ukraine'],
    'ro': ['Romania'],
    'bg': ['Bulgaria'],
    'hr': ['Croatia'],
    'sr': ['Serbia'],
    'sl': ['Slovenia'],
    'hu': ['Hungary'],
    'cs': ['Czech Republic'],
    'sk': ['Slovakia'],
    'el': ['Greece'],
    'sv': ['Sweden'],
    'no': ['Norway'],
    'da': ['Denmark'],
    'fi': ['Finland'],
    'is': ['Iceland'],
    'et': ['Estonia'],
    'lv': ['Latvia'],
    'lt': ['Lithuania'],
    'mt': ['Malta'],
    'zh-cn': ['China'],
    'zh-tw': ['Taiwan'],
    'ja': ['Japan'],
    'ko': ['South Korea', 'North Korea'],
    'th': ['Thailand'],
    'vi': ['Vietnam'],
    'hi': ['India'],
    'ta': ['India'],
    'ar': ['Saudi Arabia', 'United Arab Emirates', 'Egypt', 'Morocco', 'Algeria', 'Tunisia', 'Lebanon', 'Syria', 'Iraq', 'Jordan', 'Palestine'],
    'he': ['Israel'],
    'tr': ['Turkey'],
    'id': ['Indonesia'],
    'ms': ['Malaysia'],
    'tl': ['Philippines'],
}

LANGUAGE_SPECIFICITY = {
    'is': 1.0, 'fi': 1.0, 'pl': 1.0, 'ja': 1.0, 'ko': 1.0, 'th': 1.0, 'vi': 1.0,
    'et': 1.0, 'lv': 1.0, 'lt': 1.0, 'mt': 1.0,
    'he': 0.95, 'tl': 0.95, 'id': 0.95, 'ms': 0.95,
    'sv': 0.90, 'no': 0.90, 'da': 0.90, 'hu': 0.85, 'ro': 0.85, 'bg': 0.85,
    'cs': 0.85, 'sk': 0.85, 'hr': 0.85, 'sr': 0.85, 'sl': 0.85,
    'uk': 0.80, 'tr': 0.80, 'el': 0.80, 'ar': 0.70, 'hi': 0.75, 'ta': 0.65,
    'de': 0.65, 'it': 0.70, 'nl': 0.70, 'pt': 0.60, 'fr': 0.55,
    'zh-cn': 0.95, 'zh-tw': 0.95, 'es': 0.40,
    'en': 0.30,
}


def calculate_language_specificity(language_code: str) -> float:
    """Get language specificity score."""
    base_lang = language_code.split('-')[0].lower()
    return LANGUAGE_SPECIFICITY.get(base_lang, 0.3)


def detect_text_language(text: str) -> Tuple[str, float]:
    """Detect language from text."""
    if not HAS_LANGDETECT or not text or len(text.strip()) < 3:
        return ('unknown', 0.0)
    
    try:
        detected = detect(text)
        try:
            probs = detect_langs(text)
            confidence = max([p.prob for p in probs], default=0.0)
        except:
            confidence = 0.8
        return (detected, confidence)
    except LangDetectException:
        return ('unknown', 0.0)
    except Exception as e:
        print(f"Error detecting language: {e}")
        return ('unknown', 0.0)


def get_countries_by_language(language_code: str) -> List[str]:
    """Get list of countries where this language appears on signs."""
    base_lang = language_code.split('-')[0].lower()
    return LANGUAGE_TO_COUNTRIES.get(base_lang, [])


def analyze_language(ocr_text: str) -> LanguageResult:
    """Analyze language in OCR text."""
    language, lang_confidence = detect_text_language(ocr_text)
    
    if language == 'unknown':
        return LanguageResult(
            language='unknown',
            language_confidence=0.0,
            language_specificity=0.0,
            countries=[],
            countries_count=0
        )
    
    countries = get_countries_by_language(language)
    specificity = calculate_language_specificity(language)
    
    return LanguageResult(
        language=language,
        language_confidence=lang_confidence,
        language_specificity=specificity,
        countries=countries,
        countries_count=len(countries)
    )


def adjust_confidence_by_language(filtered_countries: List,
                                 ocr_text: str,
                                 boost_multiplier: float = 3.0) -> Tuple[List, LanguageResult]:
    """
    Adjust country confidence based on detected language - MULTIPLICATIVE BOOST (CORRECTED).
    
    FORMULA:
    --------
    For matching countries:
        new_confidence = old_confidence * (1 + (boost_multiplier - 1) * specificity)
        
    Example with French (specificity=0.55), boost_multiplier=3.0:
        multiplier = 1 + (3.0 - 1.0) * 0.55 = 1 + 1.1 = 2.1x
        France: 2.20% * 2.1 = 4.62%
        
    Example with English (specificity=0.30), boost_multiplier=3.0:
        multiplier = 1 + (3.0 - 1.0) * 0.30 = 1 + 0.6 = 1.6x
        UK: 2.27% * 1.6 = 3.63%
    
    Args:
        filtered_countries: List of CountryConfidence objects
        ocr_text: Text extracted from OCR
        boost_multiplier: Max boost multiplier (3.0 = up to 3x boost for very specific languages)
    
    Returns:
        Tuple of (updated_countries, language_result)
    """
    
    if not HAS_LANGDETECT or not ocr_text or len(ocr_text.strip()) < 3:
        return filtered_countries, None
    
    # Analyze language
    lang_result = analyze_language(ocr_text)
    
    if lang_result.language == 'unknown' or lang_result.language_confidence < 0.5:
        return filtered_countries, lang_result
    
    # CORRECTED FORMULA: multiplicative boost
    # scaled_multiplier will be between 1.0 and boost_multiplier
    scaled_multiplier = 1.0 + (boost_multiplier - 1.0) * lang_result.language_specificity
    
    print(f"\n{'='*70}")
    print(f"LANGUAGE ANALYSIS (VISIBLE SIGNS)")
    print(f"{'='*70}")
    print(f"  Detected Language: {lang_result.language}")
    print(f"  Detection Confidence: {lang_result.language_confidence:.1%}")
    print(f"  Language Specificity: {lang_result.language_specificity:.1%}")
    print(f"  Boost Multiplier: {scaled_multiplier:.2f}x")
    print(f"\n  Countries Using This Language on Signs:")
    
    for i, country in enumerate(lang_result.countries[:5], 1):
        print(f"    {i}. {country}")
    
    if lang_result.countries_count > 5:
        print(f"    ... and {lang_result.countries_count - 5} more")
    
    # Apply multiplicative boost to matching countries
    updated_countries = []
    
    for country_conf in filtered_countries:
        if country_conf.country in lang_result.countries:
            # BOOST: Multiply by scaled_multiplier
            new_confidence = country_conf.confidence * scaled_multiplier
        else:
            # REDUCE: Divide by scaled_multiplier
            new_confidence = country_conf.confidence / scaled_multiplier
        
        updated_country = country_conf.__class__(
            country=country_conf.country,
            confidence=new_confidence
        )
        updated_countries.append(updated_country)
    
    # Normalize so confidences sum to 1.0 (maintains 100% total)
    total_conf = sum(c.confidence for c in updated_countries)
    if total_conf > 0:
        updated_countries = [
            updated_countries[i].__class__(
                country=updated_countries[i].country,
                confidence=updated_countries[i].confidence / total_conf
            )
            for i in range(len(updated_countries))
        ]
    
    # Re-sort by confidence
    updated_countries.sort(key=lambda x: x.confidence, reverse=True)
    
    # Show top boosted countries
    print(f"\n  Top boosted countries:")
    boosted = [c for c in updated_countries if c.country in lang_result.countries]
    for country in boosted[:5]:
        print(f"    ✓ {country.country}: {country.confidence:.2f}%")
    
    print(f"{'='*70}")
    
    return updated_countries, lang_result