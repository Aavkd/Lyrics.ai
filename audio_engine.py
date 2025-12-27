"""
Flow-to-Lyrics: Audio Analysis Engine
=====================================
Core DSP logic for Phase 1 - Audio Analysis Backend.

This module provides:
1. Vocal isolation via Demucs
2. Rhythm analysis via Librosa (BPM, onsets)
3. JSON Pivot formatting for frontend consumption
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import librosa
import numpy as np


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Segment:
    """A single rhythmic segment (syllable slot)."""
    time_start: float
    duration: float
    is_stressed: bool = False


@dataclass
class Block:
    """A block of segments (typically one bar or phrase)."""
    id: int
    syllable_target: int
    segments: list[Segment]


@dataclass
class PivotJSON:
    """The complete Pivot JSON structure for frontend."""
    tempo: float
    duration: float
    blocks: list[Block]
    
    def to_dict(self) -> dict:
        """Convert to dictionary format for JSON serialization."""
        return {
            "meta": {
                "tempo": round(self.tempo, 2),
                "duration": round(self.duration, 2)
            },
            "blocks": [
                {
                    "id": block.id,
                    "syllable_target": block.syllable_target,
                    "segments": [
                        {
                            "time_start": round(seg.time_start, 3),
                            "duration": round(seg.duration, 3),
                            "is_stressed": seg.is_stressed
                        }
                        for seg in block.segments
                    ]
                }
                for block in self.blocks
            ]
        }


@dataclass
class AnalysisResult:
    """Result of audio analysis."""
    tempo: float
    duration: float
    onset_times: list[float]
    sample_rate: int


# =============================================================================
# DEMUCS WRAPPER - VOCAL ISOLATION
# =============================================================================

class DemucsProcessor:
    """
    Wrapper for Demucs vocal isolation.
    
    Demucs (Hybrid Transformer) separates audio into 4 stems:
    - drums
    - bass  
    - other
    - vocals (this is what we keep)
    """
    
    def __init__(self, mock_mode: bool = False):
        """
        Initialize the Demucs processor.
        
        Args:
            mock_mode: If True, skip actual Demucs processing and return
                       the original file. Useful for development without GPU.
        """
        self.mock_mode = mock_mode
        self.model_name = "htdemucs"  # Hybrid Transformer Demucs
    
    def isolate_vocals(self, audio_path: str, output_dir: Optional[str] = None) -> str:
        """
        Isolate vocals from the given audio file.
        
        Args:
            audio_path: Path to input audio file (MP3/WAV).
            output_dir: Directory to save output. If None, uses temp directory.
            
        Returns:
            Path to the isolated vocals stem.
            
        Raises:
            RuntimeError: If Demucs processing fails.
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Mock mode: return original file for development
        if self.mock_mode:
            print(f"[MOCK MODE] Skipping Demucs, returning original: {audio_path}")
            return str(audio_path)
        
        # Set up output directory
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="demucs_")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Run Demucs via subprocess
        # Command: python -m demucs --two-stems vocals -o output_dir audio_file
        cmd = [
            "python", "-m", "demucs",
            "--two-stems", "vocals",  # Only separate vocals vs instrumental
            "-o", str(output_dir),
            str(audio_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            print(f"[DEMUCS] Processing complete: {result.stdout}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Demucs processing failed: {e.stderr}")
        except FileNotFoundError:
            raise RuntimeError(
                "Demucs not found. Install with: pip install demucs"
            )
        
        # Find the vocals output file
        # Demucs outputs to: output_dir/htdemucs/track_name/vocals.wav
        track_name = audio_path.stem
        vocals_path = output_dir / self.model_name / track_name / "vocals.wav"
        
        if not vocals_path.exists():
            raise RuntimeError(f"Vocals file not found at expected path: {vocals_path}")
        
        return str(vocals_path)


# =============================================================================
# LIBROSA ANALYZER - RHYTHM DETECTION
# =============================================================================

class LibrosaAnalyzer:
    """
    Librosa-based audio analysis for BPM and onset detection.
    """
    
    def __init__(self, sample_rate: int = 22050):
        """
        Initialize the analyzer.
        
        Args:
            sample_rate: Sample rate for audio loading (default: 22050 Hz).
        """
        self.sample_rate = sample_rate
    
    def analyze(self, audio_path: str) -> AnalysisResult:
        """
        Analyze audio file for tempo and onsets.
        
        Args:
            audio_path: Path to audio file.
            
        Returns:
            AnalysisResult with tempo, duration, and onset times.
        """
        # Load audio file
        y, sr = librosa.load(audio_path, sr=self.sample_rate)
        
        # Calculate duration
        duration = librosa.get_duration(y=y, sr=sr)
        
        # Detect tempo (BPM)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        
        # Handle tempo as array (newer librosa versions return array)
        if isinstance(tempo, np.ndarray):
            tempo = float(tempo[0]) if len(tempo) > 0 else 120.0
        else:
            tempo = float(tempo)
        
        # Detect onsets (syllable start points)
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units='frames')
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)
        
        return AnalysisResult(
            tempo=tempo,
            duration=duration,
            onset_times=onset_times.tolist(),
            sample_rate=sr
        )


# =============================================================================
# JSON PIVOT FORMATTER
# =============================================================================

class PivotFormatter:
    """
    Formats analysis results into the Pivot JSON structure.
    """
    
    def __init__(self, default_segment_duration: float = 0.2):
        """
        Initialize the formatter.
        
        Args:
            default_segment_duration: Default duration for the last segment
                                      (when no following onset exists).
        """
        self.default_segment_duration = default_segment_duration
    
    def format(self, analysis: AnalysisResult) -> PivotJSON:
        """
        Format analysis results into Pivot JSON.
        
        Args:
            analysis: AnalysisResult from LibrosaAnalyzer.
            
        Returns:
            PivotJSON object ready for serialization.
        """
        segments = []
        onset_times = analysis.onset_times
        
        for i, onset_time in enumerate(onset_times):
            # Calculate duration to next onset
            if i < len(onset_times) - 1:
                duration = onset_times[i + 1] - onset_time
            else:
                # Last segment: use default duration
                duration = self.default_segment_duration
            
            segments.append(Segment(
                time_start=onset_time,
                duration=duration,
                is_stressed=False  # Default to false for MVP
            ))
        
        # Create single block containing all segments (MVP approach)
        # Phase 2 can add bar detection to split into multiple blocks
        block = Block(
            id=1,
            syllable_target=len(segments),  # Number of onsets = syllable slots
            segments=segments
        )
        
        return PivotJSON(
            tempo=analysis.tempo,
            duration=analysis.duration,
            blocks=[block]
        )


# =============================================================================
# MAIN AUDIO ENGINE
# =============================================================================

class AudioEngine:
    """
    Main audio processing engine combining all components.
    
    Usage:
        engine = AudioEngine(mock_mode=True)  # Development mode
        result = engine.process("song.mp3")
        json_output = result.to_dict()
    """
    
    def __init__(self, mock_mode: bool = False):
        """
        Initialize the audio engine.
        
        Args:
            mock_mode: If True, skip Demucs processing (development mode).
        """
        self.demucs = DemucsProcessor(mock_mode=mock_mode)
        self.analyzer = LibrosaAnalyzer()
        self.formatter = PivotFormatter()
        self.mock_mode = mock_mode
    
    def process(self, audio_path: str, output_dir: Optional[str] = None) -> PivotJSON:
        """
        Process an audio file through the complete pipeline.
        
        Pipeline:
        1. Isolate vocals via Demucs
        2. Analyze rhythm via Librosa
        3. Format into Pivot JSON
        
        Args:
            audio_path: Path to input audio file.
            output_dir: Optional directory for intermediate files.
            
        Returns:
            PivotJSON object with analysis results.
        """
        print(f"[AudioEngine] Processing: {audio_path}")
        print(f"[AudioEngine] Mock mode: {self.mock_mode}")
        
        # Step 1: Isolate vocals
        vocals_path = self.demucs.isolate_vocals(audio_path, output_dir)
        print(f"[AudioEngine] Vocals path: {vocals_path}")
        
        # Step 2: Analyze audio
        analysis = self.analyzer.analyze(vocals_path)
        print(f"[AudioEngine] Tempo: {analysis.tempo:.1f} BPM")
        print(f"[AudioEngine] Duration: {analysis.duration:.2f}s")
        print(f"[AudioEngine] Onsets detected: {len(analysis.onset_times)}")
        
        # Step 3: Format to Pivot JSON
        pivot = self.formatter.format(analysis)
        
        return pivot


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    import json
    import sys
    
    print("Flow-to-Lyrics: Audio Engine Test")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Usage: python audio_engine.py <audio_file> [--mock]")
        print("\nExample:")
        print("  python audio_engine.py song.mp3 --mock")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    mock_mode = "--mock" in sys.argv
    
    engine = AudioEngine(mock_mode=mock_mode)
    
    try:
        result = engine.process(audio_path)
        output = result.to_dict()
        
        print("\n" + "=" * 50)
        print("PIVOT JSON OUTPUT:")
        print("=" * 50)
        print(json.dumps(output, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
