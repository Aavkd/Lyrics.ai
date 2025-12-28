"""
Flow-to-Lyrics: Pipeline Inspector
===================================
Debug tool to inspect the audio analysis and prompt generation pipeline.

This script runs the pipeline up to the LLM step and displays:
1. Audio analysis results (tempo, duration, onsets)
2. Segment details (stress, sustain, pitch, IPA phonemes)
3. Full generated prompts (system + user)

Usage:
    python tests/test_pipeline_inspector.py <audio_file>
    python tests/test_pipeline_inspector.py audio_samples/3_syllabes_test.mp3
    
The script will NOT call the LLM - it stops before generation to let you
inspect the inputs that would be sent.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from audio_engine import AudioEngine, PivotJSON
from prompt_engine import PromptEngine


def print_header(title: str, width: int = 70):
    """Print a formatted header."""
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def print_section(title: str, width: int = 70):
    """Print a formatted section header."""
    print(f"\n{title}")
    print("-" * width)


def inspect_pipeline(audio_path: str, phonetic_enabled: bool = True):
    """
    Run the pipeline and inspect all intermediate outputs.
    
    Args:
        audio_path: Path to the audio file to analyze.
        phonetic_enabled: Whether to enable Allosaurus phonetic analysis.
    """
    print_header("🎵 FLOW-TO-LYRICS: PIPELINE INSPECTOR")
    print(f"\n  Audio File: {audio_path}")
    print(f"  Phonetic Analysis: {'ENABLED' if phonetic_enabled else 'DISABLED'}")
    
    # Check file exists
    if not Path(audio_path).exists():
        print(f"\n❌ ERROR: File not found: {audio_path}")
        return False
    
    # ==========================================================================
    # STEP 1: Audio Analysis
    # ==========================================================================
    print_section("📊 STEP 1: Audio Analysis")
    
    engine = AudioEngine(mock_mode=True, phonetic_enabled=phonetic_enabled)
    
    try:
        pivot = engine.process(audio_path)
    except Exception as e:
        print(f"❌ ERROR during audio analysis: {e}")
        return False
    
    # Display audio metadata
    print(f"\n  📈 Audio Metadata:")
    print(f"     • Tempo: {pivot.tempo:.1f} BPM")
    print(f"     • Duration: {pivot.duration:.2f} seconds")
    print(f"     • Blocks: {len(pivot.blocks)}")
    
    # ==========================================================================
    # STEP 2: Segment Details
    # ==========================================================================
    print_section("🎯 STEP 2: Segment Details")
    
    for block in pivot.blocks:
        print(f"\n  📦 Block {block.id}: {block.syllable_target} syllables")
        print()
        
        # Create table header
        print(f"  {'#':<3} {'Time':>7} {'Dur':>6} {'Stress':>8} {'Sustain':>8} {'Pitch':>8} {'IPA Phonemes':<20}")
        print(f"  {'-'*3} {'-'*7} {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*20}")
        
        for i, seg in enumerate(block.segments, 1):
            stress_str = "DA" if seg.is_stressed else "da"
            sustain_str = "LONG" if seg.is_sustained else "-"
            phonemes = seg.audio_phonemes if seg.audio_phonemes else "(none)"
            
            print(f"  {i:<3} {seg.time_start:>7.3f} {seg.duration:>6.3f} {stress_str:>8} {sustain_str:>8} {seg.pitch_contour:>8} {phonemes:<20}")
        
        # Build stress pattern
        stress_pattern = "-".join(["DA" if s.is_stressed else "da" for s in block.segments])
        print(f"\n  🥁 Stress Pattern: {stress_pattern}")
        
        # Show IPA summary
        all_phonemes = [s.audio_phonemes for s in block.segments if s.audio_phonemes]
        if all_phonemes:
            print(f"  🔤 Combined IPA: {' | '.join(all_phonemes)}")
        else:
            print(f"  🔤 Combined IPA: (no phonemes detected)")
    
    # ==========================================================================
    # STEP 3: Pivot JSON (Raw Output)
    # ==========================================================================
    print_section("📋 STEP 3: Pivot JSON (Raw)")
    
    pivot_dict = pivot.to_dict()
    print(json.dumps(pivot_dict, indent=2, ensure_ascii=False))
    
    # ==========================================================================
    # STEP 4: Prompt Generation
    # ==========================================================================
    print_section("📝 STEP 4: Prompt Generation")
    
    try:
        prompt_engine = PromptEngine(template_dir="prompts")
        system_prompt, user_prompt = prompt_engine.construct_prompt(pivot)
    except Exception as e:
        print(f"❌ ERROR during prompt generation: {e}")
        return False
    
    print(f"\n  💬 System Prompt ({len(system_prompt)} chars):")
    print(f"  " + "-" * 60)
    # Show first 500 chars
    if len(system_prompt) > 500:
        print(f"  {system_prompt[:500]}...")
        print(f"  [Truncated - {len(system_prompt) - 500} more chars]")
    else:
        print(f"  {system_prompt}")
    
    print(f"\n  👤 User Prompt ({len(user_prompt)} chars):")
    print(f"  " + "-" * 60)
    print(user_prompt)
    
    # ==========================================================================
    # STEP 5: Summary
    # ==========================================================================
    print_header("📊 PIPELINE INSPECTION COMPLETE")
    
    print(f"""
  ✅ Audio analyzed: {audio_path}
  ✅ Tempo: {pivot.tempo:.1f} BPM
  ✅ Duration: {pivot.duration:.2f}s
  ✅ Syllables detected: {pivot.blocks[0].syllable_target if pivot.blocks else 0}
  ✅ Phonemes extracted: {sum(1 for s in pivot.blocks[0].segments if s.audio_phonemes) if pivot.blocks else 0} / {len(pivot.blocks[0].segments) if pivot.blocks else 0} segments
  
  📌 The prompts above would be sent to the LLM.
  📌 Review the segment table to verify:
     • Syllable count matches expected
     • Stress pattern (DA/da) is reasonable
     • IPA phonemes capture the main sounds
""")
    
    return True


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("""
Flow-to-Lyrics: Pipeline Inspector
===================================

Usage:
    python tests/test_pipeline_inspector.py <audio_file> [--no-phonetic]

Examples:
    python tests/test_pipeline_inspector.py test_audio_real.mp3
    python tests/test_pipeline_inspector.py "audio samples/3_syllabes_test.mp3"
    python tests/test_pipeline_inspector.py test_audio_real.mp3 --no-phonetic

Arguments:
    audio_file     Path to the audio file to analyze
    --no-phonetic  Disable Allosaurus phonetic analysis (faster)
""")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    phonetic_enabled = "--no-phonetic" not in sys.argv
    
    success = inspect_pipeline(audio_path, phonetic_enabled)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
