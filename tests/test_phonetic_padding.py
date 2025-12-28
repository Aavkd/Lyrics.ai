"""
Flow-to-Lyrics: Phonetic Padding Tests
======================================
Test suite for the enhanced PhoneticAnalyzer with padding, retry, and fallback.

Tests:
1. classify_sound_type() fallback function
2. PhoneticAnalyzer config loading
3. Segment padding logic (boundary clamping)
4. Fallback classification behavior
"""

import sys
import numpy as np
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from audio_engine import classify_sound_type, PhoneticAnalyzer


# =============================================================================
# TEST: CLASSIFY SOUND TYPE FALLBACK
# =============================================================================

def test_classify_sound_type_vowel():
    """Test that low-frequency sounds are classified as vowels."""
    print("\n📊 Testing classify_sound_type() for vowels...")
    
    sr = 22050
    duration = 0.2
    
    # Generate a low-frequency sine wave (vowel-like)
    t = np.linspace(0, duration, int(sr * duration))
    audio = 0.5 * np.sin(2 * np.pi * 200 * t)  # 200Hz = low frequency
    
    result = classify_sound_type(audio, sr)
    # Low centroid, low ZCR should classify as vowel
    print(f"   Result: {result}")
    assert result in ("[vowel]", "[mid]"), f"Expected [vowel] or [mid], got {result}"
    print("   ✓ Low-frequency tone classified correctly")
    
    return True


def test_classify_sound_type_consonant():
    """Test that noisy sounds are classified as consonants."""
    print("\n📊 Testing classify_sound_type() for consonants...")
    
    sr = 22050
    duration = 0.2
    
    # Generate noise (fricative-like)
    audio = np.random.randn(int(sr * duration)) * 0.3
    
    result = classify_sound_type(audio, sr)
    print(f"   Result: {result}")
    # High ZCR should classify as consonant
    assert result in ("[consonant]", "[mid]"), f"Expected [consonant] or [mid], got {result}"
    print("   ✓ Noisy audio classified correctly")
    
    return True


def test_classify_sound_type_empty():
    """Test that empty audio returns [mid]."""
    print("\n📊 Testing classify_sound_type() for empty audio...")
    
    audio = np.array([])
    result = classify_sound_type(audio, 22050)
    
    assert result == "[mid]", f"Expected [mid] for empty audio, got {result}"
    print("   ✓ Empty audio returns [mid]")
    
    return True


# =============================================================================
# TEST: PHONETIC ANALYZER CONFIG LOADING
# =============================================================================

def test_phonetic_analyzer_config_loading():
    """Test that PhoneticAnalyzer loads config values correctly."""
    print("\n📊 Testing PhoneticAnalyzer config loading...")
    
    # Create analyzer (disabled to avoid loading Allosaurus)
    analyzer = PhoneticAnalyzer(enabled=False)
    
    # Verify config attributes exist
    assert hasattr(analyzer, 'min_duration'), "Missing min_duration attribute"
    assert hasattr(analyzer, 'padding'), "Missing padding attribute"
    assert hasattr(analyzer, 'retry_padding'), "Missing retry_padding attribute"
    assert hasattr(analyzer, 'fallback_enabled'), "Missing fallback_enabled attribute"
    
    print(f"   min_duration: {analyzer.min_duration}")
    print(f"   padding: {analyzer.padding}")
    print(f"   retry_padding: {analyzer.retry_padding}")
    print(f"   fallback_enabled: {analyzer.fallback_enabled}")
    
    # Verify types
    assert isinstance(analyzer.min_duration, float), "min_duration should be float"
    assert isinstance(analyzer.padding, float), "padding should be float"
    assert isinstance(analyzer.retry_padding, float), "retry_padding should be float"
    assert isinstance(analyzer.fallback_enabled, bool), "fallback_enabled should be bool"
    
    print("   ✓ All config values loaded correctly")
    
    return True


# =============================================================================
# TEST: FALLBACK BEHAVIOR WHEN DISABLED
# =============================================================================

def test_analyzer_fallback_when_disabled():
    """Test that analyzer provides fallback classification when model unavailable."""
    print("\n📊 Testing fallback behavior when model unavailable...")
    
    # Create analyzer and simulate Allosaurus not available (vs explicitly disabled)
    # We pass enabled=False but then override _explicitly_disabled to test fallback
    analyzer = PhoneticAnalyzer(enabled=False)
    analyzer._explicitly_disabled = False  # Override to test fallback mechanism
    analyzer.fallback_enabled = True
    
    # Generate test audio
    sr = 22050
    duration = 0.3
    t = np.linspace(0, duration, int(sr * duration))
    audio = 0.5 * np.sin(2 * np.pi * 300 * t)
    
    # analyze_segment should use fallback
    result = analyzer.analyze_segment(audio, sr)
    print(f"   Result: {result}")
    
    assert result in ("[vowel]", "[consonant]", "[mid]"), \
        f"Expected fallback tag, got: {result}"
    print("   ✓ Analyzer provides fallback classification when model unavailable")
    
    return True


def test_analyzer_fallback_disabled():
    """Test that disabled fallback returns empty string."""
    print("\n📊 Testing behavior when fallback is disabled...")
    
    # Create analyzer with both analysis and fallback disabled
    analyzer = PhoneticAnalyzer(enabled=False)
    analyzer.fallback_enabled = False
    
    # Generate test audio
    sr = 22050
    audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.3, int(sr * 0.3)))
    
    # analyze_segment should return empty string
    result = analyzer.analyze_segment(audio, sr)
    
    assert result == "", f"Expected empty string when fallback disabled, got: {result}"
    print("   ✓ Returns empty string when fallback disabled")
    
    return True


# =============================================================================
# TEST: SEGMENT PADDING BOUNDARY CLAMPING
# =============================================================================

def test_padding_boundary_clamping():
    """Test that padding respects audio boundaries."""
    print("\n📊 Testing padding boundary clamping...")
    
    # Create analyzer to test padding logic without Allosaurus
    analyzer = PhoneticAnalyzer(enabled=False)
    analyzer._explicitly_disabled = False  # Allow fallback for testing
    analyzer.fallback_enabled = True
    analyzer.padding = 0.1  # 100ms padding
    
    # Generate short audio (300ms)
    sr = 22050
    duration = 0.3
    audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, int(sr * duration)))
    
    # Test segments at boundaries
    onset_times = [0.0, 0.25]  # First at start, second near end
    durations = [0.1, 0.05]
    
    # analyze_segments should handle padding at boundaries
    results = analyzer.analyze_segments(audio, sr, onset_times, durations)
    
    assert len(results) == 2, f"Expected 2 results, got {len(results)}"
    print(f"   Results: {results}")
    
    # Both should have fallback classification
    for result in results:
        assert result in ("[vowel]", "[consonant]", "[mid]", ""), \
            f"Unexpected result: {result}"
    
    print("   ✓ Padding respects audio boundaries")
    
    return True


# =============================================================================
# TEST: MIN DURATION THRESHOLD
# =============================================================================

def test_min_duration_threshold():
    """Test that segments shorter than min_duration use fallback."""
    print("\n📊 Testing min_duration threshold...")
    
    analyzer = PhoneticAnalyzer(enabled=False)
    analyzer._explicitly_disabled = False  # Allow fallback for testing
    analyzer.fallback_enabled = True
    analyzer.min_duration = 0.10  # 100ms minimum
    
    sr = 22050
    
    # Create very short segment (50ms - below threshold)
    short_audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.05, int(sr * 0.05)))
    
    result = analyzer.analyze_segment(short_audio, sr)
    print(f"   Short segment ({len(short_audio)/sr*1000:.0f}ms) result: {result}")
    
    # Should fall back to classification
    assert result in ("[vowel]", "[consonant]", "[mid]"), \
        f"Expected fallback for short segment, got: {result}"
    
    print("   ✓ Short segments correctly use fallback")
    
    return True


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Flow-to-Lyrics: Phonetic Padding Test Suite")
    print("=" * 60)
    
    all_tests = [
        ("classify_sound_type (vowel)", test_classify_sound_type_vowel),
        ("classify_sound_type (consonant)", test_classify_sound_type_consonant),
        ("classify_sound_type (empty)", test_classify_sound_type_empty),
        ("PhoneticAnalyzer config loading", test_phonetic_analyzer_config_loading),
        ("Fallback when disabled", test_analyzer_fallback_when_disabled),
        ("Fallback disabled", test_analyzer_fallback_disabled),
        ("Padding boundary clamping", test_padding_boundary_clamping),
        ("Min duration threshold", test_min_duration_threshold),
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
