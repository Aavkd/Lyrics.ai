"""
Flow-to-Lyrics: Core Pipeline (The Orchestrator)
=================================================
End-to-end pipeline connecting all engines for lyric generation.

This module orchestrates:
1. AudioEngine -> PivotJSON (Step 1)
2. PromptEngine -> LLM Prompts (Step 2)
3. GenerationEngine -> Candidates (Step 3)
4. LyricValidator -> Best Match (Step 4)

Usage:
    pipeline = CorePipeline()
    best_line, score = pipeline.run_pipeline("test_audio.mp3")
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from audio_engine import AudioEngine, Block, PivotJSON, Segment
from generation_engine import GenerationEngine
from prompt_engine import PromptEngine
from validator import LyricValidator, ValidationResult


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class PipelineResult:
    """Result of the full pipeline execution.
    
    Attributes:
        best_line: The winning lyric line (or None if no valid match).
        score: Groove score of the best line (0.0 to 1.0).
        all_candidates: List of all generated candidates.
        all_validations: List of ValidationResult for each candidate.
        pivot_json: The PivotJSON from audio analysis.
    """
    best_line: Optional[str]
    score: float
    all_candidates: list[str]
    all_validations: list[ValidationResult]
    pivot_json: Optional[PivotJSON]


# =============================================================================
# CORE PIPELINE
# =============================================================================

class CorePipeline:
    """
    Main orchestrator connecting all Flow-to-Lyrics engines.
    
    Pipeline flow:
    1. Load Audio -> AudioEngine -> PivotJSON
    2. PivotJSON -> PromptEngine -> System + User Prompts
    3. Prompts -> GenerationEngine -> 5 Candidate Lines
    4. Candidates -> LyricValidator -> Best Match (Highest Groove Score)
    
    Usage:
        pipeline = CorePipeline()
        best_line, score = pipeline.run_pipeline("song.mp3")
    """
    
    def __init__(
        self,
        mock_mode: bool = False,
        ollama_model: str = "ministral-3:8b",
        ollama_url: str = "http://localhost:11434",
        templates_dir: str = "prompts"
    ):
        """
        Initialize the pipeline with all sub-engines.
        
        Args:
            mock_mode: If True, use mock mode for AudioEngine and GenerationEngine.
                       Useful for testing without real audio/LLM processing.
            ollama_model: Model name for Ollama LLM.
            ollama_url: Base URL for Ollama API.
            templates_dir: Directory containing prompt templates.
        """
        # Initialize all engines
        self.audio_engine = AudioEngine(mock_mode=mock_mode)
        self.prompt_engine = PromptEngine(template_dir=templates_dir)
        self.generation_engine = GenerationEngine(
            model=ollama_model,
            base_url=ollama_url,
            mock_mode=mock_mode
        )
        self.validator = LyricValidator()
        
        self.mock_mode = mock_mode
    
    def run_pipeline(
        self, 
        audio_path: str,
        block_index: int = 0
    ) -> tuple[Optional[str], float]:
        """
        Run the complete audio-to-lyrics pipeline.
        
        Args:
            audio_path: Path to the input audio file.
            block_index: Which block to process (default: 0, the first block).
            
        Returns:
            Tuple of (best_lyric_line, groove_score).
            Returns (None, 0.0) if no valid candidates found.
        """
        print("\n" + "=" * 70)
        print("  🎵 FLOW-TO-LYRICS: CORE PIPELINE")
        print("=" * 70)
        
        # =====================================================================
        # STEP 1: Audio Analysis
        # =====================================================================
        print("\n📊 STEP 1: Audio Analysis")
        print("-" * 50)
        
        if not os.path.exists(audio_path):
            print(f"  ❌ Audio file not found: {audio_path}")
            return None, 0.0
        
        try:
            pivot_json = self.audio_engine.process(audio_path)
            print(f"  ✓ Tempo: {pivot_json.tempo:.1f} BPM")
            print(f"  ✓ Duration: {pivot_json.duration:.2f}s")
            print(f"  ✓ Blocks: {len(pivot_json.blocks)}")
            
            if not pivot_json.blocks:
                print("  ❌ No blocks detected in audio")
                return None, 0.0
            
            block = pivot_json.blocks[block_index]
            print(f"  ✓ Block {block.id}: {block.syllable_target} syllables")
            
            # Show stress pattern
            stress_pattern = "".join(
                "DA-" if seg.is_stressed else "da-" 
                for seg in block.segments
            ).rstrip("-")
            print(f"  ✓ Pattern: {stress_pattern}")
            
        except Exception as e:
            print(f"  ❌ Audio analysis failed: {e}")
            return None, 0.0
        
        # =====================================================================
        # STEP 2: Prompt Construction
        # =====================================================================
        print("\n📝 STEP 2: Prompt Construction")
        print("-" * 50)
        
        try:
            system_prompt, user_prompt = self.prompt_engine.construct_prompt(
                pivot_json, 
                block_index=block_index
            )
            print(f"  ✓ System prompt: {len(system_prompt)} chars")
            print(f"  ✓ User prompt: {len(user_prompt)} chars")
            
            # Show a preview of the user prompt
            preview = user_prompt[:150].replace("\n", " ")
            print(f"  ✓ Preview: \"{preview}...\"")
            
        except Exception as e:
            print(f"  ❌ Prompt construction failed: {e}")
            return None, 0.0
        
        # =====================================================================
        # STEP 3: Candidate Generation
        # =====================================================================
        print("\n🧠 STEP 3: LLM Generation")
        print("-" * 50)
        
        try:
            candidates = self.generation_engine.generate_candidates(
                system_prompt, 
                user_prompt
            )
            print(f"  ✓ Generated {len(candidates)} candidates")
            
            for i, candidate in enumerate(candidates, 1):
                print(f"    {i}. \"{candidate}\"")
                
        except Exception as e:
            print(f"  ❌ Generation failed: {e}")
            return None, 0.0
        
        # =====================================================================
        # STEP 4: Validation & Selection
        # =====================================================================
        print("\n⚖️ STEP 4: Validation (The Gatekeeper)")
        print("-" * 50)
        
        target_segments = block.segments
        
        # Validate all candidates
        validations = self.validator.validate_candidates(candidates, target_segments)
        
        print(f"  Target: {len(target_segments)} syllables")
        print()
        
        best_line = None
        best_score = 0.0
        best_result = None
        
        for i, (candidate, result) in enumerate(zip(candidates, validations), 1):
            status = "✓" if result.is_valid else "✗"
            print(f"  {status} Candidate {i}: \"{candidate}\"")
            print(f"      Syllables: {result.syllable_count}, Score: {result.score:.2f}")
            print(f"      {result.reason}")
            
            if result.is_valid and result.score > best_score:
                best_line = candidate
                best_score = result.score
                best_result = result
        
        # =====================================================================
        # FINAL RESULT
        # =====================================================================
        print("\n" + "=" * 70)
        print("  🏆 PIPELINE RESULT")
        print("=" * 70)
        
        if best_line:
            print(f"\n  ✅ WINNING LYRIC: \"{best_line}\"")
            print(f"  📊 GROOVE SCORE: {best_score:.2f}")
            print(f"  🎯 STRESS PATTERN: {best_result.stress_markers}")
        else:
            print("\n  ⚠️ NO VALID CANDIDATES FOUND")
            print("  💡 Try regenerating or adjusting thresholds")
        
        print("\n" + "=" * 70 + "\n")
        
        return best_line, best_score
    
    def run_full_pipeline(
        self, 
        audio_path: str
    ) -> PipelineResult:
        """
        Run the pipeline and return detailed results.
        
        Args:
            audio_path: Path to the input audio file.
            
        Returns:
            PipelineResult with all pipeline data for analysis.
        """
        # Run standard pipeline
        best_line, score = self.run_pipeline(audio_path)
        
        # For detailed results, we need to re-run some steps
        # (In production, we'd cache these)
        try:
            pivot_json = self.audio_engine.process(audio_path)
            system_prompt, user_prompt = self.prompt_engine.construct_prompt(pivot_json)
            candidates = self.generation_engine.generate_candidates(system_prompt, user_prompt)
            validations = self.validator.validate_candidates(
                candidates, 
                pivot_json.blocks[0].segments
            )
        except Exception:
            pivot_json = None
            candidates = []
            validations = []
        
        return PipelineResult(
            best_line=best_line,
            score=score,
            all_candidates=candidates,
            all_validations=validations,
            pivot_json=pivot_json
        )


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    import sys
    
    print("\n🎵 Flow-to-Lyrics: Core Pipeline Test")
    print("=" * 50)
    
    # Default test file
    audio_path = "test_audio_real.mp3"
    
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
    
    # Check for mock mode flag
    mock_mode = "--mock" in sys.argv
    
    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        print(f"💡 Using mock mode instead")
        mock_mode = True
    
    print(f"📁 Audio file: {audio_path}")
    print(f"🔧 Mock mode: {mock_mode}")
    
    # Initialize and run pipeline
    pipeline = CorePipeline(mock_mode=mock_mode)
    
    try:
        best_line, score = pipeline.run_pipeline(audio_path)
        
        if best_line:
            print(f"\n✅ Success! Best line: \"{best_line}\" (score: {score:.2f})")
        else:
            print(f"\n⚠️ No valid candidates found")
            
    except Exception as e:
        print(f"\n❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
