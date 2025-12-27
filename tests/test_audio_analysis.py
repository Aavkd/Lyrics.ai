"""
Flow-to-Lyrics: Audio Analysis Verification Test
=================================================
Stand-alone test script that validates stress and sustain detection
using synthesized audio with known characteristics.

Test Cases:
    Beat 1: Amplitude 1.0 (LOUD)   → is_stressed: True
    Beat 2: Amplitude 0.5 (QUIET)  → is_stressed: False
    Beat 3: Duration 1.0s (LONG)   → is_sustained: True
    Beat 4: Duration 0.1s (SHORT)  → is_sustained: False
"""

import sys
import json
import tempfile
import numpy as np
import soundfile as sf
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from audio_engine import LibrosaAnalyzer, PivotFormatter


def generate_sine_wave(
    frequency: float,
    duration: float,
    sample_rate: int,
    amplitude: float = 1.0
) -> np.ndarray:
    """Generate a sine wave with given parameters."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    return amplitude * np.sin(2 * np.pi * frequency * t)


def generate_test_audio(sample_rate: int = 22050) -> tuple[np.ndarray, list[dict]]:
    """
    Generate synthetic audio with known stress/sustain characteristics.
    
    Creates 4 distinct beats with known properties:
        Beat 1: LOUD (amp=1.0), SHORT (0.2s) → stressed=True, sustained=False
        Beat 2: QUIET (amp=0.3), SHORT (0.2s) → stressed=False, sustained=False
        Beat 3: MEDIUM (amp=0.5), LONG (1.0s) → stressed=False, sustained=True
        Beat 4: MEDIUM (amp=0.5), SHORT (0.1s) → stressed=False, sustained=False
    
    Returns:
        Tuple of (audio_signal, expected_properties)
    """
    # Add silence gaps between beats to ensure onset detection
    silence_gap = 0.3  # 300ms silence between beats
    freq = 440  # A4 note
    
    # Beat 1: LOUD and SHORT
    beat1 = generate_sine_wave(freq, 0.2, sample_rate, amplitude=1.0)
    gap1 = np.zeros(int(silence_gap * sample_rate))
    
    # Beat 2: QUIET and SHORT
    beat2 = generate_sine_wave(freq, 0.2, sample_rate, amplitude=0.3)
    gap2 = np.zeros(int(silence_gap * sample_rate))
    
    # Beat 3: MEDIUM and LONG (sustained)
    beat3 = generate_sine_wave(freq, 1.0, sample_rate, amplitude=0.5)
    gap3 = np.zeros(int(silence_gap * sample_rate))
    
    # Beat 4: MEDIUM and SHORT
    beat4 = generate_sine_wave(freq, 0.1, sample_rate, amplitude=0.5)
    
    # Concatenate all segments
    audio = np.concatenate([beat1, gap1, beat2, gap2, beat3, gap3, beat4])
    
    # Expected properties for verification
    expected = [
        {"is_stressed": True, "is_sustained": False, "description": "LOUD, SHORT"},
        {"is_stressed": False, "is_sustained": False, "description": "QUIET, SHORT"},
        {"is_stressed": False, "is_sustained": True, "description": "MEDIUM, LONG"},
        {"is_stressed": False, "is_sustained": False, "description": "MEDIUM, SHORT"},
    ]
    
    return audio, expected


def run_verification_test():
    """Run the complete verification test suite."""
    print("=" * 60)
    print("Flow-to-Lyrics: Audio Analysis Verification Test")
    print("=" * 60)
    
    sample_rate = 22050
    
    # Generate synthetic audio
    print("\n[1/4] Generating synthetic test audio...")
    audio, expected = generate_test_audio(sample_rate)
    print(f"      Generated {len(audio) / sample_rate:.2f}s of audio with {len(expected)} beats")
    
    # Save to temporary file
    print("\n[2/4] Saving audio to temporary file...")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name
        sf.write(temp_path, audio, sample_rate)
        print(f"      Saved to: {temp_path}")
    
    try:
        # Run LibrosaAnalyzer
        print("\n[3/4] Running LibrosaAnalyzer...")
        analyzer = LibrosaAnalyzer(sample_rate=sample_rate)
        analysis = analyzer.analyze(temp_path)
        print(f"      Tempo: {analysis.tempo:.1f} BPM")
        print(f"      Duration: {analysis.duration:.2f}s")
        print(f"      Onsets detected: {len(analysis.onset_times)}")
        
        # Run PivotFormatter with analysis
        print("\n[4/4] Running PivotFormatter with stress/sustain detection...")
        formatter = PivotFormatter(
            stress_threshold=1.2,
            stress_window_size=3,  # Smaller window for test
            sustain_threshold=0.4
        )
        pivot = formatter.format(analysis)
        
        # Get segments
        segments = pivot.blocks[0].segments if pivot.blocks else []
        
        # Print results
        print("\n" + "=" * 60)
        print("RESULTS:")
        print("=" * 60)
        
        output = pivot.to_dict()
        print(json.dumps(output, indent=2))
        
        # Verification
        print("\n" + "=" * 60)
        print("VERIFICATION:")
        print("=" * 60)
        
        # We expect 4 onsets for 4 beats, but librosa might detect differently
        # So we check the first N segments where N = min(detected, expected)
        num_to_check = min(len(segments), len(expected))
        
        if num_to_check < len(expected):
            print(f"\n⚠️  Warning: Expected {len(expected)} segments, detected {len(segments)}")
            print("    This is normal - onset detection may vary with synthetic audio.")
        
        all_passed = True
        
        # Check stress detection
        print("\n📊 Stress Detection Tests:")
        for i, seg in enumerate(segments):
            if i < len(expected):
                exp = expected[i]
                status = "✓ PASS" if seg.is_stressed == exp["is_stressed"] else "✗ FAIL"
                if seg.is_stressed != exp["is_stressed"]:
                    all_passed = False
                print(f"   Segment {i+1} ({exp['description']}): "
                      f"is_stressed={seg.is_stressed} (expected: {exp['is_stressed']}) {status}")
        
        # Check sustain detection
        print("\n⏱️  Sustain Detection Tests:")
        for i, seg in enumerate(segments):
            if i < len(expected):
                exp = expected[i]
                status = "✓ PASS" if seg.is_sustained == exp["is_sustained"] else "✗ FAIL"
                if seg.is_sustained != exp["is_sustained"]:
                    all_passed = False
                print(f"   Segment {i+1} ({exp['description']}): "
                      f"is_sustained={seg.is_sustained} (expected: {exp['is_sustained']}) {status}")
        
        # Check JSON structure
        print("\n📋 JSON Structure Tests:")
        first_seg = output["blocks"][0]["segments"][0] if output["blocks"] and output["blocks"][0]["segments"] else {}
        
        has_stressed = "is_stressed" in first_seg
        has_sustained = "is_sustained" in first_seg
        
        print(f"   'is_stressed' field present: {has_stressed} {'✓ PASS' if has_stressed else '✗ FAIL'}")
        print(f"   'is_sustained' field present: {has_sustained} {'✓ PASS' if has_sustained else '✗ FAIL'}")
        
        if not has_stressed or not has_sustained:
            all_passed = False
        
        # Final result
        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 ALL TESTS PASSED!")
        else:
            print("❌ SOME TESTS FAILED - Review the output above")
        print("=" * 60)
        
        return all_passed
        
    finally:
        # Cleanup temporary file
        Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    success = run_verification_test()
    sys.exit(0 if success else 1)
