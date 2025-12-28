"""
Flow-to-Lyrics: Lyric Validator (The Gatekeeper)
=================================================
Step 4 of the Tech Roadmap - The "Gatekeeper"

This module provides strict validation of generated lyric candidates against
audio-derived constraints using phonetic analysis via g2p_en.

Key Features:
- Phonetic syllable counting (auditory, not orthographic)
- Stress pattern matching ("Groove Score")
- Binary validation (syllable count must match exactly)

Usage:
    validator = LyricValidator()
    result = validator.validate_line("Monster City", segments)
    print(f"Valid: {result.is_valid}, Score: {result.score}")
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from g2p_en import G2p

if TYPE_CHECKING:
    from audio_engine import Segment


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ValidationResult:
    """Result of lyric validation against audio constraints.
    
    Attributes:
        is_valid: True if syllable count matches exactly.
        score: Groove score between 0.0 and 1.0 (stress matching).
        reason: Human-readable explanation of the result.
        syllable_count: Actual syllable count of the text.
        phonemes: List of phonemes generated from the text.
        stress_markers: List of stress levels (0, 1, 2) extracted from phonemes.
    """
    is_valid: bool
    score: float
    reason: str
    syllable_count: int = 0
    phonemes: list[str] = None
    stress_markers: list[int] = None
    
    def __post_init__(self):
        if self.phonemes is None:
            self.phonemes = []
        if self.stress_markers is None:
            self.stress_markers = []


# =============================================================================
# LYRIC VALIDATOR
# =============================================================================

class LyricValidator:
    """
    Validates lyric candidates against audio-derived constraints.
    
    The "Gatekeeper" - ruthlessly filters candidates that don't match:
    1. Syllable count must match segment count exactly
    2. Stress patterns should align (scored 0.0 to 1.0)
    
    Uses g2p_en (Grapheme-to-Phoneme) for phonetic analysis:
    - "Rhythm" -> R IH1 DH AH0 M (2 syllables: IH1=stressed, AH0=unstressed)
    - "Monster" -> M AA1 N S T ER0 (2 syllables: AA1=stressed, ER0=unstressed)
    
    Stress markers in phonemes:
    - 0 = Unstressed
    - 1 = Primary stress
    - 2 = Secondary stress
    """
    
    # Regex to extract stress markers (0, 1, 2) from phonemes
    STRESS_PATTERN = re.compile(r'[012]')
    
    def __init__(self):
        """Initialize the validator with g2p_en converter."""
        self._g2p = G2p()
    
    def text_to_phonemes(self, text: str) -> list[str]:
        """
        Convert text to a list of phonemes.
        
        Args:
            text: Input text string.
            
        Returns:
            List of phoneme strings (e.g., ['M', 'AA1', 'N', 'S', 'T', 'ER0']).
        """
        return self._g2p(text)
    
    def extract_stress_markers(self, phonemes: list[str]) -> list[int]:
        """
        Extract stress levels from phonemes.
        
        Stress markers in CMU Dict phonemes:
        - 0 = Unstressed vowel
        - 1 = Primary stress
        - 2 = Secondary stress
        
        Args:
            phonemes: List of phoneme strings from g2p_en.
            
        Returns:
            List of stress levels (0, 1, or 2) for each syllable.
            
        Example:
            ["M", "AA1", "N", "S", "T", "ER0"] -> [1, 0]
            (AA1 has stress 1, ER0 has stress 0)
        """
        stress_markers = []
        for phoneme in phonemes:
            match = self.STRESS_PATTERN.search(phoneme)
            if match:
                stress_markers.append(int(match.group()))
        return stress_markers
    
    def count_syllables(self, text: str) -> tuple[int, list[str], list[int]]:
        """
        Count syllables and extract stress pattern from text.
        
        Syllables are counted by detecting vowel nuclei with stress markers
        (digits 0, 1, 2 attached to vowel phonemes).
        
        Args:
            text: Input text string.
            
        Returns:
            Tuple of (syllable_count, phonemes_list, stress_markers).
        """
        phonemes = self.text_to_phonemes(text)
        stress_markers = self.extract_stress_markers(phonemes)
        syllable_count = len(stress_markers)
        
        return syllable_count, phonemes, stress_markers
    
    def calculate_groove_score(
        self, 
        text_stress: list[int], 
        audio_stress: list[bool]
    ) -> float:
        """
        Calculate the "Groove Score" - how well text stress matches audio stress.
        
        IMPROVED Scoring Logic (Phase 1 calibration):
        - +2 points if both audio and text are stressed (hitting the beat!)
        - +1 point if both are unstressed (consistent flow)
        - +0.5 points for secondary stress (2) on stressed audio
        - 0 points for mismatches (missing the beat is neutral, not actively bad)
        
        The weighting ensures stressed beat alignment matters 2x more than
        unstressed alignment, addressing the "0.29 score" issue from testing.
        
        Args:
            text_stress: List of stress levels [0, 1, 2] from phonemes.
            audio_stress: List of booleans from audio segments (is_stressed).
            
        Returns:
            Normalized score between 0.0 and 1.0.
            Returns 0.0 if lists have different lengths.
        """
        if len(text_stress) != len(audio_stress):
            return 0.0
        
        if not text_stress:
            return 0.0
        
        points = 0.0
        # Max points: 2 for each stressed + 1 for each unstressed
        stressed_count = sum(1 for s in audio_stress if s)
        unstressed_count = len(audio_stress) - stressed_count
        max_points = (stressed_count * 2) + unstressed_count
        
        if max_points == 0:
            return 0.0
        
        for text_s, audio_s in zip(text_stress, audio_stress):
            if audio_s:
                # Audio segment is stressed -> text should have primary stress (1)
                if text_s == 1:
                    points += 2  # Double reward for hitting stressed beats
                elif text_s == 2:
                    # Secondary stress is a partial match
                    points += 0.5
                # Mismatch (text_s == 0) gets 0 points
            else:
                # Audio segment is unstressed -> text should be unstressed (0)
                if text_s == 0:
                    points += 1
                # Stressed text on unstressed audio is neutral (0 points)
        
        return points / max_points
    
    def validate_line(
        self, 
        text: str, 
        target_segments: list
    ) -> ValidationResult:
        """
        Validate a lyric line against target audio segments.
        
        Validation steps:
        1. Count syllables in text using phonetic analysis
        2. Check if syllable count matches segment count (strict)
        3. If valid, calculate groove score from stress patterns
        
        Args:
            text: Lyric line to validate.
            target_segments: List of Segment objects from audio analysis.
                             Each segment has is_stressed: bool attribute.
            
        Returns:
            ValidationResult with validation details and score.
        """
        # Step 1: Phonetic analysis
        syllable_count, phonemes, stress_markers = self.count_syllables(text)
        target_count = len(target_segments)
        
        # Step 2: Strict syllable count check
        if syllable_count != target_count:
            return ValidationResult(
                is_valid=False,
                score=0.0,
                reason=f"Syllable mismatch: got {syllable_count}, expected {target_count}",
                syllable_count=syllable_count,
                phonemes=phonemes,
                stress_markers=stress_markers
            )
        
        # Step 3: Extract audio stress pattern
        audio_stress = [seg.is_stressed for seg in target_segments]
        
        # Step 4: Calculate groove score
        groove_score = self.calculate_groove_score(stress_markers, audio_stress)
        
        return ValidationResult(
            is_valid=True,
            score=groove_score,
            reason=f"Valid! Groove score: {groove_score:.2f}",
            syllable_count=syllable_count,
            phonemes=phonemes,
            stress_markers=stress_markers
        )
    
    def validate_candidates(
        self, 
        candidates: list[str], 
        target_segments: list
    ) -> list[ValidationResult]:
        """
        Validate multiple candidates and return all results.
        
        Args:
            candidates: List of lyric line candidates.
            target_segments: List of Segment objects from audio analysis.
            
        Returns:
            List of ValidationResult objects, one per candidate.
        """
        return [
            self.validate_line(candidate, target_segments) 
            for candidate in candidates
        ]
    
    def get_best_candidate(
        self, 
        candidates: list[str], 
        target_segments: list,
        min_score: float = 0.0
    ) -> tuple[str | None, ValidationResult | None]:
        """
        Find the best valid candidate by groove score.
        
        Args:
            candidates: List of lyric line candidates.
            target_segments: List of Segment objects from audio analysis.
            min_score: Minimum groove score to accept (default: 0.0).
            
        Returns:
            Tuple of (best_text, best_result) or (None, None) if no valid candidate.
        """
        results = self.validate_candidates(candidates, target_segments)
        
        # Filter valid candidates above min_score
        valid_results = [
            (candidates[i], result) 
            for i, result in enumerate(results) 
            if result.is_valid and result.score >= min_score
        ]
        
        if not valid_results:
            return None, None
        
        # Sort by score (descending)
        valid_results.sort(key=lambda x: x[1].score, reverse=True)
        
        return valid_results[0]


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    from audio_engine import Segment
    
    print("\n🛡️ Flow-to-Lyrics: Lyric Validator (The Gatekeeper)")
    print("=" * 60)
    
    validator = LyricValidator()
    
    # Demo: Phonetic analysis
    print("\n📚 PHONETIC ANALYSIS DEMO")
    print("-" * 60)
    
    demo_words = ["Rhythm", "Monster", "City", "Power", "Fire"]
    for word in demo_words:
        count, phonemes, stress = validator.count_syllables(word)
        print(f"  \"{word}\" -> {count} syllables")
        print(f"    Phonemes: {' '.join(phonemes)}")
        print(f"    Stress: {stress}")
    
    # Demo: Validation against mock segments
    print("\n⚖️ VALIDATION DEMO")
    print("-" * 60)
    
    # Create mock segments: DA-da-DA-da pattern
    test_segments = [
        Segment(0.0, 0.2, is_stressed=True),   # DA
        Segment(0.2, 0.2, is_stressed=False),  # da
        Segment(0.4, 0.2, is_stressed=True),   # DA
        Segment(0.6, 0.2, is_stressed=False),  # da
    ]
    
    test_lines = [
        "Monster City",           # 4 syllables, good stress match
        "The machine",            # 3 syllables, wrong count
        "Power moving",           # 4 syllables
        "I go crazy now"          # 5 syllables, wrong count
    ]
    
    print(f"  Target: 4 segments (DA-da-DA-da)")
    print()
    
    for line in test_lines:
        result = validator.validate_line(line, test_segments)
        status = "✓" if result.is_valid else "✗"
        print(f"  {status} \"{line}\"")
        print(f"      {result.reason}")
        if result.is_valid:
            print(f"      Stress match: {result.stress_markers}")
    
    print("\n✅ Validator test complete!")
