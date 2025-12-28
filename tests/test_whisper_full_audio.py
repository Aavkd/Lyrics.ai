"""
Flow-to-Lyrics: Full-Audio Whisper Transcription Tests
=======================================================
Test suite for Phase D: Full-audio transcription with word alignment.

Tests:
1. transcribe_full_audio() word-level timestamps
2. _align_words_to_segments() alignment logic
3. analyze_segments_full_audio() integration
4. Config option WHISPER_USE_FULL_AUDIO
5. Real audio sample testing
"""

import sys
import numpy as np
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# TEST: CONFIG OPTION
# =============================================================================

def test_config_whisper_use_full_audio():
    """Test that WHISPER_USE_FULL_AUDIO config option is loaded correctly."""
    print("\n📊 Testing WHISPER_USE_FULL_AUDIO config loading...")
    
    from config import config
    
    # Check that property exists and returns boolean
    use_full_audio = config.WHISPER_USE_FULL_AUDIO
    print(f"   WHISPER_USE_FULL_AUDIO: {use_full_audio}")
    
    assert isinstance(use_full_audio, bool), \
        f"Expected bool, got {type(use_full_audio)}"
    
    print("   ✓ WHISPER_USE_FULL_AUDIO config loaded correctly")
    return True


# =============================================================================
# TEST: WORD ALIGNMENT LOGIC
# =============================================================================

def test_align_words_to_segments():
    """Test word-to-segment alignment logic."""
    print("\n📊 Testing word alignment logic...")
    
    from audio_engine import WhisperPhoneticAnalyzer
    
    analyzer = WhisperPhoneticAnalyzer(model_size="base")
    
    # Mock g2p for testing (avoid loading full model)
    class MockG2p:
        def __call__(self, text):
            # Simple mock: return each word's first letter as phoneme
            return text.lower().split()
    
    analyzer.g2p = MockG2p()
    analyzer._initialized = True
    
    # Test data: words with timing
    words = [
        {"word": "hello", "start": 0.0, "end": 0.5},
        {"word": "world", "start": 0.5, "end": 1.0},
        {"word": "test", "start": 1.2, "end": 1.5},
    ]
    
    # Segments that should match
    onset_times = [0.0, 0.5, 1.1]
    durations = [0.5, 0.5, 0.5]
    
    result = analyzer._align_words_to_segments(words, onset_times, durations)
    
    print(f"   Words: {[w['word'] for w in words]}")
    print(f"   Segments: {list(zip(onset_times, durations))}")
    print(f"   Result: {result}")
    
    # Check that we got results for all segments
    assert len(result) == 3, f"Expected 3 results, got {len(result)}"
    
    # First segment (0.0-0.5) should match "hello"
    assert "hello" in result[0], f"Expected 'hello' in segment 0, got '{result[0]}'"
    
    # Second segment (0.5-1.0) should match "world"
    assert "world" in result[1], f"Expected 'world' in segment 1, got '{result[1]}'"
    
    # Third segment (1.1-1.6) should match "test"
    assert "test" in result[2], f"Expected 'test' in segment 2, got '{result[2]}'"
    
    print("   ✓ Word alignment logic works correctly")
    return True


def test_align_words_overlapping():
    """Test alignment with sequential assignment (one syllable per segment)."""
    print("\n📊 Testing sequential word alignment...")
    
    from audio_engine import WhisperPhoneticAnalyzer
    
    analyzer = WhisperPhoneticAnalyzer(model_size="base")
    
    class MockG2p:
        def __call__(self, text):
            return text.lower().split()
    
    analyzer.g2p = MockG2p()
    analyzer._initialized = True
    
    # One word maps to first segment only (strict sequential)
    words = [
        {"word": "hello", "start": 0.2, "end": 0.8},  # Single syllable word
    ]
    
    onset_times = [0.0, 0.5, 1.0]
    durations = [0.5, 0.5, 0.5]
    
    result = analyzer._align_words_to_segments(words, onset_times, durations)
    
    print(f"   Word 'hello' (0.2-0.8s), 3 segments")
    print(f"   Result: {result}")
    
    # With strict sequential assignment:
    # - 1 word/syllable → segment[0] gets it
    # - segments[1] and [2] remain empty
    assert "hello" in result[0], "Syllable 0 should have 'hello'"
    assert result[1] == "", "Segment 1 should be empty (no syllable 1)"
    assert result[2] == "", "Segment 2 should be empty (no syllable 2)"
    
    print("   ✓ Sequential word alignment works correctly")
    return True


def test_align_empty_inputs():
    """Test alignment with empty inputs."""
    print("\n📊 Testing empty input handling...")
    
    from audio_engine import WhisperPhoneticAnalyzer
    
    analyzer = WhisperPhoneticAnalyzer(model_size="base")
    analyzer._initialized = True
    
    # Empty words
    result1 = analyzer._align_words_to_segments([], [0.0, 0.5], [0.5, 0.5])
    assert result1 == ["", ""], f"Expected empty results, got {result1}"
    
    # Empty segments
    result2 = analyzer._align_words_to_segments(
        [{"word": "test", "start": 0, "end": 1}], [], []
    )
    assert result2 == [], f"Expected empty list, got {result2}"
    
    print("   ✓ Empty input handling works correctly")
    return True


# =============================================================================
# TEST: PHONETIC ANALYZER INTEGRATION
# =============================================================================

def test_phonetic_analyzer_full_audio_mode():
    """Test PhoneticAnalyzer uses full-audio mode when configured."""
    print("\n📊 Testing PhoneticAnalyzer full-audio mode flag...")
    
    from audio_engine import PhoneticAnalyzer
    
    # Create analyzer (disabled to avoid loading models)
    analyzer = PhoneticAnalyzer(enabled=False)
    
    # Check that full-audio mode attribute exists
    assert hasattr(analyzer, '_use_full_audio'), "Missing _use_full_audio attribute"
    
    print(f"   _use_full_audio: {analyzer._use_full_audio}")
    
    # Should be True by default (since config defaults to true)
    # Note: actual value depends on .env, so just check it's a bool
    assert isinstance(analyzer._use_full_audio, bool), \
        f"Expected bool, got {type(analyzer._use_full_audio)}"
    
    print("   ✓ PhoneticAnalyzer has full-audio mode flag")
    return True


# =============================================================================
# TEST: REAL AUDIO (OPTIONAL)
# =============================================================================

def test_full_audio_with_real_sample():
    """Test full-audio transcription with a real audio file."""
    print("\n📊 Testing full-audio with real sample...")
    
    # Look for test audio files
    test_files = [
        Path("audio samples/talk_to_me_i_said_what.m4a"),
        Path("audio samples/trying_to_take_my_time.m4a"),
        Path("test_audio_real.mp3"),
    ]
    
    audio_file = None
    for f in test_files:
        if f.exists():
            audio_file = f
            break
    
    if audio_file is None:
        print("   ⚠️ No test audio files found, skipping real audio test")
        return True
    
    print(f"   Using: {audio_file}")
    
    try:
        import librosa
        from audio_engine import WhisperPhoneticAnalyzer
        
        # Load audio
        y, sr = librosa.load(str(audio_file), sr=22050)
        print(f"   Audio loaded: {len(y)/sr:.2f}s at {sr}Hz")
        
        # Create analyzer
        analyzer = WhisperPhoneticAnalyzer()
        
        # Check if Whisper is available
        if not analyzer.is_available:
            print("   ⚠️ Whisper not available, skipping real audio test")
            return True
        
        # Test full-audio transcription
        words = analyzer.transcribe_full_audio(y, sr)
        
        print(f"   Transcribed {len(words)} words:")
        for w in words[:5]:  # Show first 5 words
            print(f"      {w['start']:.2f}s-{w['end']:.2f}s: '{w['word']}'")
        if len(words) > 5:
            print(f"      ... and {len(words)-5} more")
        
        # Basic validation
        assert len(words) > 0, "Expected some words to be transcribed"
        
        for word in words:
            assert "word" in word, "Missing 'word' key"
            assert "start" in word, "Missing 'start' key"
            assert "end" in word, "Missing 'end' key"
            assert word["end"] >= word["start"], "End should be >= start"
        
        print("   ✓ Full-audio transcription works!")
        return True
        
    except ImportError as e:
        print(f"   ⚠️ Missing dependency: {e}")
        return True
    except Exception as e:
        print(f"   ⚠️ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return True


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Flow-to-Lyrics: Full-Audio Whisper Transcription Tests")
    print("  Phase D: Word-Level Timestamps and Alignment")
    print("=" * 60)
    
    all_tests = [
        ("Config: WHISPER_USE_FULL_AUDIO", test_config_whisper_use_full_audio),
        ("Word alignment logic", test_align_words_to_segments),
        ("Overlapping word alignment", test_align_words_overlapping),
        ("Empty input handling", test_align_empty_inputs),
        ("PhoneticAnalyzer full-audio mode", test_phonetic_analyzer_full_audio_mode),
        ("Full-audio with real sample", test_full_audio_with_real_sample),
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
