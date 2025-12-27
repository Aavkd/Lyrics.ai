"""
Flow-to-Lyrics: Prompt Engine Test
===================================
Verifies that the PromptEngine correctly loads templates and generates
prompts from PivotJSON data.

Test Strategy:
1. Create a dummy PivotJSON with a specific "trap" flow pattern
2. Run the PromptEngine
3. Print the full System and User prompts for inspection
4. Assert key elements are present in the generated prompts
"""

import sys
import os

# Add parent dir to path to import engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prompt_engine import PromptEngine
from audio_engine import PivotJSON, Block, Segment


def create_dummy_pivot() -> PivotJSON:
    """
    Creates a PivotJSON with a specific 'trap' flow: DA-da-DA-da-DA
    
    Pattern breakdown:
    - Syllable 1: Stressed (DA) - Strong beat
    - Syllable 2: Unstressed (da) - Weak beat
    - Syllable 3: Stressed (DA) - Strong beat
    - Syllable 4: Unstressed (da) - Weak beat
    - Syllable 5: Stressed (DA) + Sustained - Long final note
    
    This simulates a typical trap/hip-hop rhythmic pattern where
    the final syllable is held with an open vowel.
    """
    segments = [
        Segment(0.0, 0.2, is_stressed=True, is_sustained=False),   # DA
        Segment(0.2, 0.2, is_stressed=False, is_sustained=False),  # da
        Segment(0.4, 0.2, is_stressed=True, is_sustained=False),   # DA
        Segment(0.6, 0.2, is_stressed=False, is_sustained=False),  # da
        Segment(0.8, 0.6, is_stressed=True, is_sustained=True),    # DAAAA (Sustained)
    ]
    
    block = Block(
        id=1,
        syllable_target=5,
        segments=segments
    )
    
    return PivotJSON(tempo=140.0, duration=1.5, blocks=[block])


def test_prompt_generation():
    """Main test function for the Prompt Engine."""
    
    print("🏗️ Testing Prompt Engine for Ministral-3b...")
    print("=" * 60)
    
    # Initialize Engine
    try:
        engine = PromptEngine(template_dir="prompts")
        print("✅ Templates loaded successfully from /prompts folder")
    except FileNotFoundError as e:
        print(f"\n❌ FAIL: Could not find prompt templates.")
        print(f"   Error: {e}")
        return False
    
    # Load Data
    data = create_dummy_pivot()
    print(f"\n📊 Test Data:")
    print(f"   Tempo: {data.tempo} BPM")
    print(f"   Duration: {data.duration}s")
    print(f"   Blocks: {len(data.blocks)}")
    print(f"   Syllables: {data.blocks[0].syllable_target}")
    
    # Generate Prompts
    try:
        system_msg, user_msg = engine.construct_prompt(data)
        
        print("\n" + "=" * 60)
        print("📜 SYSTEM PROMPT (Loaded from .md):")
        print("=" * 60)
        print(system_msg)
        
        print("\n" + "=" * 60)
        print("👤 USER PROMPT (Filled Template):")
        print("=" * 60)
        print(user_msg)
        
        # Validation Checks
        print("\n" + "=" * 60)
        print("🔍 VALIDATION CHECKS:")
        print("=" * 60)
        
        errors = []
        
        # Check 1: Stress pattern present
        if "DA-da-DA-da-DA" in user_msg or "1-0-1-0-1" in user_msg:
            print("✅ Stress pattern present in user prompt")
        else:
            errors.append("Stress pattern missing from user prompt")
            print("❌ Stress pattern missing")
        
        # Check 2: Sustain constraint present
        if "sustained" in user_msg.lower():
            print("✅ Sustain constraint mentioned")
        else:
            errors.append("Sustain constraint missing")
            print("❌ Sustain constraint missing")
        
        # Check 3: Syllable count present
        if "5 syllables" in user_msg:
            print("✅ Syllable count specified (5 syllables)")
        else:
            errors.append("Syllable count missing")
            print("❌ Syllable count missing")
        
        # Check 4: JSON format in system prompt
        if '{"candidates":' in system_msg or '"candidates"' in system_msg:
            print("✅ JSON output format specified in system prompt")
        else:
            errors.append("JSON format missing from system prompt")
            print("❌ JSON format missing from system prompt")
        
        # Check 5: Few-shot examples present
        if "Example" in system_msg:
            print("✅ Few-shot examples present in system prompt")
        else:
            errors.append("Few-shot examples missing")
            print("❌ Few-shot examples missing")
        
        print("\n" + "=" * 60)
        
        if errors:
            print(f"❌ FAIL: {len(errors)} validation errors:")
            for error in errors:
                print(f"   - {error}")
            return False
        else:
            print("✅ SUCCESS: Prompt constructed correctly with external templates.")
            return True
        
    except Exception as e:
        print(f"\n❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_stress_pattern_conversion():
    """Test the stress pattern conversion logic."""
    
    print("\n" + "=" * 60)
    print("🔄 Testing Stress Pattern Conversion:")
    print("=" * 60)
    
    engine = PromptEngine(template_dir="prompts")
    
    test_cases = [
        ([True, False, True], "DA-da-DA"),
        ([False, True, False, True], "da-DA-da-DA"),
        ([True, True, True], "DA-DA-DA"),
        ([False, False, False], "da-da-da"),
        ([], ""),
    ]
    
    all_passed = True
    for stressed_flags, expected in test_cases:
        result = engine._convert_stress_to_pattern(stressed_flags)
        status = "✅" if result == expected else "❌"
        print(f"   {status} {stressed_flags} -> '{result}' (expected: '{expected}')")
        if result != expected:
            all_passed = False
    
    return all_passed


def test_sustain_constraint_generation():
    """Test the sustain constraint generation logic."""
    
    print("\n" + "=" * 60)
    print("📝 Testing Sustain Constraint Generation:")
    print("=" * 60)
    
    engine = PromptEngine(template_dir="prompts")
    
    # Create segments with different sustain patterns
    segments_with_sustain = [
        Segment(0.0, 0.2, is_stressed=True, is_sustained=False),
        Segment(0.2, 0.2, is_stressed=False, is_sustained=False),
        Segment(0.4, 0.6, is_stressed=True, is_sustained=True),  # Sustained at index 2 (syllable 3)
    ]
    
    segments_no_sustain = [
        Segment(0.0, 0.2, is_stressed=True, is_sustained=False),
        Segment(0.2, 0.2, is_stressed=False, is_sustained=False),
    ]
    
    segments_multiple_sustain = [
        Segment(0.0, 0.5, is_stressed=True, is_sustained=True),   # Sustained (syllable 1)
        Segment(0.5, 0.2, is_stressed=False, is_sustained=False),
        Segment(0.7, 0.6, is_stressed=True, is_sustained=True),   # Sustained (syllable 3)
    ]
    
    # Test with sustain
    result1 = engine._generate_sustain_constraints(segments_with_sustain)
    print(f"   With sustain at syllable 3:")
    print(f"   -> '{result1}'")
    assert "Syllable 3" in result1, "Should mention syllable 3"
    print("   ✅ Correct")
    
    # Test without sustain
    result2 = engine._generate_sustain_constraints(segments_no_sustain)
    print(f"\n   Without sustain:")
    print(f"   -> '{result2}'")
    assert "No sustained" in result2, "Should say no sustained notes"
    print("   ✅ Correct")
    
    # Test multiple sustains
    result3 = engine._generate_sustain_constraints(segments_multiple_sustain)
    print(f"\n   Multiple sustains (syllables 1 and 3):")
    print(f"   -> '{result3}'")
    assert "Syllable 1" in result3 and "Syllable 3" in result3, "Should mention both"
    print("   ✅ Correct")
    
    return True


if __name__ == "__main__":
    print("\n" + "🎤 " + "=" * 56 + " 🎤")
    print("   FLOW-TO-LYRICS: PROMPT ENGINE TEST SUITE")
    print("🎤 " + "=" * 56 + " 🎤\n")
    
    all_passed = True
    
    # Run all tests
    if not test_prompt_generation():
        all_passed = False
    
    if not test_stress_pattern_conversion():
        all_passed = False
    
    if not test_sustain_constraint_generation():
        all_passed = False
    
    # Final summary
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️ SOME TESTS FAILED - Check output above")
    print("=" * 60 + "\n")
