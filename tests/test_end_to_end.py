"""
Flow-to-Lyrics: End-to-End Tests
================================
Integration tests for the complete audio-to-lyrics pipeline.

Tests:
1. Validator logic (unit test for LyricValidator)
2. Full pipeline execution with test_audio_real.mp3

Run with: pytest tests/test_end_to_end.py -v
Or standalone: python tests/test_end_to_end.py
"""

import os
import sys

import pytest

# Add parent dir to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio_engine import Segment
from core_pipeline import CorePipeline
from validator import LyricValidator, ValidationResult


# =============================================================================
# TEST: VALIDATOR LOGIC
# =============================================================================

def test_validator_syllable_counting():
    """Test that the validator correctly counts syllables using g2p_en."""
    print("\n📊 Testing Syllable Counting...")
    
    validator = LyricValidator()
    
    # Test known syllable counts
    test_cases = [
        ("Fire", 2),           # F AY1 ER0
        ("Every", 3),          # EH1 V ER0 IY0 (varies by accent)
        ("Monster", 2),        # M AA1 N S T ER0
        ("City", 2),           # S IH1 T IY0
        ("Power", 2),          # P AW1 ER0
        ("Yeah", 1),           # Y AE1
        ("Running", 2),        # R AH1 N IH0 NG
        ("I", 1),              # AY1
        ("The", 1),            # DH AH0
        ("Machine", 2),        # M AH0 SH IY1 N
    ]
    
    for word, expected in test_cases:
        actual, _, _ = validator.count_syllables(word)
        print(f"   '{word}': expected {expected}, got {actual}")
        assert actual == expected, f"Syllable mismatch for '{word}'"
    
    print("   ✓ All syllable counts correct!")


def test_validator_stress_extraction():
    """Test that stress markers are correctly extracted from phonemes."""
    print("\n🎯 Testing Stress Extraction...")
    
    validator = LyricValidator()
    
    # "Monster City" -> M AA1 N S T ER0 + S IH1 T IY0
    # Expected stress: [1, 0, 1, 0] (Primary, Unstressed, Primary, Unstressed)
    _, _, stress = validator.count_syllables("Monster City")
    
    print(f"   'Monster City' stress pattern: {stress}")
    assert len(stress) == 4, f"Expected 4 stress markers, got {len(stress)}"
    assert stress[0] == 1, "First syllable should be stressed (1)"
    assert stress[1] == 0, "Second syllable should be unstressed (0)"
    
    print("   ✓ Stress extraction correct!")


def test_validator_groove_score():
    """Test groove score calculation for stress matching.
    
    Updated for Phase 1 weighted scoring:
    - Stressed matches = 2 points
    - Unstressed matches = 1 point
    - Max points = (stressed_count * 2) + unstressed_count
    """
    print("\n📈 Testing Groove Score Calculation...")
    
    validator = LyricValidator()
    
    # Perfect match: [1, 0] text stress with [True, False] audio stress
    # Max points = (1 * 2) + 1 = 3, earned = 2 + 1 = 3 -> 1.0
    score1 = validator.calculate_groove_score([1, 0], [True, False])
    print(f"   Perfect match [1,0] vs [T,F]: score = {score1}")
    assert score1 == 1.0, "Perfect match should score 1.0"
    
    # Complete mismatch: [0, 1] vs [True, False]
    # Max points = 3, earned = 0 + 0 = 0 -> 0.0
    score2 = validator.calculate_groove_score([0, 1], [True, False])
    print(f"   Mismatch [0,1] vs [T,F]: score = {score2}")
    assert score2 == 0.0, "Complete mismatch should score 0.0"
    
    # Partial match: [1, 1] vs [True, False] (first matches stressed, second misses unstressed)
    # Max points = (1 * 2) + 1 = 3, earned = 2 + 0 = 2 -> 0.667
    score3 = validator.calculate_groove_score([1, 1], [True, False])
    print(f"   Partial [1,1] vs [T,F]: score = {score3:.2f}")
    assert abs(score3 - 0.667) < 0.01, f"Partial match should score ~0.67, got {score3}"
    
    # Empty arrays
    score4 = validator.calculate_groove_score([], [])
    assert score4 == 0.0, "Empty arrays should score 0.0"
    
    print("   ✓ Groove score calculations correct!")


def test_validator_logic():
    """Test full validation logic with mock segments."""
    print("\n⚖️ Testing Validator Logic...")
    
    validator = LyricValidator()
    
    # Mock Segments: LOUD - quiet - LOUD - quiet (DA-da-DA-da)
    segments = [
        Segment(0.0, 0.2, is_stressed=True),   # DA
        Segment(0.2, 0.2, is_stressed=False),  # da
        Segment(0.4, 0.2, is_stressed=True),   # DA
        Segment(0.6, 0.2, is_stressed=False),  # da
    ]
    
    # Candidate 1: Perfect Match
    # "Monster City" -> M AA1 N S T ER0 + S IH1 T IY0 = [1, 0, 1, 0]
    res1 = validator.validate_line("Monster City", segments)
    print(f"   Candidate 'Monster City': Score={res1.score:.2f}, Valid={res1.is_valid}")
    assert res1.is_valid, "Should be valid syllable count"
    assert res1.score > 0.7, f"Should have high groove score, got {res1.score}"
    
    # Candidate 2: Wrong syllable count
    # "The machine" -> DH AH0 + M AH0 SH IY1 N = 3 syllables vs 4 segments
    res2 = validator.validate_line("The machine", segments)
    print(f"   Candidate 'The machine': Valid={res2.is_valid} ({res2.reason})")
    assert not res2.is_valid, "Should fail syllable count (3 vs 4)"
    
    # Candidate 3: Correct count, check scoring
    res3 = validator.validate_line("Power moving", segments)
    print(f"   Candidate 'Power moving': Score={res3.score:.2f}, Syllables={res3.syllable_count}")
    assert res3.syllable_count == 4, f"Expected 4 syllables, got {res3.syllable_count}"
    assert res3.is_valid, "Should be valid (4 syllables)"
    
    # Candidate 4: Wrong count (5 syllables)
    res4 = validator.validate_line("I go crazy now", segments)
    print(f"   Candidate 'I go crazy now': Valid={res4.is_valid}, Syllables={res4.syllable_count}")
    assert not res4.is_valid, "Should fail (5 vs 4)"
    
    print("   ✓ All validator tests passed!")


def test_get_best_candidate():
    """Test best candidate selection logic."""
    print("\n🏆 Testing Best Candidate Selection...")
    
    validator = LyricValidator()
    
    segments = [
        Segment(0.0, 0.2, is_stressed=True),
        Segment(0.2, 0.2, is_stressed=False),
        Segment(0.4, 0.2, is_stressed=True),
        Segment(0.6, 0.2, is_stressed=False),
    ]
    
    candidates = [
        "The machine",         # 3 syllables - invalid
        "Monster City",        # 4 syllables, good stress [1,0,1,0]
        "Power moving",        # 4 syllables
        "I go crazy now",      # 5 syllables - invalid
    ]
    
    best_text, best_result = validator.get_best_candidate(candidates, segments)
    
    print(f"   Best: '{best_text}' with score {best_result.score if best_result else 0:.2f}")
    
    assert best_text is not None, "Should find a valid candidate"
    assert best_result.is_valid, "Best result should be valid"
    
    print("   ✓ Best candidate selection works!")


# =============================================================================
# TEST: FULL PIPELINE
# =============================================================================

def test_full_pipeline_execution():
    """Test full pipeline with test_audio_real.mp3."""
    print("\n🚀 Testing Full Pipeline with 'test_audio_real.mp3'...")
    
    audio_file = "test_audio_real.mp3"
    
    # Check if file exists
    if not os.path.exists(audio_file):
        print(f"   ⚠️ Warning: {audio_file} not found.")
        if not os.path.exists("test_audio.wav"):
            pytest.skip("No test audio file available")
        audio_file = "test_audio.wav"
    else:
        print(f"   ✓ Found {audio_file}")
    
    # First, check if Ollama is available using a test pipeline
    test_pipeline = CorePipeline(mock_mode=True)
    ollama_available = False
    try:
        ollama_available = test_pipeline.generation_engine.test_connection()
        if ollama_available:
            print("   ✓ Ollama available - using REAL LLM generation")
        else:
            print("   ⚠️ Ollama not available - using mock mode")
    except Exception as e:
        print(f"   ⚠️ Could not test Ollama connection: {e}")
    
    # Create the actual pipeline
    # AudioEngine stays in mock mode (to skip Demucs), but GenerationEngine uses real LLM if available
    if ollama_available:
        # Create pipeline with real generation but mock audio processing
        from audio_engine import AudioEngine
        from generation_engine import GenerationEngine
        from prompt_engine import PromptEngine
        from validator import LyricValidator
        
        pipeline = CorePipeline.__new__(CorePipeline)
        pipeline.audio_engine = AudioEngine(mock_mode=True)  # Skip Demucs
        pipeline.prompt_engine = PromptEngine()
        pipeline.generation_engine = GenerationEngine(mock_mode=False)  # REAL LLM!
        pipeline.validator = LyricValidator()
        pipeline.mock_mode = False  # For logging purposes
        print("   ✓ Pipeline configured: Mock Audio + REAL LLM")
    else:
        pipeline = CorePipeline(mock_mode=True)
        print("   ✓ Pipeline configured: Full Mock Mode")
    
    try:
        best_lyric, score = pipeline.run_pipeline(audio_file)
        
        print("\n   " + "=" * 50)
        print(f"   🏆 WINNING LYRIC: {best_lyric}")
        print(f"   📊 SCORE: {score}")
        print("   " + "=" * 50)
        
        # With real LLM, we might or might not get a match
        # With mock mode, we expect no match (syllable mismatch)
        assert score >= 0.0, "Score should be non-negative"
        
        if best_lyric:
            print(f"   ✓ Found a valid lyric with score {score:.2f}!")
        else:
            print("   ⚠️ No valid candidates found (expected if syllable counts don't match)")
        
        print("   ✓ Pipeline execution completed!")
        
    except Exception as e:
        pytest.fail(f"Pipeline failed: {e}")


def test_pipeline_with_invalid_file():
    """Test pipeline gracefully handles missing files."""
    print("\n🚫 Testing Pipeline with Invalid File...")
    
    pipeline = CorePipeline(mock_mode=True)
    
    best_lyric, score = pipeline.run_pipeline("nonexistent_file.mp3")
    
    assert best_lyric is None, "Should return None for missing file"
    assert score == 0.0, "Score should be 0.0 for missing file"
    
    print("   ✓ Pipeline handles invalid files gracefully!")


def test_pipeline_initialization():
    """Test that CorePipeline initializes all engines correctly."""
    print("\n🔧 Testing Pipeline Initialization...")
    
    pipeline = CorePipeline(mock_mode=True)
    
    assert pipeline.audio_engine is not None, "AudioEngine should be initialized"
    assert pipeline.prompt_engine is not None, "PromptEngine should be initialized"
    assert pipeline.generation_engine is not None, "GenerationEngine should be initialized"
    assert pipeline.validator is not None, "LyricValidator should be initialized"
    assert pipeline.mock_mode is True, "Mock mode should be set"
    
    print("   ✓ All engines initialized correctly!")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  🧪 FLOW-TO-LYRICS: END-TO-END TEST SUITE")
    print("=" * 70)
    
    # Run all tests manually for detailed output
    all_passed = True
    
    tests = [
        ("Syllable Counting", test_validator_syllable_counting),
        ("Stress Extraction", test_validator_stress_extraction),
        ("Groove Score", test_validator_groove_score),
        ("Validator Logic", test_validator_logic),
        ("Best Candidate Selection", test_get_best_candidate),
        ("Pipeline Initialization", test_pipeline_initialization),
        ("Invalid File Handling", test_pipeline_with_invalid_file),
        ("Full Pipeline", test_full_pipeline_execution),
    ]
    
    for name, test_func in tests:
        try:
            test_func()
            print(f"\n   ✅ {name}: PASSED")
        except AssertionError as e:
            print(f"\n   ❌ {name}: FAILED - {e}")
            all_passed = False
        except Exception as e:
            print(f"\n   ❌ {name}: ERROR - {e}")
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("  ✅ ALL TESTS PASSED!")
    else:
        print("  ⚠️ SOME TESTS FAILED!")
    print("=" * 70 + "\n")
