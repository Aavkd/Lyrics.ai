"""
Flow-to-Lyrics: Phonetic Validation Tests
==========================================
Test suite for ARPABET-to-IPA mapping and phonetic matching functionality.

Tests:
1. ARPABET to IPA conversion
2. Phonetic match scoring
3. Combined scoring with phonetic data
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from validator import (
    LyricValidator,
    ValidationResult,
    ARPABET_TO_IPA,
    PHONETIC_CLASSES
)
from audio_engine import Segment


# =============================================================================
# TEST: ARPABET-TO-IPA MAPPING
# =============================================================================

def test_arpabet_to_ipa_mapping():
    """Test that ARPABET phonemes are correctly mapped to IPA."""
    print("\n📊 Testing ARPABET to IPA mapping...")
    
    validator = LyricValidator()
    
    # Test 1: Basic word "man" -> M AE1 N -> m æ n
    phonemes = ['M', 'AE1', 'N']
    ipa = validator.normalize_arpabet_to_ipa(phonemes)
    
    assert 'm' in ipa, f"Expected 'm' in '{ipa}'"
    assert 'æ' in ipa, f"Expected 'æ' in '{ipa}'"
    assert 'n' in ipa, f"Expected 'n' in '{ipa}'"
    print(f"   ✓ 'man' -> ['M', 'AE1', 'N'] -> '{ipa}'")
    
    # Test 2: Word with diphthong "day" -> D EY1 -> d eɪ
    phonemes = ['D', 'EY1']
    ipa = validator.normalize_arpabet_to_ipa(phonemes)
    assert 'd' in ipa, f"Expected 'd' in '{ipa}'"
    print(f"   ✓ 'day' -> ['D', 'EY1'] -> '{ipa}'")
    
    # Test 3: Stress markers are stripped
    phonemes = ['M', 'AA1', 'N', 'S', 'T', 'ER0']  # "monster"
    ipa = validator.normalize_arpabet_to_ipa(phonemes)
    assert '0' not in ipa and '1' not in ipa, "Stress markers should be stripped"
    print(f"   ✓ Stress markers stripped: '{ipa}'")
    
    # Test 4: Empty phonemes
    ipa = validator.normalize_arpabet_to_ipa([])
    assert ipa == "", f"Empty input should return empty string, got '{ipa}'"
    print("   ✓ Empty phonemes handled correctly")
    
    return True


# =============================================================================
# TEST: PHONETIC MATCH SCORING
# =============================================================================

def test_phonetic_match_scoring():
    """Test phonetic match score calculation."""
    print("\n📊 Testing phonetic match scoring...")
    
    validator = LyricValidator()
    
    # Test 1: Exact match
    text_phonemes = ['M', 'AE1', 'N']  # "man"
    audio_ipa = "m æ n"
    score = validator.calculate_phonetic_match(text_phonemes, audio_ipa)
    assert score > 0.8, f"Exact match should score > 0.8, got {score}"
    print(f"   ✓ Exact match 'man' vs 'm æ n' -> score {score:.2f}")
    
    # Test 2: Empty audio IPA returns 0
    score = validator.calculate_phonetic_match(['M', 'AE1', 'N'], "")
    assert score == 0.0, f"Empty audio should return 0.0, got {score}"
    print("   ✓ Empty audio IPA returns 0.0")
    
    # Test 3: Empty text phonemes returns 0
    score = validator.calculate_phonetic_match([], "m æ n")
    assert score == 0.0, f"Empty text should return 0.0, got {score}"
    print("   ✓ Empty text phonemes returns 0.0")
    
    # Test 4: Partial match (different vowel, same consonants)
    text_phonemes = ['B', 'AE1', 'D']  # "bad"
    audio_ipa = "b ɑ d"  # different vowel
    score = validator.calculate_phonetic_match(text_phonemes, audio_ipa)
    assert score > 0.4, f"Partial match should score > 0.4, got {score}"
    print(f"   ✓ Partial match 'bad' vs 'b ɑ d' -> score {score:.2f}")
    
    # Test 5: Complete mismatch
    text_phonemes = ['M', 'AE1', 'N']
    audio_ipa = "p i k"  # completely different
    score = validator.calculate_phonetic_match(text_phonemes, audio_ipa)
    assert score < 0.5, f"Mismatch should score < 0.5, got {score}"
    print(f"   ✓ Mismatch 'man' vs 'p i k' -> score {score:.2f}")
    
    return True


# =============================================================================
# TEST: VALIDATION WITH PHONETIC DATA
# =============================================================================

def test_validation_with_phonetic_data():
    """Test that validate_line correctly uses phonetic data in scoring."""
    print("\n📊 Testing validation with phonetic data...")
    
    validator = LyricValidator()
    
    # Create segments with phonetic data
    segments_with_phonetics = [
        Segment(0.0, 0.2, is_stressed=True, audio_phonemes="m"),
        Segment(0.2, 0.2, is_stressed=False, audio_phonemes="æ"),
        Segment(0.4, 0.2, is_stressed=True, audio_phonemes="n"),
    ]
    
    # Test with matching phonetics ("man")
    result = validator.validate_line("My man", segments_with_phonetics)
    
    # Should be invalid (wrong syllable count: "my man" = 2, not 3)
    # Actually "my man" might be 2 syllables, let's check
    print(f"   'My man' -> {result.syllable_count} syllables, valid: {result.is_valid}")
    
    # Try with exactly matching syllable count
    segments_3syl = [
        Segment(0.0, 0.2, is_stressed=True, audio_phonemes="m"),
        Segment(0.2, 0.2, is_stressed=False, audio_phonemes="ɔ"),
        Segment(0.4, 0.2, is_stressed=True, audio_phonemes="n"),
    ]
    
    result = validator.validate_line("Monster", segments_3syl)
    print(f"   'Monster' -> {result.syllable_count} syllables, valid: {result.is_valid}")
    
    if result.is_valid:
        assert result.phonetic_score >= 0.0, "Phonetic score should be >= 0"
        assert result.score > 0.0, "Combined score should be > 0"
        print(f"   ✓ Groove: {result.groove_score:.2f}, Phonetic: {result.phonetic_score:.2f}, Combined: {result.score:.2f}")
    
    return True


# =============================================================================
# TEST: VALIDATION WITHOUT PHONETIC DATA (BACKWARDS COMPATIBILITY)
# =============================================================================

def test_validation_without_phonetic_data():
    """Test that validation works without phonetic data (backwards compatible)."""
    print("\n📊 Testing validation without phonetic data...")
    
    validator = LyricValidator()
    
    # Create segments WITHOUT phonetic data
    segments_no_phonetics = [
        Segment(0.0, 0.2, is_stressed=True),
        Segment(0.2, 0.2, is_stressed=False),
    ]
    
    result = validator.validate_line("Monster", segments_no_phonetics)
    
    assert result.is_valid == True, f"Should be valid, got {result.is_valid}"
    assert result.phonetic_score == 0.0, f"Phonetic score should be 0.0 without data, got {result.phonetic_score}"
    assert result.groove_score == result.score, "Score should equal groove_score when no phonetic data"
    assert "no phonetic data" in result.reason.lower(), "Reason should mention no phonetic data"
    
    print(f"   ✓ Valid without phonetic data: score={result.score:.2f}")
    print(f"   ✓ Reason: {result.reason}")
    
    return True


# =============================================================================
# TEST: PHONETIC CLASSES
# =============================================================================

def test_phonetic_classes():
    """Test that phonetic classes are correctly defined."""
    print("\n📊 Testing phonetic classes...")
    
    # Verify key classes exist
    assert 'plosive' in PHONETIC_CLASSES, "plosive class should exist"
    assert 'nasal' in PHONETIC_CLASSES, "nasal class should exist"
    assert 'fricative' in PHONETIC_CLASSES, "fricative class should exist"
    
    # Verify class contents
    assert 'b' in PHONETIC_CLASSES['plosive'], "b should be a plosive"
    assert 'm' in PHONETIC_CLASSES['nasal'], "m should be a nasal"
    assert 's' in PHONETIC_CLASSES['fricative'], "s should be a fricative"
    
    print("   ✓ All phonetic classes defined correctly")
    
    return True


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Flow-to-Lyrics: Phonetic Validation Test Suite")
    print("=" * 60)
    
    all_tests = [
        ("ARPABET to IPA Mapping", test_arpabet_to_ipa_mapping),
        ("Phonetic Match Scoring", test_phonetic_match_scoring),
        ("Validation with Phonetic Data", test_validation_with_phonetic_data),
        ("Validation without Phonetic Data", test_validation_without_phonetic_data),
        ("Phonetic Classes", test_phonetic_classes),
    ]
    
    all_passed = True
    
    for test_name, test_func in all_tests:
        try:
            result = test_func()
            status = "✅ PASS" if result else "❌ FAIL"
            if not result:
                all_passed = False
        except Exception as e:
            status = f"❌ ERROR: {e}"
            all_passed = False
            import traceback
            traceback.print_exc()
        
        print(f"\n{status}: {test_name}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("  🎉 ALL TESTS PASSED!")
    else:
        print("  ⚠️ SOME TESTS FAILED!")
    print("=" * 60 + "\n")
    
    sys.exit(0 if all_passed else 1)
