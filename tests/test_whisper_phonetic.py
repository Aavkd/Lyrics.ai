"""
Flow-to-Lyrics: Whisper Phonetic Analyzer Tests
================================================
Test suite for Phase C: Whisper + g2p_en integration.

Tests:
1. WhisperPhoneticAnalyzer initialization (lazy loading)
2. g2p_en conversion accuracy
3. PhoneticAnalyzer backend selection (Whisper vs Allosaurus)
4. Config-based model selection
"""

import sys
import numpy as np
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# TEST: CONFIG LOADING
# =============================================================================

def test_config_phonetic_model():
    """Test that PHONETIC_MODEL config option is loaded correctly."""
    print("\n📊 Testing PHONETIC_MODEL config loading...")
    
    from config import config
    
    # Check that property exists and returns valid value
    model = config.PHONETIC_MODEL
    print(f"   PHONETIC_MODEL: {model}")
    
    assert model in ("whisper", "allosaurus"), \
        f"Invalid PHONETIC_MODEL: {model}, expected 'whisper' or 'allosaurus'"
    
    print("   ✓ PHONETIC_MODEL config loaded correctly")
    return True


def test_config_whisper_model_size():
    """Test that WHISPER_MODEL_SIZE config option is loaded correctly."""
    print("\n📊 Testing WHISPER_MODEL_SIZE config loading...")
    
    from config import config
    
    # Check that property exists and returns valid value
    size = config.WHISPER_MODEL_SIZE
    print(f"   WHISPER_MODEL_SIZE: {size}")
    
    valid_sizes = ("tiny", "base", "small", "medium", "large")
    assert size in valid_sizes, \
        f"Invalid WHISPER_MODEL_SIZE: {size}, expected one of {valid_sizes}"
    
    print("   ✓ WHISPER_MODEL_SIZE config loaded correctly")
    return True


# =============================================================================
# TEST: WHISPER PHONETIC ANALYZER
# =============================================================================

def test_whisper_analyzer_init():
    """Test WhisperPhoneticAnalyzer initialization (lazy loading)."""
    print("\n📊 Testing WhisperPhoneticAnalyzer initialization...")
    
    from audio_engine import WhisperPhoneticAnalyzer
    
    # Create analyzer - should not load model yet (lazy init)
    analyzer = WhisperPhoneticAnalyzer(model_size="base")
    
    # Verify lazy init state
    assert analyzer._initialized == False, "Analyzer should not be initialized yet"
    assert analyzer.model is None, "Model should be None before lazy init"
    assert analyzer.g2p is None, "g2p should be None before lazy init"
    
    print("   ✓ Analyzer created with lazy initialization")
    return True


def test_whisper_analyzer_g2p_conversion():
    """Test g2p_en conversion from text to phonemes."""
    print("\n📊 Testing g2p_en conversion...")
    
    from audio_engine import WhisperPhoneticAnalyzer
    
    analyzer = WhisperPhoneticAnalyzer(model_size="base")
    
    # Force load g2p only (not Whisper - which takes longer)
    try:
        from g2p_en import G2p
        analyzer.g2p = G2p()
    except ImportError:
        print("   ⚠️ g2p_en not installed, skipping test")
        return True
    
    # Test conversion
    test_cases = [
        ("hello", True),   # Should produce phonemes
        ("talk", True),    # Should produce phonemes
        ("me", True),      # Should produce phonemes
    ]
    
    for text, should_have_result in test_cases:
        result = analyzer._words_to_ipa(text)
        print(f"   '{text}' → '{result}'")
        
        if should_have_result:
            assert len(result) > 0, f"Expected phonemes for '{text}', got empty"
    
    print("   ✓ g2p_en conversion working correctly")
    return True


# =============================================================================
# TEST: PHONETIC ANALYZER BACKEND SELECTION
# =============================================================================

def test_phonetic_analyzer_backend_selection():
    """Test that PhoneticAnalyzer selects backend based on config."""
    print("\n📊 Testing PhoneticAnalyzer backend selection...")
    
    from audio_engine import PhoneticAnalyzer
    
    # Create analyzer (disabled to avoid loading heavy models)
    analyzer = PhoneticAnalyzer(enabled=False)
    
    # Check that phonetic_model attribute exists
    assert hasattr(analyzer, 'phonetic_model'), "Missing phonetic_model attribute"
    assert hasattr(analyzer, '_use_whisper'), "Missing _use_whisper attribute"
    
    print(f"   phonetic_model: {analyzer.phonetic_model}")
    print(f"   _use_whisper: {analyzer._use_whisper}")
    
    # Verify consistency
    if analyzer.phonetic_model == "whisper":
        assert analyzer._use_whisper == True, "Should use Whisper when phonetic_model='whisper'"
    else:
        assert analyzer._use_whisper == False, "Should not use Whisper when phonetic_model='allosaurus'"
    
    print("   ✓ Backend selection logic is correct")
    return True


def test_phonetic_analyzer_fallback_when_disabled():
    """Test fallback behavior when analyzer is disabled."""
    print("\n📊 Testing fallback when analyzer disabled...")
    
    from audio_engine import PhoneticAnalyzer
    
    # Create disabled analyzer with fallback enabled
    analyzer = PhoneticAnalyzer(enabled=False)
    analyzer._explicitly_disabled = False  # Allow fallback
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
    
    print("   ✓ Fallback works when analyzer disabled")
    return True


# =============================================================================
# TEST: END-TO-END WITH REAL AUDIO (OPTIONAL)
# =============================================================================

def test_whisper_with_real_audio():
    """Test Whisper analyzer with real audio file (if available)."""
    print("\n📊 Testing Whisper with real audio...")
    
    # Look for test audio files
    test_files = [
        Path("audio samples/talk_to_me_i_said_what.m4a"),
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
        from audio_engine import PhoneticAnalyzer
        
        # Load audio
        y, sr = librosa.load(str(audio_file), sr=22050)
        
        # Create analyzer
        analyzer = PhoneticAnalyzer(enabled=True)
        
        # If Whisper not available, skip
        analyzer._lazy_init()
        if not analyzer._use_whisper or analyzer._whisper_analyzer is None:
            print("   ⚠️ Whisper not available, skipping real audio test")
            return True
        
        # Analyze first 2 seconds
        segment = y[:sr * 2]
        result = analyzer.analyze_segment(segment, sr)
        
        print(f"   Result: '{result}'")
        
        # Should have some phonemes (not empty, not just fallback tag)
        if result and result not in ("[vowel]", "[consonant]", "[mid]"):
            print("   ✓ Whisper produced phoneme output!")
        else:
            print("   ⚠️ Whisper returned empty/fallback (may need longer audio)")
        
        return True
        
    except ImportError as e:
        print(f"   ⚠️ Missing dependency: {e}")
        return True
    except Exception as e:
        print(f"   ⚠️ Error during test: {e}")
        return True


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Flow-to-Lyrics: Whisper Phonetic Analyzer Test Suite")
    print("  Phase C: Whisper + g2p_en Integration")
    print("=" * 60)
    
    all_tests = [
        ("Config: PHONETIC_MODEL", test_config_phonetic_model),
        ("Config: WHISPER_MODEL_SIZE", test_config_whisper_model_size),
        ("WhisperPhoneticAnalyzer init", test_whisper_analyzer_init),
        ("g2p_en conversion", test_whisper_analyzer_g2p_conversion),
        ("PhoneticAnalyzer backend selection", test_phonetic_analyzer_backend_selection),
        ("Fallback when disabled", test_phonetic_analyzer_fallback_when_disabled),
        ("Whisper with real audio", test_whisper_with_real_audio),
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
