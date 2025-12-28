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
    is_sustained: bool = False
    pitch_contour: str = "mid"  # "low", "mid", "high", "rising", "falling"
    audio_phonemes: str = ""  # Raw IPA phonemes from Allosaurus (e.g., "b a d a")


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
                            "is_stressed": seg.is_stressed,
                            "is_sustained": seg.is_sustained,
                            "pitch_contour": seg.pitch_contour,
                            "audio_phonemes": seg.audio_phonemes
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
    audio_signal: np.ndarray = None  # Raw audio for amplitude analysis


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
# AUDIO UTILITIES
# =============================================================================

def resample_audio(y: np.ndarray, orig_sr: int, target_sr: int = 16000) -> np.ndarray:
    """
    Resample audio to target sample rate.
    
    Allosaurus requires 16kHz mono audio for phone recognition.
    
    Args:
        y: Audio signal array.
        orig_sr: Original sample rate.
        target_sr: Target sample rate (default: 16000 Hz for Allosaurus).
        
    Returns:
        Resampled audio signal.
    """
    if orig_sr == target_sr:
        return y
    return librosa.resample(y, orig_sr=orig_sr, target_sr=target_sr)


# =============================================================================
# PHONETIC ANALYZER - IPA RECOGNITION
# =============================================================================

def classify_sound_type(y_segment: np.ndarray, sr: int) -> str:
    """
    Fallback: classify sound as vowel, consonant, or mid using spectral features.
    
    Used when Allosaurus fails to detect phonemes. Provides basic guidance
    to the LLM about the nature of the sound.
    
    Args:
        y_segment: Audio signal array for the segment.
        sr: Sample rate.
        
    Returns:
        "[vowel]" for open vowel sounds (low centroid, low ZCR)
        "[consonant]" for fricatives/plosives (high ZCR)
        "[mid]" for uncertain classification
    """
    if len(y_segment) == 0:
        return "[mid]"
    
    try:
        # Spectral centroid: high = bright sound, low = deeper sound
        centroid = librosa.feature.spectral_centroid(y=y_segment, sr=sr)
        mean_centroid = np.mean(centroid)
        
        # Zero crossing rate: high = noisy/fricative, low = tonal/vowel
        zcr = librosa.feature.zero_crossing_rate(y_segment)
        mean_zcr = np.mean(zcr)
        
        # Classify based on features
        if mean_zcr > 0.1:
            return "[consonant]"  # High ZCR = fricative/plosive
        elif mean_centroid < 2000:
            return "[vowel]"      # Low centroid = open vowel sound
        else:
            return "[mid]"        # Uncertain / mixed
            
    except Exception:
        return "[mid]"  # Return neutral on any error

class PhoneticAnalyzer:
    """
    Wrapper for Allosaurus phone recognition.
    
    Allosaurus is a universal phone recognizer that outputs IPA tokens
    regardless of language or meaning - perfect for analyzing mumbles.
    
    Enhanced features:
    - Configurable segment padding for acoustic context
    - Retry mechanism with expanded padding on failure
    - Fallback classification when Allosaurus fails
    - Short segment merging for better recognition
    
    Usage:
        analyzer = PhoneticAnalyzer()
        ipa = analyzer.analyze_segment(audio_chunk, sample_rate=22050)
        # Returns: "b a d a" (IPA tokens)
    """
    
    def __init__(self, enabled: bool = None):
        """
        Initialize the Phonetic Analyzer.
        
        Args:
            enabled: If False, skip phonetic analysis (backward compatible - no fallback).
                    If None, reads from config and uses fallback on failure.
        """
        # Track if user explicitly disabled (for backward compatibility)
        # If explicitly disabled, don't use fallback either
        self._explicitly_disabled = (enabled is False)
        
        # Load configuration
        try:
            from config import config
            self.min_duration = config.PHONETIC_MIN_DURATION
            self.padding = config.PHONETIC_PADDING
            self.retry_padding = config.PHONETIC_RETRY_PADDING
            self.fallback_enabled = config.PHONETIC_FALLBACK_ENABLED
            if enabled is None:
                enabled = config.PHONETIC_ENABLED
        except ImportError:
            # Fallback defaults if config not available
            self.min_duration = 0.10
            self.padding = 0.05
            self.retry_padding = 0.10
            self.fallback_enabled = True
            if enabled is None:
                enabled = True
        
        # Override fallback if explicitly disabled (backward compatibility)
        if self._explicitly_disabled:
            self.fallback_enabled = False
        
        self.enabled = enabled
        self.model = None
        self._initialized = False
    
    def _lazy_init(self):
        """
        Lazy initialization of Allosaurus model (download on first use).
        """
        if self._initialized:
            return
        
        if not self.enabled:
            self._initialized = True
            return
            
        try:
            from allosaurus.app import read_recognizer
            self.model = read_recognizer()
            print("[PhoneticAnalyzer] Allosaurus model loaded successfully")
        except ImportError:
            print("[PhoneticAnalyzer] WARNING: allosaurus not installed. Run: pip install allosaurus")
            self.enabled = False
        except Exception as e:
            print(f"[PhoneticAnalyzer] WARNING: Failed to load Allosaurus: {e}")
            self.enabled = False
        
        self._initialized = True
    
    def _run_allosaurus(self, y_segment: np.ndarray, sr: int) -> str:
        """
        Internal method: Run Allosaurus on audio segment.
        
        Args:
            y_segment: Audio signal array.
            sr: Sample rate.
            
        Returns:
            IPA string or empty string on failure.
        """
        if self.model is None:
            return ""
        
        # Resample to 16kHz for Allosaurus
        y_16k = resample_audio(y_segment, sr, 16000)
        
        import tempfile
        import soundfile as sf
        
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
                sf.write(temp_path, y_16k, 16000)
            
            result = self.model.recognize(temp_path)
            return result.strip() if result else ""
            
        except Exception as e:
            print(f"[PhoneticAnalyzer] Allosaurus call failed: {e}")
            return ""
        finally:
            if temp_path:
                try:
                    Path(temp_path).unlink(missing_ok=True)
                except Exception:
                    pass
    
    def analyze_segment(
        self, 
        y_segment: np.ndarray, 
        sr: int,
        min_duration: float = None,
        use_fallback: bool = True
    ) -> str:
        """
        Extract IPA phonemes from an audio segment.
        
        Args:
            y_segment: Audio signal array for the segment.
            sr: Sample rate of the audio.
            min_duration: Minimum duration in seconds. Uses config default if None.
            use_fallback: If True, use classify_sound_type() on failure.
            
        Returns:
            Space-separated IPA phoneme string (e.g., "b a d a").
            Returns "[vowel]", "[consonant]", or "[mid]" if fallback is used.
            Returns empty string if analysis fails and fallback is disabled.
        """
        self._lazy_init()
        
        if not self.enabled or self.model is None:
            if use_fallback and self.fallback_enabled:
                return classify_sound_type(y_segment, sr)
            return ""
        
        # Use config default if not specified
        if min_duration is None:
            min_duration = self.min_duration
        
        # Check minimum duration
        duration = len(y_segment) / sr
        if duration < min_duration:
            if use_fallback and self.fallback_enabled:
                return classify_sound_type(y_segment, sr)
            return ""
        
        # First attempt
        result = self._run_allosaurus(y_segment, sr)
        
        if result:
            return result
        
        # Fallback classification if enabled
        if use_fallback and self.fallback_enabled:
            return classify_sound_type(y_segment, sr)
        
        return ""
    
    def analyze_segments(
        self,
        y: np.ndarray,
        sr: int,
        onset_times: list[float],
        durations: list[float]
    ) -> list[str]:
        """
        Analyze multiple segments and return IPA phonemes for each.
        
        Enhanced with:
        - Padding on each side of segment for acoustic context
        - Retry mechanism with expanded padding on failure
        - Fallback classification when Allosaurus fails
        
        Args:
            y: Full audio signal.
            sr: Sample rate.
            onset_times: List of segment start times in seconds.
            durations: List of segment durations in seconds.
            
        Returns:
            List of IPA strings (or fallback tags), one per segment.
        """
        self._lazy_init()
        
        if not self.enabled or self.model is None:
            # Even when disabled, provide fallback if enabled
            if self.fallback_enabled:
                phonemes_list = []
                for onset_time, duration in zip(onset_times, durations):
                    start_sample = max(0, int(onset_time * sr))
                    end_sample = min(len(y), int((onset_time + duration) * sr))
                    if end_sample > start_sample:
                        segment_audio = y[start_sample:end_sample]
                        phonemes_list.append(classify_sound_type(segment_audio, sr))
                    else:
                        phonemes_list.append("[mid]")
                return phonemes_list
            return [""] * len(onset_times)
        
        # Calculate padding in samples
        padding_samples = int(self.padding * sr)
        retry_padding_samples = int(self.retry_padding * sr)
        
        phonemes_list = []
        detected_count = 0
        fallback_count = 0
        
        for onset_time, duration in zip(onset_times, durations):
            # Original segment boundaries
            orig_start = int(onset_time * sr)
            orig_end = int((onset_time + duration) * sr)
            
            # Add padding for first attempt (Phase A.1: Add Segment Padding)
            start_sample = max(0, orig_start - padding_samples)
            end_sample = min(len(y), orig_end + padding_samples)
            
            if end_sample <= start_sample:
                if self.fallback_enabled:
                    phonemes_list.append("[mid]")
                    fallback_count += 1
                else:
                    phonemes_list.append("")
                continue
            
            segment_audio = y[start_sample:end_sample]
            
            # First attempt with standard padding
            ipa = self._run_allosaurus(segment_audio, sr)
            
            # Retry with expanded padding if failed (Phase A.3: Add Retry)
            if not ipa and duration < 0.2:  # Only retry for short segments
                expanded_start = max(0, orig_start - retry_padding_samples)
                expanded_end = min(len(y), orig_end + retry_padding_samples)
                
                if expanded_end > expanded_start:
                    expanded_segment = y[expanded_start:expanded_end]
                    ipa = self._run_allosaurus(expanded_segment, sr)
            
            if ipa:
                phonemes_list.append(ipa)
                detected_count += 1
            else:
                # Fallback classification (Phase B.2)
                if self.fallback_enabled:
                    # Use original segment (without padding) for fallback classification
                    orig_segment = y[max(0, orig_start):min(len(y), orig_end)]
                    fallback = classify_sound_type(orig_segment, sr)
                    phonemes_list.append(fallback)
                    fallback_count += 1
                else:
                    phonemes_list.append("")
        
        # Log detection statistics
        total = len(onset_times)
        if total > 0:
            detection_rate = detected_count / total * 100
            print(f"[PhoneticAnalyzer] Detection: {detected_count}/{total} ({detection_rate:.1f}%), "
                  f"Fallback: {fallback_count}")
        
        return phonemes_list


# =============================================================================
# LIBROSA ANALYZER - RHYTHM DETECTION
# =============================================================================

class LibrosaAnalyzer:
    """
    Librosa-based audio analysis for BPM and onset detection.
    
    Enhanced with adaptive onset detection strategies:
    1. Spectral flux onset detection (primary)
    2. Energy-based onset detection (secondary, optional)
    3. Merged, deduplicated onset times
    """
    
    def __init__(self, sample_rate: int = 22050):
        """
        Initialize the analyzer.
        
        Args:
            sample_rate: Sample rate for audio loading (default: 22050 Hz).
        """
        self.sample_rate = sample_rate
        
        # Load configuration (import here to avoid circular imports)
        try:
            from config import config
            self.onset_delta = config.ONSET_DELTA
            self.use_energy_detection = config.ONSET_USE_ENERGY
            self.onset_wait = config.ONSET_WAIT
        except ImportError:
            # Fallback defaults if config not available
            self.onset_delta = 0.05
            self.use_energy_detection = True
            self.onset_wait = 1
    
    def _detect_onsets_spectral(
        self, 
        y: np.ndarray, 
        sr: int,
        onset_env: np.ndarray
    ) -> np.ndarray:
        """
        Detect onsets using spectral flux method.
        
        Args:
            y: Audio signal.
            sr: Sample rate.
            onset_env: Pre-computed onset strength envelope.
            
        Returns:
            Array of onset times in seconds.
        """
        onset_frames = librosa.onset.onset_detect(
            onset_envelope=onset_env,
            sr=sr,
            backtrack=True,
            wait=self.onset_wait,
            pre_max=1,
            post_max=1,
            pre_avg=1,
            post_avg=1,
            delta=self.onset_delta,
            units='frames'
        )
        return librosa.frames_to_time(onset_frames, sr=sr)
    
    def _detect_onsets_energy(
        self,
        y: np.ndarray,
        sr: int,
        hop_length: int = 512
    ) -> np.ndarray:
        """
        Detect onsets using energy-based (RMS) peak detection.
        
        This is a secondary detection strategy that catches onsets
        that spectral flux might miss, especially in continuous speech.
        
        Args:
            y: Audio signal.
            sr: Sample rate.
            hop_length: Hop length for RMS computation.
            
        Returns:
            Array of onset times in seconds.
        """
        # Compute RMS energy
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        
        # Simple peak detection: find local maxima above threshold
        # Use a more sensitive threshold for energy peaks
        rms_normalized = rms / (np.max(rms) + 1e-10)
        
        # Find peaks: points higher than neighbors and above threshold
        peaks = []
        threshold = 0.15  # Relative threshold for energy peaks
        min_distance = int(0.08 * sr / hop_length)  # Min 80ms between peaks
        
        last_peak_idx = -min_distance
        for i in range(1, len(rms_normalized) - 1):
            if i - last_peak_idx < min_distance:
                continue
            
            # Check if local maximum and above threshold
            if (rms_normalized[i] > rms_normalized[i-1] and 
                rms_normalized[i] > rms_normalized[i+1] and
                rms_normalized[i] > threshold):
                peaks.append(i)
                last_peak_idx = i
        
        # Convert frames to times
        if peaks:
            return librosa.frames_to_time(np.array(peaks), sr=sr, hop_length=hop_length)
        return np.array([])
    
    def _merge_onsets(
        self,
        spectral_onsets: np.ndarray,
        energy_onsets: np.ndarray,
        min_distance: float = 0.05
    ) -> list[float]:
        """
        Merge onsets from multiple detection strategies.
        
        Removes duplicates where two onsets are within min_distance of each other.
        When duplicates exist, keeps the earlier onset.
        
        Args:
            spectral_onsets: Onset times from spectral flux detection.
            energy_onsets: Onset times from energy-based detection.
            min_distance: Minimum time between onsets to consider them different.
            
        Returns:
            Sorted, deduplicated list of onset times.
        """
        # Combine all onsets
        all_onsets = np.concatenate([spectral_onsets, energy_onsets])
        
        if len(all_onsets) == 0:
            return []
        
        # Sort by time
        all_onsets = np.sort(all_onsets)
        
        # Deduplicate: keep onsets that are at least min_distance apart
        unique_onsets = [all_onsets[0]]
        for onset in all_onsets[1:]:
            if onset - unique_onsets[-1] >= min_distance:
                unique_onsets.append(onset)
        
        return unique_onsets
    
    def analyze(self, audio_path: str) -> AnalysisResult:
        """
        Analyze audio file for tempo and onsets using adaptive detection.
        
        Uses multiple onset detection strategies and merges results
        for more robust syllable identification.
        
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
        
        # Compute onset strength envelope (used by spectral detection)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        
        # Primary detection: Spectral flux
        spectral_onsets = self._detect_onsets_spectral(y, sr, onset_env)
        print(f"[LibrosaAnalyzer] Spectral flux: {len(spectral_onsets)} onsets (delta={self.onset_delta})")
        
        # Secondary detection: Energy-based (FALLBACK only)
        # Only use if spectral detection found very few onsets (< 3)
        # This prevents over-detection while providing safety net for near-silence
        if self.use_energy_detection and len(spectral_onsets) < 3:
            energy_onsets = self._detect_onsets_energy(y, sr)
            print(f"[LibrosaAnalyzer] Energy-based (fallback): {len(energy_onsets)} onsets")
            
            # Merge and deduplicate
            onset_times = self._merge_onsets(spectral_onsets, energy_onsets)
            print(f"[LibrosaAnalyzer] Merged (deduped): {len(onset_times)} onsets")
        else:
            onset_times = spectral_onsets.tolist()
            if self.use_energy_detection:
                print(f"[LibrosaAnalyzer] Energy detection skipped (spectral found {len(spectral_onsets)} onsets)")
        
        return AnalysisResult(
            tempo=tempo,
            duration=duration,
            onset_times=onset_times,
            sample_rate=sr,
            audio_signal=y
        )


# =============================================================================
# JSON PIVOT FORMATTER (with Enhanced Audio Analysis)
# =============================================================================

class PivotFormatter:
    """
    Formats analysis results into the Pivot JSON structure.
    
    Enhanced with:
    - Stress detection via RMS amplitude analysis
    - Sustain detection via duration thresholds
    - Phonetic analysis via Allosaurus (IPA extraction)
    - Automatic segment splitting for long segments
    """
    
    def __init__(
        self, 
        default_segment_duration: float = 0.2,
        stress_threshold: float = 1.2,
        stress_window_size: int = 5,
        sustain_threshold: float = 0.4,
        max_segment_duration: float = None,
        phonetic_analyzer: PhoneticAnalyzer = None
    ):
        """
        Initialize the formatter with configurable thresholds.
        
        Args:
            default_segment_duration: Default duration for the last segment
                                      (when no following onset exists).
            stress_threshold: Multiplier for local average to detect stress.
                              Segment is stressed if RMS > threshold * local_avg.
            stress_window_size: Number of neighboring segments to consider
                                for local average calculation.
            sustain_threshold: Duration in seconds above which a segment
                               is considered sustained (long vowel).
            max_segment_duration: Maximum segment duration before automatic
                                  splitting. If None, loads from config.
            phonetic_analyzer: PhoneticAnalyzer instance for IPA extraction.
                               If None, phonetic analysis will be skipped.
        """
        self.default_segment_duration = default_segment_duration
        self.stress_threshold = stress_threshold
        self.stress_window_size = stress_window_size
        self.sustain_threshold = sustain_threshold
        self.phonetic_analyzer = phonetic_analyzer
        
        # Load max_segment_duration from config if not provided
        if max_segment_duration is None:
            try:
                from config import config
                self.max_segment_duration = config.MAX_SEGMENT_DURATION
            except ImportError:
                self.max_segment_duration = 0.5
        else:
            self.max_segment_duration = max_segment_duration
    
    def _find_energy_valleys(
        self,
        y: np.ndarray,
        sr: int,
        segment_start: float,
        segment_end: float,
        min_valley_spacing: float = 0.08,
        min_valley_depth: float = 0.3
    ) -> list[float]:
        """
        Find local energy minima within a segment for splitting.
        
        Only returns valleys where energy drops SIGNIFICANTLY, avoiding
        splits during sustained notes where energy stays relatively flat.
        
        Args:
            y: Audio signal.
            sr: Sample rate.
            segment_start: Segment start time in seconds.
            segment_end: Segment end time in seconds.
            min_valley_spacing: Minimum time between valleys.
            min_valley_depth: Minimum relative depth of valley (0.0-1.0).
                              A value of 0.3 means energy must drop by at least
                              30% compared to surrounding peaks to be considered
                              a valid split point. This prevents splitting
                              sustained notes with flat energy profiles.
            
        Returns:
            List of valley times (potential split points).
        """
        start_sample = int(segment_start * sr)
        end_sample = int(segment_end * sr)
        
        # Clamp to valid range
        start_sample = max(0, start_sample)
        end_sample = min(len(y), end_sample)
        
        if end_sample <= start_sample:
            return []
        
        segment_audio = y[start_sample:end_sample]
        
        # Compute RMS energy with small hop for fine resolution
        hop_length = 256
        rms = librosa.feature.rms(y=segment_audio, hop_length=hop_length)[0]
        
        if len(rms) < 5:  # Need enough frames to detect valleys
            return []
        
        # Normalize RMS
        rms_max = np.max(rms) + 1e-10
        rms_normalized = rms / rms_max
        
        # Find local minima (valleys) with depth checking
        valleys = []
        min_distance_frames = int(min_valley_spacing * sr / hop_length)
        window_size = max(3, min_distance_frames // 2)  # Window for local peak detection
        
        last_valley_idx = -min_distance_frames
        for i in range(window_size, len(rms_normalized) - window_size):
            if i - last_valley_idx < min_distance_frames:
                continue
            
            # Check if local minimum
            if not (rms_normalized[i] < rms_normalized[i-1] and 
                    rms_normalized[i] < rms_normalized[i+1]):
                continue
            
            # Find local peaks on either side to measure valley depth
            left_peak = np.max(rms_normalized[max(0, i-window_size):i])
            right_peak = np.max(rms_normalized[i+1:min(len(rms_normalized), i+window_size+1)])
            surrounding_avg = (left_peak + right_peak) / 2
            
            # Calculate valley depth relative to surrounding peaks
            valley_depth = surrounding_avg - rms_normalized[i]
            
            # Only accept valleys with significant depth (Issue #3: sustained note handling)
            # If energy stays flat, valley_depth will be small -> don't split
            if valley_depth < min_valley_depth:
                continue  # Flat valley = sustained note, don't split
            
            # Also require absolute energy drop below 50% of max
            if rms_normalized[i] >= 0.5:
                continue
            
            # Convert frame to time (relative to segment start)
            valley_time = segment_start + (i * hop_length / sr)
            
            # Only include valleys that are well inside the segment
            margin = 0.05  # 50ms from edges
            if segment_start + margin < valley_time < segment_end - margin:
                valleys.append(valley_time)
                last_valley_idx = i
        
        return valleys
    
    def _split_long_segments(
        self,
        onset_times: list[float],
        durations: list[float],
        y: np.ndarray,
        sr: int
    ) -> tuple[list[float], list[float]]:
        """
        Split segments longer than max_segment_duration at energy valleys.
        
        Prevents multi-syllable segments by subdividing long segments
        at natural break points (energy valleys).
        
        Args:
            onset_times: Original onset times.
            durations: Original segment durations.
            y: Audio signal for energy analysis.
            sr: Sample rate.
            
        Returns:
            Tuple of (new_onset_times, new_durations) with splits applied.
        """
        if y is None:
            return onset_times, durations
        
        new_onsets = []
        new_durations = []
        split_count = 0
        
        for onset, duration in zip(onset_times, durations):
            if duration <= self.max_segment_duration:
                # Segment is short enough, keep as-is
                new_onsets.append(onset)
                new_durations.append(duration)
            else:
                # Segment is too long, try to split at energy valleys
                segment_end = onset + duration
                valleys = self._find_energy_valleys(y, sr, onset, segment_end)
                
                if not valleys:
                    # No good split points found, keep original
                    new_onsets.append(onset)
                    new_durations.append(duration)
                else:
                    # Split segment at valleys
                    all_points = [onset] + valleys + [segment_end]
                    
                    for i in range(len(all_points) - 1):
                        sub_onset = all_points[i]
                        sub_duration = all_points[i + 1] - sub_onset
                        new_onsets.append(sub_onset)
                        new_durations.append(sub_duration)
                    
                    split_count += 1
        
        if split_count > 0:
            print(f"[PivotFormatter] Split {split_count} long segments -> {len(new_onsets)} total segments")
        
        return new_onsets, new_durations
    
    def _filter_low_energy_segments(
        self,
        onset_times: list[float],
        durations: list[float],
        y: np.ndarray,
        sr: int,
        min_energy_ratio: float = 0.15,
        max_short_duration: float = 0.15
    ) -> tuple[list[float], list[float]]:
        """
        Filter out low-energy segments that are likely breath sounds or noise.
        
        Issue #2: The "Breath" Trap - prevents detecting breath intakes as syllables.
        
        A segment is filtered if BOTH conditions are met:
        1. Duration is short (< max_short_duration seconds)
        2. RMS energy is low (< min_energy_ratio of track's max energy)
        
        Long low-energy segments are kept (might be quiet speech).
        High-energy short segments are kept (might be consonant pops).
        
        Args:
            onset_times: Segment start times.
            durations: Segment durations.
            y: Audio signal.
            sr: Sample rate.
            min_energy_ratio: Minimum energy threshold relative to track max.
            max_short_duration: Duration threshold for "short" segments.
            
        Returns:
            Tuple of (filtered_onset_times, filtered_durations).
        """
        if y is None or len(onset_times) == 0:
            return onset_times, durations
        
        # Calculate global RMS max for reference
        global_rms = librosa.feature.rms(y=y)[0]
        global_max_rms = np.max(global_rms) + 1e-10
        energy_threshold = min_energy_ratio * global_max_rms
        
        filtered_onsets = []
        filtered_durations = []
        filtered_count = 0
        
        for onset, duration in zip(onset_times, durations):
            # Only filter short segments
            if duration < max_short_duration:
                # Calculate segment RMS
                start_sample = int(onset * sr)
                end_sample = int((onset + duration) * sr)
                start_sample = max(0, start_sample)
                end_sample = min(len(y), end_sample)
                
                if end_sample > start_sample:
                    segment_audio = y[start_sample:end_sample]
                    segment_rms = np.sqrt(np.mean(segment_audio ** 2))
                    
                    # Filter if energy is below threshold (likely breath/noise)
                    if segment_rms < energy_threshold:
                        filtered_count += 1
                        continue  # Skip this segment
            
            # Keep segment
            filtered_onsets.append(onset)
            filtered_durations.append(duration)
        
        if filtered_count > 0:
            print(f"[PivotFormatter] Filtered {filtered_count} low-energy segments (breaths/noise)")
        
        return filtered_onsets, filtered_durations
    
    def _calculate_segment_rms(
        self, 
        y: np.ndarray, 
        sr: int, 
        time_start: float, 
        duration: float
    ) -> float:
        """
        Calculate the RMS amplitude of an audio segment.
        
        Args:
            y: Audio signal array.
            sr: Sample rate.
            time_start: Segment start time in seconds.
            duration: Segment duration in seconds.
            
        Returns:
            RMS amplitude of the segment.
        """
        start_sample = int(time_start * sr)
        end_sample = int((time_start + duration) * sr)
        
        # Clamp to valid range
        start_sample = max(0, start_sample)
        end_sample = min(len(y), end_sample)
        
        if end_sample <= start_sample:
            return 0.0
        
        segment_audio = y[start_sample:end_sample]
        
        # Calculate RMS (Root Mean Square)
        rms = np.sqrt(np.mean(segment_audio ** 2))
        return float(rms)
    
    def _detect_stress(
        self, 
        rms_values: list[float]
    ) -> list[bool]:
        """
        Detect stressed segments based on RMS amplitude.
        
        A segment is stressed if its RMS exceeds the local average by
        the configured threshold (e.g., > 1.2x local average).
        
        Args:
            rms_values: List of RMS amplitudes for each segment.
            
        Returns:
            List of booleans indicating stress for each segment.
        """
        if not rms_values:
            return []
        
        n = len(rms_values)
        half_window = self.stress_window_size // 2
        stressed = []
        
        for i in range(n):
            # Calculate local window bounds
            window_start = max(0, i - half_window)
            window_end = min(n, i + half_window + 1)
            
            # Get local neighborhood RMS values
            local_rms = rms_values[window_start:window_end]
            local_avg = np.mean(local_rms) if local_rms else 0.0
            
            # Avoid division by zero; if no signal, not stressed
            if local_avg == 0:
                stressed.append(False)
            else:
                # Stressed if RMS exceeds threshold * local average
                is_stressed = bool(rms_values[i] > (self.stress_threshold * local_avg))
                stressed.append(is_stressed)
        
        return stressed
    
    def _detect_sustain(self, durations: list[float]) -> list[bool]:
        """
        Detect sustained notes based on duration.
        
        A segment is sustained if its duration exceeds the configured
        threshold (default: 0.4 seconds).
        
        Args:
            durations: List of segment durations in seconds.
            
        Returns:
            List of booleans indicating sustain for each segment.
        """
        return [bool(d > self.sustain_threshold) for d in durations]
    
    def _detect_pitch(
        self,
        y: np.ndarray,
        sr: int,
        onset_times: list[float],
        durations: list[float]
    ) -> list[str]:
        """
        Detect pitch contour for each segment using pYIN algorithm.
        
        Pitch is categorized as:
        - "low": median frequency < 150 Hz (bass range)
        - "mid": median frequency 150-300 Hz (typical speech)
        - "high": median frequency > 300 Hz (higher vocals)
        - "rising": start pitch < end pitch by > 20%
        - "falling": start pitch > end pitch by > 20%
        
        Args:
            y: Audio signal array.
            sr: Sample rate.
            onset_times: List of segment start times.
            durations: List of segment durations.
            
        Returns:
            List of pitch contour strings for each segment.
        """
        if y is None or len(y) == 0:
            return ["mid"] * len(onset_times)
        
        # Use pYIN for pitch tracking (more accurate than piptrack for vocals)
        # fmin=50 for low vocals, fmax=500 for high vocals
        try:
            f0, voiced_flag, voiced_probs = librosa.pyin(
                y, 
                fmin=librosa.note_to_hz('C2'),  # ~65 Hz
                fmax=librosa.note_to_hz('C6'),  # ~1047 Hz
                sr=sr
            )
        except Exception:
            # Fallback if pyin fails
            return ["mid"] * len(onset_times)
        
        # Convert frames to time
        times = librosa.times_like(f0, sr=sr)
        
        pitch_contours = []
        
        for onset_time, duration in zip(onset_times, durations):
            end_time = onset_time + duration
            
            # Find pitch values within this segment
            mask = (times >= onset_time) & (times < end_time)
            segment_pitches = f0[mask]
            
            # Filter out NaN (unvoiced frames)
            valid_pitches = segment_pitches[~np.isnan(segment_pitches)]
            
            if len(valid_pitches) == 0:
                pitch_contours.append("mid")
                continue
            
            median_pitch = np.median(valid_pitches)
            
            # Check for rising/falling contour
            if len(valid_pitches) >= 3:
                start_pitch = np.mean(valid_pitches[:len(valid_pitches)//3])
                end_pitch = np.mean(valid_pitches[-len(valid_pitches)//3:])
                
                if not np.isnan(start_pitch) and not np.isnan(end_pitch):
                    ratio = end_pitch / start_pitch if start_pitch > 0 else 1.0
                    
                    if ratio > 1.2:  # >20% increase
                        pitch_contours.append("rising")
                        continue
                    elif ratio < 0.8:  # >20% decrease
                        pitch_contours.append("falling")
                        continue
            
            # Categorize by absolute pitch
            if median_pitch < 150:
                pitch_contours.append("low")
            elif median_pitch > 300:
                pitch_contours.append("high")
            else:
                pitch_contours.append("mid")
        
        return pitch_contours
    
    def format(self, analysis: AnalysisResult) -> PivotJSON:
        """
        Format analysis results into Pivot JSON with stress/sustain/pitch detection.
        
        Includes automatic splitting of long segments at energy valleys.
        
        Args:
            analysis: AnalysisResult from LibrosaAnalyzer.
            
        Returns:
            PivotJSON object ready for serialization.
        """
        onset_times = analysis.onset_times
        y = analysis.audio_signal
        sr = analysis.sample_rate
        
        # First pass: calculate durations
        durations = []
        for i, onset_time in enumerate(onset_times):
            if i < len(onset_times) - 1:
                duration = onset_times[i + 1] - onset_time
            else:
                duration = self.default_segment_duration
            durations.append(duration)
        
        # Split long segments at energy valleys (prevents multi-syllable segments)
        onset_times, durations = self._split_long_segments(onset_times, durations, y, sr)
        
        # Filter out low-energy segments (Issue #2: breaths and noise)
        onset_times, durations = self._filter_low_energy_segments(onset_times, durations, y, sr)
        
        # Calculate RMS amplitude for each segment
        rms_values = []
        if y is not None:
            for i, onset_time in enumerate(onset_times):
                rms = self._calculate_segment_rms(y, sr, onset_time, durations[i])
                rms_values.append(rms)
        else:
            # No audio signal available, all RMS = 0
            rms_values = [0.0] * len(onset_times)
        
        # Detect stress, sustain, and pitch
        stressed = self._detect_stress(rms_values)
        sustained = self._detect_sustain(durations)
        pitch_contours = self._detect_pitch(y, sr, onset_times, durations)
        
        # Detect phonemes via Allosaurus (if analyzer is available)
        if self.phonetic_analyzer is not None and y is not None:
            audio_phonemes = self.phonetic_analyzer.analyze_segments(y, sr, onset_times, durations)
        else:
            audio_phonemes = [""] * len(onset_times)
        
        # Build segments with all detected features
        segments = []
        for i, onset_time in enumerate(onset_times):
            segments.append(Segment(
                time_start=onset_time,
                duration=durations[i],
                is_stressed=stressed[i] if i < len(stressed) else False,
                is_sustained=sustained[i] if i < len(sustained) else False,
                pitch_contour=pitch_contours[i] if i < len(pitch_contours) else "mid",
                audio_phonemes=audio_phonemes[i] if i < len(audio_phonemes) else ""
            ))
        
        # Create single block containing all segments (MVP approach)
        # Phase 2 can add bar detection to split into multiple blocks
        block = Block(
            id=1,
            syllable_target=len(segments),
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
    
    def __init__(self, mock_mode: bool = False, phonetic_enabled: bool = True):
        """
        Initialize the audio engine.
        
        Args:
            mock_mode: If True, skip Demucs processing (development mode).
            phonetic_enabled: If True, enable Allosaurus phonetic analysis.
                              Set to False for faster processing without IPA.
        """
        self.demucs = DemucsProcessor(mock_mode=mock_mode)
        self.analyzer = LibrosaAnalyzer()
        
        # Initialize phonetic analyzer if enabled
        self.phonetic_analyzer = PhoneticAnalyzer(enabled=phonetic_enabled)
        self.formatter = PivotFormatter(phonetic_analyzer=self.phonetic_analyzer)
        
        self.mock_mode = mock_mode
        self.phonetic_enabled = phonetic_enabled
    
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
