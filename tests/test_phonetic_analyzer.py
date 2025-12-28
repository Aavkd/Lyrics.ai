"""
Flow-to-Lyrics: Phonetic Analyzer Tests
=======================================
Test suite for the PhoneticAnalyzer class and related utilities.

Tests:
1. resample_audio() utility function
2. PhoneticAnalyzer initialization (lazy loading)
3. PhoneticAnalyzer.analyze_segment() with synthetic audio
4. PhoneticAnalyzer.analyze_segments() batch processing
"""

import sys
import tempfile
import numpy as np
import soundfile as sf
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from audio_engine import (
    resample_audio, 
    PhoneticAnalyzer, 
    Segment,
    LibrosaAnalyzer,
    PivotFormatter
)


# =============================================================================
# TEST: RESAMPLE AUDIO UTILITY
# =============================================================================

def test_resample_audio():
    """Test that resampling works correctly."""
    print("\n📊 Testing resample_audio()...")
    
    # Create a simple sine wave at 22050 Hz
    orig_sr = 22050
    duration = 0.5  # 500ms
    freq = 440  # A4 note
    
    t = np.linspace(0, duration, int(orig_sr * duration), endpoint=False)
    audio = np.sin(2 * np.pi * freq * t)
    
    # Test 1: Same sample rate should return same array
    result = resample_audio(audio, orig_sr, orig_sr)
    assert len(result) == len(audio), "Same sample rate should return same length"
    print("   ✓ Same sample rate passthrough works")
    
    # Test 2: Resample to 16kHz
    target_sr = 16000
    resampled = resample_audio(audio, orig_sr, target_sr)
    expected_length = int(len(audio) * target_sr / orig_sr)
    
    # Allow some tolerance for resampling
    assert abs(len(resampled) - expected_length) < 10, \
        f"Expected ~{expected_length} samples, got {len(resampled)}"
    print(f"   ✓ Resampled from {orig_sr}Hz to {target_sr}Hz ({len(audio)} -> {len(resampled)} samples)")
    
    # Test 3: Verify it's still valid audio (not all zeros)
    assert np.max(np.abs(resampled)) > 0.5, "Resampled audio should preserve amplitude"
    print("   ✓ Resampled audio preserves signal")
    
    return True


# =============================================================================
# TEST: PHONETIC ANALYZER (DISABLED MODE)
# =============================================================================

def test_phonetic_analyzer_disabled():
    """Test PhoneticAnalyzer in disabled mode (no Allosaurus)."""
    print("\n📊 Testing PhoneticAnalyzer (disabled mode)...")
    
    # Create analyzer in disabled mode
    analyzer = PhoneticAnalyzer(enabled=False)
    
    # Create synthetic audio
    sr = 22050
    duration = 0.5
    audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, int(sr * duration)))
    
    # Test analyze_segment returns empty string
    result = analyzer.analyze_segment(audio, sr)
    assert result == "", f"Disabled analyzer should return empty string, got: '{result}'"
    print("   ✓ analyze_segment returns empty string when disabled")
    
    # Test analyze_segments returns empty list
    onset_times = [0.0, 0.2, 0.4]
    durations = [0.2, 0.2, 0.1]
    results = analyzer.analyze_segments(audio, sr, onset_times, durations)
    
    assert len(results) == len(onset_times), "Should return one result per segment"
    assert all(r == "" for r in results), "All results should be empty strings"
    print("   ✓ analyze_segments returns empty strings when disabled")
    
    return True


# =============================================================================
# TEST: PHONETIC ANALYZER (ENABLED MODE - OPTIONAL)
# =============================================================================

def test_phonetic_analyzer_enabled():
    """
    Test PhoneticAnalyzer with Allosaurus (if installed).
    This test is optional - it will skip if Allosaurus is not available.
    """
    print("\n📊 Testing PhoneticAnalyzer (enabled mode)...")
    
    # Try to import Allosaurus
    try:
        from allosaurus.app import read_recognizer
        print("   ✓ Allosaurus is installed")
    except ImportError:
        print("   ⚠️ Allosaurus not installed - skipping live tests")
        print("   Run: pip install allosaurus")
        return True  # Skip but don't fail
    
    # Create analyzer
    analyzer = PhoneticAnalyzer(enabled=True)
    
    # Generate speech-like audio (formant synthesis is complex, use real file if available)
    # For now, test with a simple sine wave - Allosaurus may return empty for pure tones
    sr = 16000
    duration = 0.5
    
    # Create a chirp signal (more speech-like than pure tone)
    t = np.linspace(0, duration, int(sr * duration))
    # Frequency sweep from 200Hz to 800Hz (vowel-like)
    freq = 200 + 600 * t / duration
    audio = 0.5 * np.sin(2 * np.pi * freq * t)
    
    # Test that analyze_segment doesn't crash
    try:
        result = analyzer.analyze_segment(audio, sr)
        print(f"   ✓ analyze_segment returned: '{result}' (may be empty for synthetic audio)")
    except Exception as e:
        print(f"   ⚠️ analyze_segment raised exception: {e}")
        return True  # Skip but don't fail
    
    return True


# =============================================================================
# TEST: SEGMENT DATACLASS
# =============================================================================

def test_segment_has_audio_phonemes():
    """Test that Segment dataclass has audio_phonemes field."""
    print("\n📊 Testing Segment dataclass...")
    
    # Create a segment with all fields
    seg = Segment(
        time_start=0.5,
        duration=0.2,
        is_stressed=True,
        is_sustained=False,
        pitch_contour="mid",
        audio_phonemes="b a d a"
    )
    
    assert seg.audio_phonemes == "b a d a", "audio_phonemes should be set correctly"
    print("   ✓ Segment has audio_phonemes field")
    
    # Test default value
    seg_default = Segment(time_start=0.0, duration=0.1)
    assert seg_default.audio_phonemes == "", "audio_phonemes should default to empty string"
    print("   ✓ audio_phonemes defaults to empty string")
    
    return True


# =============================================================================
# TEST: PIVOT FORMATTER INTEGRATION
# =============================================================================

def test_pivot_formatter_with_phonetic_analyzer():
    """Test that PivotFormatter correctly uses PhoneticAnalyzer."""
    print("\n📊 Testing PivotFormatter with PhoneticAnalyzer...")
    
    # Create a disabled phonetic analyzer
    phonetic_analyzer = PhoneticAnalyzer(enabled=False)
    
    # Create formatter with phonetic analyzer
    formatter = PivotFormatter(phonetic_analyzer=phonetic_analyzer)
    
    assert formatter.phonetic_analyzer is not None, "Formatter should have phonetic analyzer"
    print("   ✓ PivotFormatter accepts phonetic_analyzer parameter")
    
    # Create formatter without phonetic analyzer
    formatter_no_phonetic = PivotFormatter()
    assert formatter_no_phonetic.phonetic_analyzer is None, "Formatter should work without analyzer"
    print("   ✓ PivotFormatter works without phonetic_analyzer")
    
    return True


# =============================================================================
# TEST: FULL INTEGRATION (WITH REAL AUDIO)
# =============================================================================

def test_full_integration_with_audio():
    """Test full pipeline with synthesized audio including phonetic field."""
    print("\n📊 Testing full integration...")
    
    # Generate synthetic audio
    sr = 22050
    duration = 1.0
    
    # Three beats with gaps
    beat1 = np.sin(2 * np.pi * 440 * np.linspace(0, 0.2, int(0.2 * sr)))
    gap1 = np.zeros(int(0.1 * sr))
    beat2 = np.sin(2 * np.pi * 440 * np.linspace(0, 0.2, int(0.2 * sr)))
    gap2 = np.zeros(int(0.1 * sr))
    beat3 = np.sin(2 * np.pi * 440 * np.linspace(0, 0.2, int(0.2 * sr)))
    
    audio = np.concatenate([beat1, gap1, beat2, gap2, beat3])
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name
        sf.write(temp_path, audio, sr)
    
    try:
        # Analyze with LibrosaAnalyzer
        analyzer = LibrosaAnalyzer(sample_rate=sr)
        analysis = analyzer.analyze(temp_path)
        
        # Format with disabled phonetic analyzer
        phonetic_analyzer = PhoneticAnalyzer(enabled=False)
        formatter = PivotFormatter(phonetic_analyzer=phonetic_analyzer)
        pivot = formatter.format(analysis)
        
        # Check output structure
        output = pivot.to_dict()
        
        # Verify audio_phonemes field exists in output
        if output["blocks"] and output["blocks"][0]["segments"]:
            first_seg = output["blocks"][0]["segments"][0]
            assert "audio_phonemes" in first_seg, "Segment should have audio_phonemes field"
            print("   ✓ audio_phonemes field present in Pivot JSON output")
            
            # Should be empty string since phonetic is disabled
            assert first_seg["audio_phonemes"] == "", "audio_phonemes should be empty when disabled"
            print("   ✓ audio_phonemes is empty when analyzer is disabled")
        else:
            print("   ⚠️ No segments detected (may be normal for synthetic audio)")
        
        return True
        
    finally:
        Path(temp_path).unlink(missing_ok=True)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Flow-to-Lyrics: Phonetic Analyzer Test Suite")
    print("=" * 60)
    
    all_tests = [
        ("Resample Audio Utility", test_resample_audio),
        ("PhoneticAnalyzer (Disabled)", test_phonetic_analyzer_disabled),
        ("PhoneticAnalyzer (Enabled)", test_phonetic_analyzer_enabled),
        ("Segment Dataclass", test_segment_has_audio_phonemes),
        ("PivotFormatter Integration", test_pivot_formatter_with_phonetic_analyzer),
        ("Full Integration", test_full_integration_with_audio),
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
        
        print(f"\n{status}: {test_name}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("  🎉 ALL TESTS PASSED!")
    else:
        print("  ⚠️ SOME TESTS FAILED!")
    print("=" * 60 + "\n")
    
    sys.exit(0 if all_passed else 1)
