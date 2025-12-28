"""
Flow-to-Lyrics: Generation Engine Test Suite
=============================================
Tests the GenerationEngine's ability to communicate with Ollama
and robustly parse LLM responses.

Test Focus:
1. Real Ollama connection and model availability
2. Robust JSON parsing from "dirty" LLM output
3. Integration test with real LLM generation (model from config)

Configuration:
    Model and Ollama settings are loaded from .env file via config module.
"""

import sys
import os

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from generation_engine import GenerationEngine


def test_ollama_connection():
    """Test that Ollama is running and configured model is available."""
    print(f"\n🔌 Testing Ollama Connection (model: {config.OLLAMA_MODEL})...")
    
    engine = GenerationEngine()
    
    if engine.test_connection():
        print(f"✅ Ollama is running and {config.OLLAMA_MODEL} is available")
        return True
    else:
        print("❌ FAIL: Cannot connect to Ollama or model not found")
        print("   Make sure Ollama is running: ollama serve")
        print(f"   Make sure model is pulled: ollama pull {config.OLLAMA_MODEL}")
        return False


def test_robust_json_parsing():
    """Test that the parser handles dirty LLM output correctly."""
    print("\n🧪 Testing Robust JSON Parsing (Dirty Output)...")
    
    engine = GenerationEngine()
    
    # Simulate a "chatty" 3B model response with markdown and filler text
    dirty_response = """
    Sure! Here are 5 variations for your trap beat:
    
    ```json
    {
        "candidates": [
            "Riding through the city",
            "Never looking back now",
            "Money on my mind state",
            "Living for the moment",
            "Sky is not the limit"
        ]
    }
    ```
    
    Hope this helps!
    """
    
    # Test the private parsing method directly
    parsed = engine._clean_and_parse_json(dirty_response)
    
    print(f"   Parsed candidates: {parsed}")
    
    assert len(parsed) == 5, f"Expected 5 candidates, got {len(parsed)}"
    assert parsed[0] == "Riding through the city", f"First candidate mismatch: {parsed[0]}"
    
    print("✅ Successfully extracted JSON from markdown/conversational filler.")
    return True


def test_malformed_json_recovery():
    """Test handling of common LLM JSON errors like trailing commas."""
    print("\n🧪 Testing Malformed JSON Recovery...")
    
    engine = GenerationEngine()
    
    # JSON with a common LLM error (trailing comma)
    malformed_response = """
    {
        "candidates": [
            "Line one",
            "Line two", 
        ]
    }
    """
    
    try:
        parsed = engine._clean_and_parse_json(malformed_response)
        print(f"   ✅ Parser handled trailing comma: {parsed}")
        assert len(parsed) == 2, f"Expected 2 candidates, got {len(parsed)}"
        return True
    except Exception as e:
        print(f"   ❌ Parser failed on trailing comma: {e}")
        return False


def test_real_generation():
    """Integration test: Generate real candidates from Ollama."""
    print(f"\n🧠 Testing Real LLM Generation with {config.OLLAMA_MODEL}...")
    
    # Uses config defaults for model, url, temperature
    engine = GenerationEngine(
        temperature=0.7  # Override just temperature for consistent test results
    )
    
    # First check connection
    if not engine.test_connection():
        print("⚠️ Skipping real generation test - Ollama not available")
        return None  # Not a failure, just skipped
    
    # Use a simple prompt for testing
    system_prompt = """You are a skilled rap lyricist. Generate lyrics that match exact rhythmic constraints.

Always respond with valid JSON:
{"candidates": ["line 1", "line 2", "line 3", "line 4", "line 5"]}

Generate exactly 5 different line variations. Each line MUST have exactly 5 syllables."""

    user_prompt = """Write a line with exactly **5 syllables**.

## Stress Pattern
DA-da-DA-da-DA

## Response
Generate 5 variations as JSON:
{"candidates": [...]}"""

    try:
        print("   Sending request to Ollama...")
        candidates = engine.generate_candidates(system_prompt, user_prompt)
        
        print(f"\n   📝 Generated {len(candidates)} candidates:")
        for i, candidate in enumerate(candidates, 1):
            print(f"      {i}. \"{candidate}\"")
        
        assert len(candidates) > 0, "Expected at least 1 candidate"
        print("\n✅ Real LLM generation successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Generation failed: {e}")
        return False


def test_json_without_markdown():
    """Test parsing clean JSON without markdown wrappers."""
    print("\n🧪 Testing Clean JSON Parsing...")
    
    engine = GenerationEngine()
    
    clean_response = '{"candidates": ["First line here", "Second line now", "Third one coming"]}'
    
    parsed = engine._clean_and_parse_json(clean_response)
    
    assert len(parsed) == 3, f"Expected 3 candidates, got {len(parsed)}"
    print(f"   Parsed: {parsed}")
    print("✅ Clean JSON parsed correctly.")
    return True


def test_fallback_line_split():
    """Test fallback when JSON parsing completely fails."""
    print("\n🧪 Testing Fallback Line Splitting...")
    
    engine = GenerationEngine()
    
    # Response with no valid JSON at all
    broken_response = """
    Here are some lyrics for you:
    
    Running through the night
    Breaking all the chains
    Never gonna stop now
    
    Let me know if you need more!
    """
    
    parsed = engine._clean_and_parse_json(broken_response)
    
    print(f"   Fallback parsed: {parsed}")
    # Should extract the actual lyric lines, not the filler
    assert len(parsed) > 0, "Expected at least some lines from fallback"
    print("✅ Fallback parsing extracted lines correctly.")
    return True


if __name__ == "__main__":
    print("\n" + "🎤 " + "=" * 56 + " 🎤")
    print("   FLOW-TO-LYRICS: GENERATION ENGINE TEST SUITE")
    print("🎤 " + "=" * 56 + " 🎤")
    
    results = []
    
    # Test 1: Ollama connection
    results.append(("Ollama Connection", test_ollama_connection()))
    
    # Test 2: JSON parsing (dirty output)
    results.append(("Robust JSON Parsing", test_robust_json_parsing()))
    
    # Test 3: Malformed JSON
    results.append(("Malformed JSON Recovery", test_malformed_json_recovery()))
    
    # Test 4: Clean JSON
    results.append(("Clean JSON Parsing", test_json_without_markdown()))
    
    # Test 5: Fallback parsing
    results.append(("Fallback Line Splitting", test_fallback_line_split()))
    
    # Test 6: Real generation (only if Ollama available)
    results.append(("Real LLM Generation", test_real_generation()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for name, result in results:
        if result is True:
            print(f"   ✅ {name}")
            passed += 1
        elif result is False:
            print(f"   ❌ {name}")
            failed += 1
        else:
            print(f"   ⚠️ {name} (Skipped)")
            skipped += 1
    
    print("")
    print(f"   Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    print("=" * 60)
    
    if failed > 0:
        print("⚠️ SOME TESTS FAILED - Check output above")
    else:
        print("🎉 ALL TESTS PASSED!")
    print("")
