"""
Flow-to-Lyrics: Prompt Engine
=============================
Step 2 of the Tech Roadmap - The "Translator"

This module translates PivotJSON audio constraints into structured text prompts
optimized for Ministral-3b LLM lyric generation.

Key Features:
- External template loading from .md files
- Stress pattern conversion (bool array -> "DA-da-DA" notation)
- Sustain constraint generation (open vowel suggestions)
- JSON output format for "Generate Many" strategy
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from audio_engine import Block, PivotJSON, Segment


class PromptEngine:
    """
    Translates PivotJSON audio analysis into LLM-ready prompts.
    
    Usage:
        engine = PromptEngine(template_dir="prompts")
        system_msg, user_msg = engine.construct_prompt(pivot_json)
    """
    
    # Jinja2-style placeholder pattern
    PLACEHOLDER_PATTERN = re.compile(r'\{\{(\w+)\}\}')
    
    def __init__(self, template_dir: str = "prompts", candidate_count: int = 5):
        """
        Initialize the Prompt Engine.
        
        Args:
            template_dir: Directory containing .md template files.
            candidate_count: Number of candidates to request from LLM.
        """
        self.template_dir = Path(template_dir)
        self.candidate_count = candidate_count
        
        # Load templates on initialization
        self._system_template = self._load_template("system_instruction.md")
        self._user_template = self._load_template("user_template.md")
    
    def _load_template(self, filename: str) -> str:
        """
        Load a markdown template file.
        
        Args:
            filename: Name of the template file (e.g., "system_instruction.md").
            
        Returns:
            Template content as string.
            
        Raises:
            FileNotFoundError: If template file doesn't exist.
        """
        template_path = self.template_dir / filename
        
        if not template_path.exists():
            raise FileNotFoundError(
                f"Template not found: {template_path}\n"
                f"Expected templates in: {self.template_dir.absolute()}"
            )
        
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _convert_stress_to_pattern(self, stressed_flags: list[bool]) -> str:
        """
        Convert stress boolean array to human-readable pattern.
        
        Args:
            stressed_flags: List of booleans [True, False, True, ...].
            
        Returns:
            Pattern string like "DA-da-DA" or "1-0-1".
        
        Examples:
            [True, False, True] -> "DA-da-DA"
            [False, True, False, True] -> "da-DA-da-DA"
        """
        if not stressed_flags:
            return ""
        
        pattern_parts = []
        for is_stressed in stressed_flags:
            pattern_parts.append("DA" if is_stressed else "da")
        
        return "-".join(pattern_parts)
    
    def _generate_sustain_constraints(self, segments: list) -> str:
        """
        Generate text constraints for sustained syllables.
        
        Args:
            segments: List of Segment objects with is_sustained flag.
            
        Returns:
            Constraint text like "Syllable 5 is long (sustained), use open vowels."
        
        Examples:
            If segment[4].is_sustained = True:
            -> "Syllable 5 is long (sustained), use open vowels like 'fly', 'go', 'day'."
        """
        sustained_indices = []
        
        for i, segment in enumerate(segments):
            if segment.is_sustained:
                # 1-indexed for human readability
                sustained_indices.append(i + 1)
        
        if not sustained_indices:
            return "No sustained notes. All syllables are short."
        
        constraints = []
        for idx in sustained_indices:
            constraints.append(
                f"Syllable {idx} is long (sustained), use open vowels like 'fly', 'go', 'day', 'way', 'sky'."
            )
        
        return "\n".join(constraints)
    
    def _generate_pitch_guidance(self, segments: list) -> str:
        """
        Generate melodic guidance from pitch contours.
        
        Args:
            segments: List of Segment objects with pitch_contour field.
            
        Returns:
            Natural language guidance for the LLM based on pitch patterns.
            
        Examples:
            - "Segment 2 is **high-pitch**. Consider open vowels (O, A, E)."
            - "Segment 4 has a **rising** melody. Build energy into the word."
        """
        if not segments:
            return "No pitch data available."
        
        # Check if segments have pitch_contour attribute
        if not hasattr(segments[0], 'pitch_contour'):
            return "Pitch analysis not available for this audio."
        
        guidance_lines = []
        
        for i, seg in enumerate(segments, 1):
            pitch = getattr(seg, 'pitch_contour', 'mid')
            
            if pitch == "high":
                guidance_lines.append(
                    f"- Syllable {i} is **high-pitch**. Use bright, open vowels (EE, AY, OH)."
                )
            elif pitch == "low":
                guidance_lines.append(
                    f"- Syllable {i} is **low-pitch**. Use deep vowels (OO, AW, O)."
                )
            elif pitch == "rising":
                guidance_lines.append(
                    f"- Syllable {i} **rises** in pitch. Build energy into the word."
                )
            elif pitch == "falling":
                guidance_lines.append(
                    f"- Syllable {i} **falls** in pitch. Use it for emphasis or resolution."
                )
            # "mid" is neutral, no special guidance needed
        
        if not guidance_lines:
            return "All syllables are **mid-pitch**. Standard syllable placement."
        
        return "\n".join(guidance_lines)
    
    def _generate_phonetic_hints(self, segments: list) -> str:
        """
        Generate phonetic hints from audio_phonemes for sound-alike matching.
        
        Args:
            segments: List of Segment objects with audio_phonemes field.
            
        Returns:
            Formatted string with phonetic hints for the LLM.
            
        Examples:
            - "Syllable 1 sounds like: /b a/ → try words with 'ba' sound (bad, back, bat)"
            - "Syllable 3 sounds like: /m ʌ n/ → try 'man', 'money', 'month'"
        """
        if not segments:
            return "No phonetic data available."
        
        # Check if segments have audio_phonemes attribute
        if not hasattr(segments[0], 'audio_phonemes'):
            return "Phonetic analysis not available for this audio."
        
        hints = []
        
        for i, seg in enumerate(segments, 1):
            phonemes = getattr(seg, 'audio_phonemes', '')
            
            if phonemes and phonemes.strip():
                # Format the IPA phonemes for display
                hints.append(
                    f"- Syllable {i} sounds like: **/{phonemes}/**"
                )
        
        if not hints:
            return "No clear phonetic patterns detected. Generate based on rhythm only."
        
        return "\n".join(hints)
    
    def _process_block(self, block) -> dict:
        """
        Convert a Block's data into LLM-friendly formats.
        
        Args:
            block: Block object containing segments with stress/sustain/pitch info.
            
        Returns:
            Dictionary with:
                - syllable_count: int
                - stress_pattern: str (e.g., "DA-da-DA-da-DA")
                - sustain_constraints: str (e.g., "Syllable 5 is long...")
                - pitch_guidance: str (melodic guidance for each segment)
        """
        segments = block.segments
        
        # Extract stress flags from segments
        stressed_flags = [seg.is_stressed for seg in segments]
        
        # Generate pattern and constraints
        stress_pattern = self._convert_stress_to_pattern(stressed_flags)
        sustain_constraints = self._generate_sustain_constraints(segments)
        pitch_guidance = self._generate_pitch_guidance(segments)
        phonetic_hints = self._generate_phonetic_hints(segments)
        
        return {
            "syllable_count": block.syllable_target,
            "stress_pattern": stress_pattern,
            "sustain_constraints": sustain_constraints,
            "pitch_guidance": pitch_guidance,
            "phonetic_hints": phonetic_hints,
            "candidate_count": self.candidate_count
        }
    
    def _fill_template(self, template: str, values: dict) -> str:
        """
        Fill Jinja2-style placeholders in template.
        
        Args:
            template: Template string with {{placeholder}} syntax.
            values: Dictionary of placeholder -> value mappings.
            
        Returns:
            Filled template string.
        """
        def replace_placeholder(match):
            key = match.group(1)
            return str(values.get(key, match.group(0)))
        
        return self.PLACEHOLDER_PATTERN.sub(replace_placeholder, template)
    
    def construct_prompt(
        self, 
        pivot_json, 
        block_index: int = 0
    ) -> tuple[str, str]:
        """
        Construct full system and user prompts from PivotJSON.
        
        Args:
            pivot_json: PivotJSON object from audio analysis.
            block_index: Index of the block to process (default: 0).
            
        Returns:
            Tuple of (system_prompt, user_prompt).
            
        Raises:
            IndexError: If block_index is out of range.
        """
        if not pivot_json.blocks:
            raise ValueError("PivotJSON has no blocks to process")
        
        if block_index >= len(pivot_json.blocks):
            raise IndexError(
                f"Block index {block_index} out of range. "
                f"PivotJSON has {len(pivot_json.blocks)} blocks."
            )
        
        # Get the target block
        block = pivot_json.blocks[block_index]
        
        # Process block data into LLM-friendly formats
        block_data = self._process_block(block)
        
        # System prompt is static (loaded from template)
        system_prompt = self._system_template
        
        # User prompt is filled with block-specific data
        user_prompt = self._fill_template(self._user_template, block_data)
        
        return system_prompt, user_prompt
    
    def construct_prompt_for_all_blocks(
        self, 
        pivot_json
    ) -> list[tuple[str, str]]:
        """
        Construct prompts for all blocks in PivotJSON.
        
        Args:
            pivot_json: PivotJSON object from audio analysis.
            
        Returns:
            List of (system_prompt, user_prompt) tuples, one per block.
        """
        prompts = []
        for i in range(len(pivot_json.blocks)):
            prompts.append(self.construct_prompt(pivot_json, block_index=i))
        return prompts


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    # Quick test with mock data
    from dataclasses import dataclass
    
    @dataclass
    class MockSegment:
        time_start: float
        duration: float
        is_stressed: bool
        is_sustained: bool
    
    @dataclass
    class MockBlock:
        id: int
        syllable_target: int
        segments: list
    
    @dataclass
    class MockPivotJSON:
        tempo: float
        duration: float
        blocks: list
    
    # Create test data: DA-da-DA-da-DA pattern with last syllable sustained
    segments = [
        MockSegment(0.0, 0.2, is_stressed=True, is_sustained=False),
        MockSegment(0.2, 0.2, is_stressed=False, is_sustained=False),
        MockSegment(0.4, 0.2, is_stressed=True, is_sustained=False),
        MockSegment(0.6, 0.2, is_stressed=False, is_sustained=False),
        MockSegment(0.8, 0.6, is_stressed=True, is_sustained=True),
    ]
    
    block = MockBlock(id=1, syllable_target=5, segments=segments)
    pivot = MockPivotJSON(tempo=140.0, duration=1.5, blocks=[block])
    
    # Test engine
    print("Flow-to-Lyrics: Prompt Engine Test")
    print("=" * 50)
    
    try:
        engine = PromptEngine(template_dir="prompts")
        system_msg, user_msg = engine.construct_prompt(pivot)
        
        print("\n📜 SYSTEM PROMPT:")
        print("-" * 50)
        print(system_msg[:500] + "..." if len(system_msg) > 500 else system_msg)
        
        print("\n👤 USER PROMPT:")
        print("-" * 50)
        print(user_msg)
        
        print("\n✅ Prompt Engine working correctly!")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
