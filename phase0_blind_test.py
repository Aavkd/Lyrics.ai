"""
Flow-to-Lyrics: Phase 0 Blind Test
===================================
Validates the lyric generation engine without a frontend.

Strategy: "Generate Many, Filter Best"
- We do NOT trust the LLM to count syllables perfectly.
- We generate batches of variations and filter them using deterministic validation.

Tech: g2p_en (Grapheme-to-Phoneme) for phonetic syllable counting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from g2p_en import G2p


# =============================================================================
# SYLLABLE VALIDATOR
# =============================================================================

class SyllableValidator:
    """
    Validates syllable counts using phonetic analysis (g2p_en).
    
    Why g2p_en?
    -----------
    - We need to count AUDITORY syllables, not orthographic ones.
    - "Fire" looks like 2 syllables but sounds like 2: F AY1 ER0
    - "Every" looks like 3 syllables but sounds like 2: EH1 V R IY0
    - Hyphenation libraries (pyphen) count visual syllables, which is wrong for rap/singing.
    
    How it works:
    -------------
    1. Convert text to phonemes using g2p_en (CMU Dict based).
    2. Count stress markers (digits 0, 1, 2) which are attached to vowel nuclei.
    3. Each stress marker = 1 syllable.
    
    Example:
        "I got fire" -> ['AY1', 'G', 'AA1', 'T', 'F', 'AY1', 'ER0']
        Stress markers: AY1 (1), AA1 (1), AY1 (1), ER0 (1) = 4 syllables
    """
    
    # Regex to find stress markers (digits 0, 1, 2) in phonemes
    STRESS_PATTERN = re.compile(r'[012]')
    
    def __init__(self) -> None:
        """Initialize the G2P converter."""
        self._g2p = G2p()
    
    def text_to_phonemes(self, text: str) -> list[str]:
        """
        Convert text to a list of phonemes.
        
        Args:
            text: Input text string.
            
        Returns:
            List of phoneme strings (e.g., ['AY1', 'G', 'AA1', 'T']).
        """
        return self._g2p(text)
    
    def count_syllables(self, text: str) -> tuple[int, list[str]]:
        """
        Count the number of syllables in the given text.
        
        Syllables are counted by detecting vowel nuclei with stress markers
        (digits 0, 1, 2 attached to vowel phonemes).
        
        Args:
            text: Input text string.
            
        Returns:
            Tuple of (syllable_count, phonemes_list).
        """
        phonemes = self.text_to_phonemes(text)
        
        # Count phonemes that contain stress markers (0, 1, or 2)
        # These indicate vowel nuclei, which correspond to syllables
        syllable_count = sum(
            1 for phoneme in phonemes 
            if self.STRESS_PATTERN.search(phoneme)
        )
        
        return syllable_count, phonemes
    
    def validate(self, text: str, target_syllables: int) -> ValidationResult:
        """
        Validate if text matches target syllable count.
        
        Args:
            text: Input text string.
            target_syllables: Expected syllable count.
            
        Returns:
            ValidationResult with match status and details.
        """
        actual_count, phonemes = self.count_syllables(text)
        
        return ValidationResult(
            text=text,
            target_syllables=target_syllables,
            actual_syllables=actual_count,
            is_valid=actual_count == target_syllables,
            phonemes=phonemes
        )


@dataclass
class ValidationResult:
    """Result of syllable validation."""
    text: str
    target_syllables: int
    actual_syllables: int
    is_valid: bool
    phonemes: list[str]
    
    def __str__(self) -> str:
        status = "✓" if self.is_valid else "✗"
        return (
            f"{status} [{self.actual_syllables}/{self.target_syllables}] "
            f"\"{self.text}\""
        )


# =============================================================================
# LYRIC GENERATOR (MOCK)
# =============================================================================

class LyricGenerator:
    """
    Mock LLM interface for generating lyric candidates.
    
    In production, this would call an actual LLM API (e.g., GPT-4, Llama-3).
    For Phase 0 blind test, we return pre-defined mock data to test the
    validation pipeline.
    """
    
    # Mock candidate pool organized by approximate syllable targets
    # Some are intentionally "wrong" to test the filter
    MOCK_CANDIDATES: dict[str, list[str]] = {
        "8_syllables": [
            "I rise above the city lights",      # 8 syllables
            "My dreams are burning way too bright",  # 8 syllables
            "We running through the midnight streets",  # 8 syllables
            "Fire in my soul tonight",            # 6 syllables (intentionally wrong)
            "Breaking chains and taking flight yeah",  # 8 syllables
        ],
        "10_syllables": [
            "We rise above the noise and take the crown tonight",  # 10 syllables
            "I'm breaking every chain that holds me down now",     # 10 syllables  
            "My vision crystal clear",                             # 5 syllables (intentionally wrong)
            "The city never sleeps",                               # 5 syllables (wrong)
            "I climb so high",                                     # 3 syllables (wrong)
        ],
        "6_syllables": [
            "Fire in my veins",                    # 5 syllables (wrong)
            "Legends never die young",             # 5 syllables (wrong)
            "I'm ready for the fight",             # 6 syllables
            "Breaking out the cage now",           # 5 syllables (wrong)
            "Money on my mind now",                # 5 syllables (wrong)
        ],
        "generic": [
            "Yeah I'm on the way up now",          # 7 syllables
            "Can't nobody stop me",                # 5 syllables
            "Living life without regret",          # 7 syllables
            "This the anthem of the streets",      # 7 syllables
            "We gonna make it to the top",         # 8 syllables
        ]
    }
    
    def generate_line(
        self, 
        target_syllables: int, 
        context: str = ""
    ) -> list[str]:
        """
        Generate candidate lines for the given syllable target.
        
        In a real implementation, this would:
        1. Call an LLM with a structured prompt
        2. Request 5 variations in parallel
        3. Return raw candidates for validation
        
        Args:
            target_syllables: Target syllable count for the line.
            context: Thematic context or previous lines (unused in mock).
            
        Returns:
            List of 5 candidate strings.
        """
        # Select mock candidates based on target
        key = f"{target_syllables}_syllables"
        if key in self.MOCK_CANDIDATES:
            return self.MOCK_CANDIDATES[key].copy()
        else:
            return self.MOCK_CANDIDATES["generic"].copy()


# =============================================================================
# PIPELINE WORKFLOW
# =============================================================================

@dataclass
class LineResult:
    """Result for a single line in the pipeline."""
    target_syllables: int
    selected_line: Optional[str]
    actual_syllables: Optional[int]
    phonemes: Optional[list[str]]
    success: bool
    all_candidates: list[ValidationResult]


def run_pipeline(syllable_targets: list[int]) -> list[LineResult]:
    """
    Run the "Generate Many, Filter Best" pipeline.
    
    Workflow:
    1. For each target syllable count
    2. Generate 5 candidates via LyricGenerator
    3. Validate each candidate via SyllableValidator
    4. Select first candidate where actual == target
    5. If none match, mark as retry needed
    
    Args:
        syllable_targets: List of target syllable counts.
        
    Returns:
        List of LineResult objects.
    """
    validator = SyllableValidator()
    generator = LyricGenerator()
    
    results: list[LineResult] = []
    
    for target in syllable_targets:
        # Step 1: Generate candidates
        candidates = generator.generate_line(target, context="trap theme")
        
        # Step 2: Validate all candidates
        validations = [
            validator.validate(candidate, target) 
            for candidate in candidates
        ]
        
        # Step 3: Find first valid match
        valid_matches = [v for v in validations if v.is_valid]
        
        if valid_matches:
            selected = valid_matches[0]
            results.append(LineResult(
                target_syllables=target,
                selected_line=selected.text,
                actual_syllables=selected.actual_syllables,
                phonemes=selected.phonemes,
                success=True,
                all_candidates=validations
            ))
        else:
            # No match found - would trigger retry in production
            results.append(LineResult(
                target_syllables=target,
                selected_line=None,
                actual_syllables=None,
                phonemes=None,
                success=False,
                all_candidates=validations
            ))
    
    return results


def print_report(results: list[LineResult]) -> None:
    """
    Print a structured report of the pipeline results.
    
    Args:
        results: List of LineResult objects from the pipeline.
    """
    print("\n" + "=" * 70)
    print("  FLOW-TO-LYRICS: PHASE 0 BLIND TEST REPORT")
    print("=" * 70)
    
    success_count = sum(1 for r in results if r.success)
    total_count = len(results)
    
    print(f"\n  Summary: {success_count}/{total_count} lines matched target syllables")
    print(f"  Success Rate: {success_count/total_count*100:.1f}%")
    print("-" * 70)
    
    for i, result in enumerate(results, 1):
        print(f"\n  LINE {i}")
        print(f"  {'─' * 66}")
        print(f"  Target Syllables: {result.target_syllables}")
        
        if result.success:
            print(f"  Status: ✓ MATCHED")
            print(f"  Selected: \"{result.selected_line}\"")
            print(f"  Actual Count: {result.actual_syllables}")
            print(f"  Phonemes: {' '.join(result.phonemes)}")
        else:
            print(f"  Status: ⚠ RETRY NEEDED (no candidates matched)")
        
        # Show all candidates for debugging
        print(f"\n  All Candidates:")
        for j, v in enumerate(result.all_candidates, 1):
            status = "✓" if v.is_valid else "✗"
            print(f"    {j}. {status} [{v.actual_syllables}] \"{v.text}\"")
    
    print("\n" + "=" * 70)
    print("  END OF REPORT")
    print("=" * 70 + "\n")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main() -> None:
    """Main entry point for Phase 0 blind test."""
    
    print("\n🎤 Flow-to-Lyrics: Phase 0 Blind Test")
    print("━" * 50)
    print("Strategy: 'Generate Many, Filter Best'")
    print("Validator: g2p_en (Phonetic Syllable Counting)")
    print("━" * 50)
    
    # Example syllable targets (typical 4-bar structure)
    syllable_targets = [8, 10, 8, 10]
    
    print(f"\n📋 Input Syllable Targets: {syllable_targets}")
    print("🔄 Running pipeline...")
    
    # Run the pipeline
    results = run_pipeline(syllable_targets)
    
    # Print structured report
    print_report(results)
    
    # Demo: Show phonetic counting for specific words
    print("\n📚 PHONETIC COUNTING DEMO")
    print("-" * 50)
    
    validator = SyllableValidator()
    demo_words = ["Fire", "Every", "Supercalifragilistic", "Yeah", "Running"]
    
    for word in demo_words:
        count, phonemes = validator.count_syllables(word)
        print(f"  \"{word}\" → {count} syllables")
        print(f"    Phonemes: {' '.join(phonemes)}")
    
    print("\n✅ Phase 0 Blind Test Complete!")


if __name__ == "__main__":
    main()
