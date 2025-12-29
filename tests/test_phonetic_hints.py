"""
Flow-to-Lyrics: Phonetic Hints Test
====================================
Tests the phonetic analysis pipeline on audio files to output "sound-alike" hints
for each detected syllable.

This allows comparison of detected phonemes against the expected mumbles.

Run: python tests/test_phonetic_hints.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from audio_engine import (
    LibrosaAnalyzer,
    PivotFormatter,
    PhoneticAnalyzer,
    get_whisper_analyzer,
)


# =============================================================================
# EXPECTED SYLLABLES (for comparison)
# =============================================================================

EXPECTED_SYLLABLES = {
    "talk_to_me_i_said_what.m4a": {
        "phrase": "Talk to me, I said what",
        "syllables": ["Talk", "to", "me", "I", "said", "what"],
    },
    "99_problems.m4a": {
        "phrase": "99 problems", 
        "syllables": ["Nine", "ty", "nine", "prob", "lems"],
    },
    "everybody_equal.m4a": {
        "phrase": "Everybody equal",
        "syllables": ["Ev", "ry", "bo", "dy", "e", "qual"],
    },
    "mumble_on_this_beat.m4a": {
        "phrase": "Mumble on this beat",
        "syllables": ["Mum", "ble", "on", "this", "beat"],
    },
    "trying_to_take_my_time.m4a": {
        "phrase": "Trying to take my time",
        "syllables": ["Try", "ing", "to", "take", "my", "time"],
    },
    "oh_ma_oh_ma_on_my_tec_nine.m4a": {
        "phrase": "Oh ma oh ma on my Tec Nine",
        "syllables": ["oh", "ma", "oh", "ma", "on", "my", "tec", "nine"],
    },
    "what_bout_you.m4a": {
        "phrase": "What 'bout you",
        "syllables": ["What", "'bout", "you"],
    }
}


# =============================================================================
# PHONETIC ANALYSIS
# =============================================================================

def analyze_phonetics(filepath: Path) -> dict:
    """
    Analyze a single audio file and extract phonetic hints for each segment.
    
    Args:
        filepath: Path to audio file.
        
    Returns:
        Dictionary with segments and their phonetic hints.
    """
    # Initialize components
    analyzer = LibrosaAnalyzer()
    phonetic_analyzer = PhoneticAnalyzer(enabled=True)  # Enable phonetics
    formatter = PivotFormatter(phonetic_analyzer=phonetic_analyzer)
    
    # Run analysis
    analysis = analyzer.analyze(str(filepath))
    
    # Format to PivotJSON (includes phonetic analysis via full-audio Whisper)
    pivot = formatter.format(analysis)
    
    # Extract segments with phonemes
    segments_with_phonemes = []
    if pivot.blocks:
        for segment in pivot.blocks[0].segments:
            segments_with_phonemes.append({
                "time_start": segment.time_start,
                "duration": segment.duration,
                "phonemes": segment.audio_phonemes if hasattr(segment, 'audio_phonemes') else "",
            })
    
    return {
        "segments": segments_with_phonemes,
        "tempo": pivot.meta.tempo,
        "duration": pivot.meta.duration,
    }


def get_whisper_syllables(filepath: Path) -> list[dict]:
    """
    Use Whisper to transcribe and get syllable-level phonemes using g2p_en.
    
    This gives more accurate "sound-alike" hints by using full-audio context.
    """
    import librosa
    
    # Load audio
    y, sr = librosa.load(str(filepath), sr=22050)
    
    # Get Whisper transcription
    whisper = get_whisper_analyzer()
    words = whisper.transcribe_full_audio(y, sr)
    
    if not words:
        return []
    
    # Get syllable-level phonemes
    syllables = whisper._words_to_syllables_with_timing(words)
    
    return syllables


def run_phonetic_analysis():
    """
    Run phonetic analysis on all audio files and print sound-alike hints.
    """
    print("\n" + "=" * 75)
    print("  🔊 PHONETIC HINTS ANALYSIS")
    print("  Comparing detected sounds to expected mumbles")
    print("=" * 75)
    
    # Find audio samples directory
    project_root = Path(__file__).parent.parent
    samples_dir = project_root / "audio samples"
    
    if not samples_dir.exists():
        print(f"❌ Error: Audio samples directory not found: {samples_dir}")
        return
    
    # Process each expected file
    for filename, expected in EXPECTED_SYLLABLES.items():
        filepath = samples_dir / filename
        
        if not filepath.exists():
            print(f"\n⚠️ File not found: {filename}")
            continue
        
        print(f"\n{'─' * 75}")
        print(f"📄 {filename}")
        print(f"   Expected: \"{expected['phrase']}\"")
        print(f"   Syllables: {' | '.join(expected['syllables'])}")
        print()
        
        try:
            # Get Whisper-based syllable phonemes
            syllables = get_whisper_syllables(filepath)
            
            if syllables:
                print("   ## Phonetic Hints (Sound-Alike)")
                for i, syl in enumerate(syllables, 1):
                    phonemes = syl.get("phonemes", "")
                    word = syl.get("word", "")
                    
                    # Compare with expected if available
                    expected_syl = ""
                    if i <= len(expected['syllables']):
                        expected_syl = expected['syllables'][i - 1]
                    
                    print(f"   - Syllable {i} sounds like: **/{phonemes}/** ", end="")
                    if expected_syl:
                        print(f"(expected: \"{expected_syl}\")")
                    else:
                        print("(extra)")
                
                # Check for missing syllables
                if len(syllables) < len(expected['syllables']):
                    print(f"\n   ⚠️ Missing {len(expected['syllables']) - len(syllables)} syllable(s)")
                elif len(syllables) > len(expected['syllables']):
                    print(f"\n   ⚠️ {len(syllables) - len(expected['syllables'])} extra syllable(s) detected")
                else:
                    print(f"\n   ✅ Syllable count matches: {len(syllables)}/{len(expected['syllables'])}")
            else:
                print("   ❌ No phonemes detected (Whisper transcription failed)")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 75)
    print("  Analysis complete!")
    print("=" * 75 + "\n")


# =============================================================================
# DETAILED COMPARISON OUTPUT
# =============================================================================

def generate_comparison_report():
    """
    Generate a detailed markdown report comparing detected vs expected phonemes.
    """
    print("\n" + "=" * 75)
    print("  📝 GENERATING PHONETIC COMPARISON REPORT")
    print("=" * 75)
    
    project_root = Path(__file__).parent.parent
    samples_dir = project_root / "audio samples"
    report_path = project_root / "docs" / "PHONETIC_HINTS_REPORT.md"
    
    lines = [
        "# 🔊 Phonetic Hints Report",
        "",
        f"**Generated:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "This report compares detected phonemes against expected syllables for each audio file.",
        "",
        "---",
        "",
    ]
    
    for filename, expected in EXPECTED_SYLLABLES.items():
        filepath = samples_dir / filename
        
        if not filepath.exists():
            continue
        
        lines.append(f"## {filename}")
        lines.append("")
        lines.append(f"**Expected:** \"{expected['phrase']}\"")
        lines.append("")
        lines.append("| # | Expected | Detected Phonemes |")
        lines.append("|---|----------|-------------------|")
        
        try:
            syllables = get_whisper_syllables(filepath)
            
            max_len = max(len(expected['syllables']), len(syllables))
            
            for i in range(max_len):
                exp_syl = expected['syllables'][i] if i < len(expected['syllables']) else "—"
                det_phon = syllables[i].get("phonemes", "—") if i < len(syllables) else "—"
                
                lines.append(f"| {i+1} | {exp_syl} | /{det_phon}/ |")
            
            # Summary
            if len(syllables) == len(expected['syllables']):
                lines.append(f"\n✅ **Match:** {len(syllables)}/{len(expected['syllables'])} syllables")
            else:
                diff = len(syllables) - len(expected['syllables'])
                if diff > 0:
                    lines.append(f"\n⚠️ **Over-detection:** +{diff} syllables")
                else:
                    lines.append(f"\n⚠️ **Under-detection:** {diff} syllables")
                    
        except Exception as e:
            lines.append(f"\n❌ Error: {e}")
        
        lines.append("")
        lines.append("---")
        lines.append("")
    
    # Write report
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"\n📝 Report saved to: {report_path}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phonetic Hints Analysis")
    parser.add_argument("--report", action="store_true", help="Generate markdown report")
    args = parser.parse_args()
    
    if args.report:
        generate_comparison_report()
    else:
        run_phonetic_analysis()
