"""
Flow-to-Lyrics: Precision Tuning Test Harness
==============================================
Phase 1 - Step 1.3: Onset Detection Calibration

This script analyzes the audio samples in `audio samples/` folder
to find optimal onset detection parameters for the user's vocal style.

Run: python tests/test_precision_tuning.py
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class OnsetConfig:
    """Configuration for onset detection."""
    name: str
    backtrack: bool = True
    wait: int = 1
    pre_max: int = 1
    post_max: int = 1
    pre_avg: int = 1
    post_avg: int = 1
    delta: float = 0.07
    
    def to_dict(self) -> dict:
        return {
            "wait": self.wait,
            "pre_max": self.pre_max,
            "post_max": self.post_max,
            "pre_avg": self.pre_avg,
            "post_avg": self.post_avg,
            "delta": self.delta
        }


@dataclass
class TuningResult:
    """Result of testing a configuration on an audio file."""
    file_name: str
    expected_syllables: int
    detected_syllables: int
    error: int
    config_name: str
    onset_times: list[float]


# =============================================================================
# PRESET CONFIGURATIONS
# =============================================================================

CONFIGS = [
    OnsetConfig(
        name="Default",
        backtrack=True,
        wait=1,
        pre_max=1,
        post_max=1,
        pre_avg=1,
        post_avg=1,
        delta=0.07
    ),
    OnsetConfig(
        name="Sensitive",
        backtrack=True,
        wait=1,
        pre_max=1,
        post_max=1,
        pre_avg=1,
        post_avg=1,
        delta=0.03  # Lower threshold = more onsets detected
    ),
    OnsetConfig(
        name="Less Sensitive",
        backtrack=True,
        wait=1,
        pre_max=1,
        post_max=1,
        pre_avg=1,
        post_avg=1,
        delta=0.1  # Higher threshold = fewer onsets
    ),
    OnsetConfig(
        name="Wide Window",
        backtrack=True,
        wait=3,
        pre_max=3,
        post_max=3,
        pre_avg=3,
        post_avg=3,
        delta=0.07
    ),
    OnsetConfig(
        name="Narrow Window",
        backtrack=True,
        wait=1,
        pre_max=1,
        post_max=1,
        pre_avg=1,
        post_avg=1,
        delta=0.05
    ),
    OnsetConfig(
        name="Vocal Optimized",
        backtrack=True,
        wait=2,
        pre_max=2,
        post_max=2,
        pre_avg=2,
        post_avg=2,
        delta=0.05
    ),
]


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def parse_syllable_count_from_filename(filename: str) -> int | None:
    """
    Extract expected syllable count from filename.
    
    Examples:
        "3_syllabes_test.mp3" -> 3
        "10_syllabes_test.mp3" -> 10
        "3_syllabes(sustained)_test.mp3" -> 3
    """
    # Match pattern: number followed by _syllabe or _syllabes
    match = re.match(r"(\d+)_syllabe", filename)
    if match:
        return int(match.group(1))
    return None


def detect_onsets_with_config(
    audio_path: str, 
    config: OnsetConfig,
    sr: int = 22050
) -> list[float]:
    """
    Detect onsets using a specific configuration.
    
    Args:
        audio_path: Path to audio file.
        config: OnsetConfig with parameters.
        sr: Sample rate.
        
    Returns:
        List of onset times in seconds.
    """
    y, sr = librosa.load(audio_path, sr=sr)
    
    # Compute onset strength envelope
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    
    # Detect onsets with configuration
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_env,
        sr=sr,
        backtrack=config.backtrack,
        wait=config.wait,
        pre_max=config.pre_max,
        post_max=config.post_max,
        pre_avg=config.pre_avg,
        post_avg=config.post_avg,
        delta=config.delta,
        units='frames'
    )
    
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    return onset_times.tolist()


def get_audio_samples_dir() -> Path:
    """Get the audio samples directory path."""
    project_root = Path(__file__).parent.parent
    return project_root / "audio samples"


def load_audio_samples() -> list[tuple[Path, int]]:
    """
    Load audio samples and their expected syllable counts.
    
    Returns:
        List of (file_path, expected_syllables) tuples.
    """
    samples_dir = get_audio_samples_dir()
    
    if not samples_dir.exists():
        raise FileNotFoundError(f"Audio samples directory not found: {samples_dir}")
    
    samples = []
    for file_path in samples_dir.glob("*.mp3"):
        expected = parse_syllable_count_from_filename(file_path.name)
        if expected is not None:
            samples.append((file_path, expected))
    
    # Sort by expected syllable count
    samples.sort(key=lambda x: x[1])
    
    return samples


# =============================================================================
# MAIN TUNING FUNCTION
# =============================================================================

def run_precision_tuning(verbose: bool = True) -> dict:
    """
    Run precision tuning on all audio samples.
    
    Args:
        verbose: If True, print detailed output.
        
    Returns:
        Dictionary with results and best configuration.
    """
    print("\n" + "=" * 70)
    print("  🎯 PRECISION TUNING: Onset Detection Calibration")
    print("=" * 70)
    
    # Load samples
    try:
        samples = load_audio_samples()
        print(f"\n📁 Found {len(samples)} audio samples:")
        for path, expected in samples:
            print(f"   • {path.name} (expected: {expected} syllables)")
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        return {"error": str(e)}
    
    # Run all configurations on all samples
    all_results: list[TuningResult] = []
    config_scores: dict[str, int] = {c.name: 0 for c in CONFIGS}
    
    print("\n" + "-" * 70)
    print("  Testing Configurations...")
    print("-" * 70)
    
    for config in CONFIGS:
        if verbose:
            print(f"\n🔧 Config: {config.name}")
        
        config_error_sum = 0
        
        for file_path, expected in samples:
            onset_times = detect_onsets_with_config(str(file_path), config)
            detected = len(onset_times)
            error = detected - expected
            config_error_sum += abs(error)
            
            result = TuningResult(
                file_name=file_path.name,
                expected_syllables=expected,
                detected_syllables=detected,
                error=error,
                config_name=config.name,
                onset_times=onset_times
            )
            all_results.append(result)
            
            if verbose:
                status = "✓" if error == 0 else "✗"
                error_str = f"+{error}" if error > 0 else str(error)
                print(f"   {status} {file_path.name}: {expected} → {detected} (error: {error_str})")
        
        # Lower total error = better score
        config_scores[config.name] = config_error_sum
    
    # Find best configuration (lowest total error)
    best_config_name = min(config_scores, key=config_scores.get)
    best_config = next(c for c in CONFIGS if c.name == best_config_name)
    
    # Print summary table
    print("\n" + "=" * 70)
    print("  📊 RESULTS SUMMARY")
    print("=" * 70)
    
    print("\n┌" + "─" * 68 + "┐")
    print(f"│ {'File':<35} │ {'Expected':>8} │ {'Config':<15} │ {'Error':>5} │")
    print("├" + "─" * 68 + "┤")
    
    # Group by file and show best config for each
    for file_path, expected in samples:
        file_results = [r for r in all_results if r.file_name == file_path.name]
        best_for_file = min(file_results, key=lambda r: abs(r.error))
        
        error_str = f"+{best_for_file.error}" if best_for_file.error > 0 else str(best_for_file.error)
        if best_for_file.error == 0:
            error_str = "✓ 0"
        
        print(f"│ {file_path.name:<35} │ {expected:>8} │ {best_for_file.config_name:<15} │ {error_str:>5} │")
    
    print("└" + "─" * 68 + "┘")
    
    # Config ranking
    print("\n📈 Configuration Ranking (by total error):")
    sorted_configs = sorted(config_scores.items(), key=lambda x: x[1])
    for i, (name, total_error) in enumerate(sorted_configs, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        print(f"   {medal} {i}. {name}: Total Error = {total_error}")
    
    # Best config details
    print("\n" + "=" * 70)
    print(f"  🏆 RECOMMENDED CONFIGURATION: {best_config.name}")
    print("=" * 70)
    print(f"\n   Parameters:")
    print(f"   • backtrack = {best_config.backtrack}")
    print(f"   • wait = {best_config.wait}")
    print(f"   • pre_max = {best_config.pre_max}")
    print(f"   • post_max = {best_config.post_max}")
    print(f"   • pre_avg = {best_config.pre_avg}")
    print(f"   • post_avg = {best_config.post_avg}")
    print(f"   • delta = {best_config.delta}")
    
    # Detailed analysis per sample with best config
    print("\n📋 Detailed Analysis (Best Config):")
    for file_path, expected in samples:
        result = next(r for r in all_results 
                      if r.file_name == file_path.name 
                      and r.config_name == best_config.name)
        
        print(f"\n   📄 {file_path.name}")
        print(f"      Expected: {expected} syllables")
        print(f"      Detected: {result.detected_syllables} syllables")
        print(f"      Onset times: {[round(t, 3) for t in result.onset_times[:10]]}")
        if len(result.onset_times) > 10:
            print(f"                   ... and {len(result.onset_times) - 10} more")
    
    print("\n" + "=" * 70 + "\n")
    
    return {
        "samples": samples,
        "results": all_results,
        "config_scores": config_scores,
        "best_config": best_config,
        "best_config_name": best_config_name
    }


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    run_precision_tuning(verbose=True)
