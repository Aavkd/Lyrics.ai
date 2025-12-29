"""
Flow-to-Lyrics: Audio Samples LLM Generation Test
==================================================
Runs the full LLM pipeline on all test audio samples to generate lyric candidates.

This test:
1. Analyzes each audio file for syllables, stress, and pitch
2. Generates prompts from the analysis
3. Calls the LLM to generate 5 lyric candidates
4. Validates and scores each candidate
5. Selects the best match

Run: python tests/test_audio_llm_generation.py
     python tests/test_audio_llm_generation.py --report  # Generate markdown report
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from audio_engine import AudioEngine
from core_pipeline import CorePipeline
from generation_engine import GenerationEngine
from prompt_engine import PromptEngine
from validator import LyricValidator


# =============================================================================
# EXPECTED AUDIO SAMPLES
# =============================================================================

AUDIO_SAMPLES = {
    "talk_to_me_i_said_what.m4a": {
        "phrase": "Talk to me, I said what",
        "syllables": 6,
        "breakdown": "Talk | to | me | I | said | what",
    },
    "99_problems.m4a": {
        "phrase": "99 problems", 
        "syllables": 5,
        "breakdown": "Nine | ty | nine | prob | lems",
    },
    "everybody_equal.m4a": {
        "phrase": "Everybody equal",
        "syllables": 6,
        "breakdown": "Ev | ry | bo | dy | e | qual",
    },
    "mumble_on_this_beat.m4a": {
        "phrase": "Mumble on this beat",
        "syllables": 5,
        "breakdown": "Mum | ble | on | this | beat",
    },
    "trying_to_take_my_time.m4a": {
        "phrase": "Trying to take my time",
        "syllables": 6,
        "breakdown": "Try | ing | to | take | my | time",
    },
    "oh_ma_oh_ma_on_my_tec_nine.m4a": {
        "phrase": "Oh ma oh ma on my Tec Nine",
        "syllables": 8,
        "breakdown": "oh | ma | oh | ma | on | my | tec | nine",
    },
    "what_bout_you.m4a": {
        "phrase": "What 'bout you",
        "syllables": 3,
        "breakdown": "What | 'bout | you",
    }
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class GenerationResult:
    """Result of generating lyrics for a single audio file."""
    filename: str
    expected_phrase: str
    expected_syllables: int
    detected_syllables: int
    candidates: list[str]
    best_lyric: str | None
    best_score: float
    all_scores: list[tuple[str, float, bool]]  # (candidate, score, valid)
    phonetic_hints: list[str]
    tempo: float
    duration: float


# =============================================================================
# LLM GENERATION
# =============================================================================

def generate_for_file(filepath: Path, pipeline: CorePipeline) -> GenerationResult | None:
    """
    Run full LLM generation pipeline on a single audio file.
    
    Returns:
        GenerationResult with all candidates and scores.
    """
    filename = filepath.name
    expected = AUDIO_SAMPLES.get(filename, {})
    
    try:
        # Use the full pipeline with multi-candidate exposure
        result = pipeline.run_full_pipeline(str(filepath))
        
        if result is None:
            print(f"   ❌ Pipeline returned None for {filename}")
            return None
        
        # Get phonetic hints from pivot
        phonetic_hints = []
        if result.pivot_json and result.pivot_json.blocks:
            for segment in result.pivot_json.blocks[0].segments:
                if hasattr(segment, 'audio_phonemes') and segment.audio_phonemes:
                    phonetic_hints.append(segment.audio_phonemes)
                else:
                    phonetic_hints.append("—")
        
        # Get all validation results
        all_scores = []
        for candidate, validation in zip(result.candidates, result.validations):
            all_scores.append((candidate, validation.score, validation.is_valid))
        
        return GenerationResult(
            filename=filename,
            expected_phrase=expected.get("phrase", ""),
            expected_syllables=expected.get("syllables", 0),
            detected_syllables=len(result.pivot_json.blocks[0].segments) if result.pivot_json and result.pivot_json.blocks else 0,
            candidates=result.candidates,
            best_lyric=result.best_line,
            best_score=result.best_score,
            all_scores=all_scores,
            phonetic_hints=phonetic_hints,
            tempo=result.metadata.get("tempo", 0),
            duration=result.metadata.get("duration", 0),
        )
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_all_generations(verbose: bool = True) -> list[GenerationResult]:
    """
    Run LLM generation on all audio samples.
    """
    print("\n" + "=" * 75)
    print("  🎤 AUDIO SAMPLES LLM GENERATION TEST")
    print("  Full Pipeline: Audio → Analysis → Prompt → LLM → Validation")
    print("=" * 75)
    
    # Find audio samples directory
    project_root = Path(__file__).parent.parent
    samples_dir = project_root / "audio samples"
    
    if not samples_dir.exists():
        print(f"❌ Error: Audio samples directory not found: {samples_dir}")
        return []
    
    # Check Ollama connection
    print("\n🔌 Checking LLM connection...")
    test_pipeline = CorePipeline(mock_mode=True)
    ollama_available = False
    try:
        ollama_available = test_pipeline.generation_engine.test_connection()
        if ollama_available:
            print("   ✅ Ollama connected - using REAL LLM generation")
        else:
            print("   ⚠️ Ollama not available - using MOCK mode")
    except Exception as e:
        print(f"   ⚠️ Could not connect to Ollama: {e}")
    
    # Create pipeline
    if ollama_available:
        pipeline = CorePipeline.__new__(CorePipeline)
        pipeline.audio_engine = AudioEngine(mock_mode=True)  # Skip Demucs
        pipeline.prompt_engine = PromptEngine()
        pipeline.generation_engine = GenerationEngine(mock_mode=False)  # REAL LLM
        pipeline.validator = LyricValidator()
        pipeline.mock_mode = False
    else:
        pipeline = CorePipeline(mock_mode=True)
    
    results = []
    
    # Process each audio file
    for filename, expected in AUDIO_SAMPLES.items():
        filepath = samples_dir / filename
        
        if not filepath.exists():
            print(f"\n⚠️ File not found: {filename}")
            continue
        
        print(f"\n{'─' * 75}")
        print(f"📄 {filename}")
        print(f"   Expected: \"{expected['phrase']}\" ({expected['syllables']} syllables)")
        print(f"   Breakdown: {expected['breakdown']}")
        
        result = generate_for_file(filepath, pipeline)
        
        if result:
            results.append(result)
            
            # Print results
            print(f"\n   📊 Detection: {result.detected_syllables} syllables | {result.tempo:.1f} BPM | {result.duration:.2f}s")
            
            if result.phonetic_hints:
                print(f"\n   🔊 Phonetic Hints:")
                for i, hint in enumerate(result.phonetic_hints[:8], 1):  # Max 8
                    print(f"      Syllable {i}: /{hint}/")
            
            print(f"\n   🎯 LLM Candidates:")
            for i, (candidate, score, valid) in enumerate(result.all_scores, 1):
                status = "✅" if valid else "❌"
                winner = "🏆" if candidate == result.best_lyric else "  "
                print(f"      {winner} {i}. \"{candidate}\" (score: {score:.2f}) {status}")
            
            print(f"\n   🏆 Best Match: \"{result.best_lyric}\" (score: {result.best_score:.2f})")
    
    # Print summary
    print("\n" + "=" * 75)
    print("  📊 SUMMARY")
    print("=" * 75)
    
    valid_results = [r for r in results if r.best_lyric is not None]
    
    print(f"\n   Total files processed: {len(results)}")
    print(f"   Files with valid lyrics: {len(valid_results)}/{len(results)}")
    
    if valid_results:
        avg_score = sum(r.best_score for r in valid_results) / len(valid_results)
        print(f"   Average best score: {avg_score:.2f}")
    
    print("\n" + "=" * 75 + "\n")
    
    return results


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_report(results: list[GenerationResult] | None = None):
    """Generate a markdown report of the LLM generation results."""
    
    if results is None:
        results = run_all_generations(verbose=False)
    
    project_root = Path(__file__).parent.parent
    report_path = project_root / "docs" / "LLM_GENERATION_REPORT.md"
    
    lines = [
        "# 🎤 LLM Lyric Generation Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "This report shows LLM-generated lyric candidates for each audio sample.",
        "",
        "---",
        "",
    ]
    
    for result in results:
        lines.append(f"## {result.filename}")
        lines.append("")
        lines.append(f"**Expected:** \"{result.expected_phrase}\"  ")
        lines.append(f"**Syllables:** {result.expected_syllables} expected, {result.detected_syllables} detected")
        lines.append("")
        
        # Phonetic hints
        if result.phonetic_hints:
            lines.append("### Phonetic Hints (Sound-Alike)")
            lines.append("")
            for i, hint in enumerate(result.phonetic_hints, 1):
                lines.append(f"- Syllable {i}: **/{hint}/**")
            lines.append("")
        
        # Candidates
        lines.append("### LLM Candidates")
        lines.append("")
        lines.append("| # | Candidate | Score | Valid |")
        lines.append("|---|-----------|-------|-------|")
        
        for i, (candidate, score, valid) in enumerate(result.all_scores, 1):
            status = "✅" if valid else "❌"
            winner = "🏆 " if candidate == result.best_lyric else ""
            lines.append(f"| {i} | {winner}\"{candidate}\" | {score:.2f} | {status} |")
        
        lines.append("")
        lines.append(f"**Winner:** \"{result.best_lyric}\" with score {result.best_score:.2f}")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    # Summary
    lines.append("## Summary")
    lines.append("")
    valid_count = sum(1 for r in results if r.best_lyric is not None)
    lines.append(f"- Files processed: {len(results)}")
    lines.append(f"- Valid lyrics found: {valid_count}/{len(results)}")
    if results:
        avg_score = sum(r.best_score for r in results if r.best_lyric) / max(valid_count, 1)
        lines.append(f"- Average score: {avg_score:.2f}")
    
    # Write report
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"\n📝 Report saved to: {report_path}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Audio Samples LLM Generation Test")
    parser.add_argument("--report", action="store_true", help="Generate markdown report")
    parser.add_argument("--file", "-f", type=str, help="Test a single file")
    args = parser.parse_args()
    
    if args.file:
        # Single file mode
        project_root = Path(__file__).parent.parent
        filepath = project_root / "audio samples" / args.file
        
        if not filepath.exists():
            filepath = Path(args.file)
        
        if not filepath.exists():
            print(f"❌ File not found: {args.file}")
            sys.exit(1)
        
        # Create pipeline
        test_pipeline = CorePipeline(mock_mode=True)
        ollama_available = test_pipeline.generation_engine.test_connection()
        
        if ollama_available:
            pipeline = CorePipeline.__new__(CorePipeline)
            pipeline.audio_engine = AudioEngine(mock_mode=True)
            pipeline.prompt_engine = PromptEngine()
            pipeline.generation_engine = GenerationEngine(mock_mode=False)
            pipeline.validator = LyricValidator()
            pipeline.mock_mode = False
        else:
            pipeline = CorePipeline(mock_mode=True)
        
        result = generate_for_file(filepath, pipeline)
        if result:
            print(f"\n🏆 Best: \"{result.best_lyric}\" (score: {result.best_score:.2f})")
    elif args.report:
        results = run_all_generations()
        generate_report(results)
    else:
        run_all_generations()
