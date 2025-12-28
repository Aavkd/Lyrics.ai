"""
Flow-to-Lyrics: New Audio Samples Analysis
==========================================
Tests the syllable detection pipeline on the new user-recorded audio files.

These files are titled by what the user mumbled, so we know exactly what to expect:
- "talk_to_me_i_said_what.m4a"     -> "Talk to me, I said what" = 6 syllables
- "99_problems.m4a"               -> "99 problems" = 5 syllables
- "everybody_equal.m4a"           -> "Everybody equal" = 6 syllables  
- "mumble_on_this_beat.m4a"       -> "Mumble on this beat" = 5 syllables
- "trying_to_take_my_time.m4a"    -> "Trying to take my time" = 6 syllables
- "what_bout_you.m4a"             -> "What 'bout you" = 3 syllables

Run: python tests/test_new_audio_samples.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from audio_engine import (
    LibrosaAnalyzer,
    PivotFormatter,
    PhoneticAnalyzer,
    PivotJSON,
)


# =============================================================================
# EXPECTED SYLLABLE COUNTS (Manual mapping based on file content)
# =============================================================================

EXPECTED_SYLLABLES = {
    "talk_to_me_i_said_what.m4a": {
        "phrase": "Talk to me, I said what",
        "syllables": 6,
        "breakdown": "Talk(1) to(1) me(1) I(1) said(1) what(1)"
    },
    "99_problems.m4a": {
        "phrase": "99 problems", 
        "syllables": 5,
        "breakdown": "Nine(1) ty(1) nine(1) prob(1) lems(1)"
    },
    "everybody_equal.m4a": {
        "phrase": "Everybody equal",
        "syllables": 6,
        "breakdown": "Ev(1) ry(1) bo(1) dy(1) e(1) qual(1)"
    },
    "mumble_on_this_beat.m4a": {
        "phrase": "Mumble on this beat",
        "syllables": 5,
        "breakdown": "Mum(1) ble(1) on(1) this(1) beat(1)"
    },
    "trying_to_take_my_time.m4a": {
        "phrase": "Trying to take my time",
        "syllables": 6,
        "breakdown": "Try(1) ing(1) to(1) take(1) my(1) time(1)"
    },
    "oh_ma_oh_ma_on_my_tec_nine.m4a": {
        "phrase": "Oh ma oh ma on my Tec Nine",
        "syllables": 8,
        "breakdown": "oh(1) ma(1) oh(1) ma(1) on(1) my(1) tec(1) nine(1)"
    },
    "what_bout_you.m4a": {
        "phrase": "What 'bout you",
        "syllables": 3,
        "breakdown": "What(1) 'bout(1) you(1)"
    }
    
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class AnalysisResult:
    """Result of analyzing a single audio file."""
    filename: str
    expected_phrase: str
    expected_syllables: int
    expected_breakdown: str
    detected_syllables: int
    tempo: float
    duration: float
    segments: list[dict]
    error: int
    accuracy_percent: float


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def analyze_audio_file(filepath: Path, phonetic_enabled: bool = False) -> dict:
    """
    Analyze a single audio file using the audio engine pipeline.
    
    Args:
        filepath: Path to audio file.
        phonetic_enabled: Whether to enable phonetic (IPA) analysis.
        
    Returns:
        Dictionary with analysis results.
    """
    # Initialize components
    analyzer = LibrosaAnalyzer()
    phonetic_analyzer = PhoneticAnalyzer(enabled=phonetic_enabled)
    formatter = PivotFormatter(phonetic_analyzer=phonetic_analyzer)
    
    # Run analysis
    analysis = analyzer.analyze(str(filepath))
    
    # Format to PivotJSON (format() takes an AnalysisResult object)
    pivot = formatter.format(analysis)
    
    return {
        "pivot": pivot,
        "tempo": analysis.tempo,
        "duration": analysis.duration,
        "onset_times": analysis.onset_times
    }


def run_analysis(verbose: bool = True, phonetic_enabled: bool = False) -> list[AnalysisResult]:
    """
    Run analysis on all new audio samples.
    
    Args:
        verbose: If True, print detailed output.
        phonetic_enabled: Whether to run phonetic analysis.
        
    Returns:
        List of AnalysisResult objects.
    """
    print("\n" + "=" * 75)
    print("  🎵 NEW AUDIO SAMPLES ANALYSIS")
    print("  Testing Syllable Detection Pipeline (No LLM)")
    print("=" * 75)
    
    # Find audio samples directory
    project_root = Path(__file__).parent.parent
    samples_dir = project_root / "audio samples"
    
    if not samples_dir.exists():
        raise FileNotFoundError(f"Audio samples directory not found: {samples_dir}")
    
    results = []
    
    # Process each expected file
    for filename, expected_data in EXPECTED_SYLLABLES.items():
        filepath = samples_dir / filename
        
        if not filepath.exists():
            print(f"\n⚠️  File not found: {filename}")
            continue
        
        if verbose:
            print(f"\n{'─' * 75}")
            print(f"📄 Analyzing: {filename}")
            print(f"   Expected: \"{expected_data['phrase']}\"")
            print(f"   Syllables: {expected_data['syllables']} ({expected_data['breakdown']})")
        
        try:
            analysis = analyze_audio_file(filepath, phonetic_enabled=phonetic_enabled)
            pivot = analysis["pivot"]
            
            # Get detected syllable count from segments
            if pivot.blocks and len(pivot.blocks) > 0:
                detected = len(pivot.blocks[0].segments)
                segments = [
                    {
                        "time_start": round(seg.time_start, 3),
                        "duration": round(seg.duration, 3),
                        "is_stressed": seg.is_stressed,
                        "is_sustained": seg.is_sustained,
                        "pitch_contour": seg.pitch_contour,
                        "audio_phonemes": seg.audio_phonemes
                    }
                    for seg in pivot.blocks[0].segments
                ]
            else:
                detected = 0
                segments = []
            
            error = detected - expected_data["syllables"]
            accuracy = max(0, 1 - abs(error) / expected_data["syllables"]) * 100
            
            result = AnalysisResult(
                filename=filename,
                expected_phrase=expected_data["phrase"],
                expected_syllables=expected_data["syllables"],
                expected_breakdown=expected_data["breakdown"],
                detected_syllables=detected,
                tempo=round(analysis["tempo"], 2),
                duration=round(analysis["duration"], 3),
                segments=segments,
                error=error,
                accuracy_percent=round(accuracy, 1)
            )
            results.append(result)
            
            # Print result
            status = "✅" if error == 0 else "⚠️" if abs(error) <= 1 else "❌"
            error_str = f"+{error}" if error > 0 else str(error)
            
            if verbose:
                print(f"   Result: {detected} syllables detected (error: {error_str}) {status}")
                print(f"   Tempo: {result.tempo} BPM | Duration: {result.duration}s")
                
                if segments:
                    print(f"\n   Segments:")
                    for i, seg in enumerate(segments, 1):
                        stress = "🔊" if seg["is_stressed"] else "  "
                        sustain = "⏸" if seg["is_sustained"] else " "
                        ipa = f" [{seg['audio_phonemes']}]" if seg["audio_phonemes"] else ""
                        print(f"      {i:2}. {stress}{sustain} {seg['time_start']:5.3f}s - {seg['duration']:.3f}s  {seg['pitch_contour']:<7}{ipa}")
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Print summary
    if results:
        print_summary(results)
    
    return results


def print_summary(results: list[AnalysisResult]):
    """Print a summary table of all results."""
    print("\n" + "=" * 75)
    print("  📊 SUMMARY")
    print("=" * 75)
    
    # Calculate totals
    total_expected = sum(r.expected_syllables for r in results)
    total_detected = sum(r.detected_syllables for r in results)
    total_error = sum(abs(r.error) for r in results)
    perfect_matches = sum(1 for r in results if r.error == 0)
    close_matches = sum(1 for r in results if abs(r.error) <= 1)
    
    # Print table header
    print(f"\n┌{'─' * 35}┬{'─' * 10}┬{'─' * 10}┬{'─' * 8}┬{'─' * 8}┐")
    print(f"│ {'File':<33} │ {'Expected':>8} │ {'Detected':>8} │ {'Error':>6} │ {'Status':>6} │")
    print(f"├{'─' * 35}┼{'─' * 10}┼{'─' * 10}┼{'─' * 8}┼{'─' * 8}┤")
    
    for r in results:
        status = "✅" if r.error == 0 else "⚠️" if abs(r.error) <= 1 else "❌"
        error_str = f"+{r.error}" if r.error > 0 else str(r.error)
        # Truncate filename if too long
        fname = r.filename[:31] + "..." if len(r.filename) > 33 else r.filename
        print(f"│ {fname:<33} │ {r.expected_syllables:>8} │ {r.detected_syllables:>8} │ {error_str:>6} │ {status:>6} │")
    
    print(f"├{'─' * 35}┼{'─' * 10}┼{'─' * 10}┼{'─' * 8}┼{'─' * 8}┤")
    print(f"│ {'TOTAL':>33} │ {total_expected:>8} │ {total_detected:>8} │ {total_error:>6} │        │")
    print(f"└{'─' * 35}┴{'─' * 10}┴{'─' * 10}┴{'─' * 8}┴{'─' * 8}┘")
    
    # Print stats
    print(f"\n📈 Statistics:")
    print(f"   • Perfect matches (error = 0): {perfect_matches}/{len(results)}")
    print(f"   • Acceptable matches (|error| ≤ 1): {close_matches}/{len(results)}")
    print(f"   • Total absolute error: {total_error}")
    print(f"   • Average error per file: {total_error / len(results):.2f}")


def generate_report(results: list[AnalysisResult]) -> str:
    """
    Generate a Markdown report of the analysis.
    
    Args:
        results: List of AnalysisResult objects.
        
    Returns:
        Markdown string.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    md = f"""# 🎵 Audio Pipeline Test Report

**Generated:** {timestamp}  
**Test Type:** Syllable Detection Analysis (No LLM)  
**Phoneme Analysis:** Disabled (testing audio/syllable pipeline only)

---

## 📋 Test Summary

| Metric | Value |
|--------|-------|
| Files Tested | {len(results)} |
| Perfect Matches | {sum(1 for r in results if r.error == 0)}/{len(results)} |
| Close Matches (±1) | {sum(1 for r in results if abs(r.error) <= 1)}/{len(results)} |
| Total Expected Syllables | {sum(r.expected_syllables for r in results)} |
| Total Detected Syllables | {sum(r.detected_syllables for r in results)} |
| Total Absolute Error | {sum(abs(r.error) for r in results)} |

---

## 📊 Results by File

"""
    
    for r in results:
        status = "✅ PASS" if r.error == 0 else "⚠️ CLOSE" if abs(r.error) <= 1 else "❌ FAIL"
        error_str = f"+{r.error}" if r.error > 0 else str(r.error)
        
        md += f"""### {r.filename}

**Status:** {status}

| Property | Value |
|----------|-------|
| Expected Phrase | "{r.expected_phrase}" |
| Syllable Breakdown | {r.expected_breakdown} |
| Expected Syllables | {r.expected_syllables} |
| Detected Syllables | {r.detected_syllables} |
| Error | {error_str} |
| Tempo | {r.tempo} BPM |
| Duration | {r.duration}s |

"""
        
        if r.segments:
            md += "**Detected Segments:**\n\n"
            md += "| # | Start (s) | Duration (s) | Stressed | Sustained | Pitch |\n"
            md += "|---|-----------|--------------|----------|-----------|-------|\n"
            
            for i, seg in enumerate(r.segments, 1):
                stressed = "🔊" if seg["is_stressed"] else ""
                sustained = "⏸" if seg["is_sustained"] else ""
                md += f"| {i} | {seg['time_start']:.3f} | {seg['duration']:.3f} | {stressed} | {sustained} | {seg['pitch_contour']} |\n"
            
            md += "\n"
        
        md += "---\n\n"
    
    # Add analysis section
    md += """## 🔍 Analysis

### Observations

"""
    
    # Identify patterns
    under_detected = [r for r in results if r.error < 0]
    over_detected = [r for r in results if r.error > 0]
    perfect = [r for r in results if r.error == 0]
    
    if perfect:
        md += f"- **Perfect Detection ({len(perfect)} files):** "
        md += ", ".join(f"`{r.filename}`" for r in perfect) + "\n"
    
    if under_detected:
        md += f"- **Under-Detection ({len(under_detected)} files):** "
        md += ", ".join(f"`{r.filename}` (expected {r.expected_syllables}, got {r.detected_syllables})" for r in under_detected) + "\n"
    
    if over_detected:
        md += f"- **Over-Detection ({len(over_detected)} files):** "
        md += ", ".join(f"`{r.filename}` (expected {r.expected_syllables}, got {r.detected_syllables})" for r in over_detected) + "\n"

    md += """
### Potential Issues

"""
    
    # Check for long segments (potential under-detection)
    files_with_long_segments = []
    for r in results:
        long_segs = [s for s in r.segments if s["duration"] > 0.5]
        if long_segs:
            files_with_long_segments.append((r.filename, len(long_segs), max(s["duration"] for s in long_segs)))
    
    if files_with_long_segments:
        md += "**Long Segments Detected (may indicate missed syllables):**\n\n"
        for fname, count, max_dur in files_with_long_segments:
            md += f"- `{fname}`: {count} segment(s) > 0.5s (max: {max_dur:.3f}s)\n"
        md += "\n"
    
    md += """
### Recommendations

Based on this analysis:

1. **If under-detection is observed:** Consider lowering `ONSET_DELTA` in `.env` for higher sensitivity
2. **If over-detection is observed:** Consider raising `ONSET_DELTA` or enabling breath filtering
3. **Long segments:** May need `MAX_SEGMENT_DURATION` adjustment for auto-splitting

---

*Report generated by `tests/test_new_audio_samples.py`*
"""
    
    return md


def save_report(results: list[AnalysisResult], output_path: Path = None):
    """
    Save the analysis report to a Markdown file.
    
    Args:
        results: List of AnalysisResult objects.
        output_path: Optional output path. Defaults to docs/AUDIO_PIPELINE_TEST_REPORT.md
    """
    if output_path is None:
        project_root = Path(__file__).parent.parent
        output_path = project_root / "docs" / "AUDIO_PIPELINE_TEST_REPORT.md"
    
    report = generate_report(results)
    output_path.write_text(report, encoding="utf-8")
    print(f"\n📝 Report saved to: {output_path}")


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Parse arguments
    verbose = "--quiet" not in sys.argv
    phonetic = "--phonetic" in sys.argv
    save = "--save" in sys.argv or True  # Always save by default
    
    print("Running with phonetic analysis:", "Enabled" if phonetic else "Disabled")
    
    results = run_analysis(verbose=verbose, phonetic_enabled=phonetic)
    
    if results and save:
        save_report(results)
    
    print("\n" + "=" * 75 + "\n")
