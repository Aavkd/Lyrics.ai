Technical Design Document: Phonetic "Sound-Alike" Generation
Feature Branch: feature/phonetic-matching

Target Version: 2.1 (Post-Precision Engine)

Objective: Enable the "Flow-to-Lyrics" engine to generate words that phonetically resemble the input vocal mumbles ("yaourt"), ensuring the output sounds like the artist's original flow.

1. Overview
The current architecture captures Rhythm (Syllables via LibrosaAnalyzer) and Melody (Pitch via pYIN). However, it ignores the Timbre/Phonetics of the input.

This feature introduces a Phonetic Recognition Layer using Allosaurus (Universal Phone Recognizer). This allows the system to hear that a mumble sounds like "/ba-da/" and guide the LLM to generate words like "Brother" or "Border" instead of random 2-syllable words.

2. Architecture Updates
2.1. New Dependency: Allosaurus
We will replace the standard Speech-to-Text approach (which fails on mumbles) with Allosaurus, a library designed to output raw IPA (International Phonetic Alphabet) tokens regardless of language or meaning.

Package: allosaurus

Input: 16kHz Mono Audio Tensor

Output: IPA String (e.g., d æ n)

2.2. Data Flow Diagram
Extrait de code

graph LR
    Audio -->|Resample 16kHz| Allosaurus
    Allosaurus -->|IPA Tokens| AudioEngine
    AudioEngine -->|phonemes| PivotJSON
    
    PivotJSON -->|Prompt: 'Sounds like /d æ n/'| LLM
    LLM -->|Candidate: 'Dan'| Validator
    
    Validator -->|G2P: 'D AE N'| Comparator
    Comparator -->|Score| Result
3. Module Implementation Plan
Step 1: Audio Pre-processing (Prerequisite)
As noted in the Project Status, the pipeline currently lacks 16kHz normalization. Allosaurus requires strict 16kHz input.

Task: Add a resampling utility in audio_engine.py.

Python

# audio_engine.py update
import librosa
import numpy as np

def resample_audio(y: np.ndarray, orig_sr: int, target_sr: int = 16000) -> np.ndarray:
    if orig_sr == target_sr:
        return y
    return librosa.resample(y, orig_sr=orig_sr, target_sr=target_sr)
Step 2: The Phonetic Analyzer (audio_engine.py)
Create a new wrapper class for Allosaurus, similar to DemucsProcessor and LibrosaAnalyzer.

Implementation:

Initialize allosaurus.app.read_recognizer() on startup.

Implement extract_phonemes(segment_audio).

Update the Segment dataclass to include the new field.

Python

# audio_engine.py update

@dataclass
class Segment:
    # Existing fields...
    time_start: float
    duration: float
    is_stressed: bool
    pitch_contour: str
    # NEW FIELD
    audio_phonemes: str = ""  # Raw IPA output (e.g., "b a")

class PhoneticAnalyzer:
    def __init__(self):
        from allosaurus.app import read_recognizer
        self.model = read_recognizer()
    
    def analyze_segment(self, y_segment: np.ndarray, sr: int) -> str:
        # Allosaurus expects 16kHz
        # Run inference -> Return string
        pass
Step 3: Prompt Engineering (prompt_engine.py)
The LLM needs to know how to use this phonetic data. We will inject "Phonetic Hints" into the user prompt.

Template Update (prompts/user_template.md): Add a new column to the segment table structure:

Markdown

| Syllable | Stress | Pitch | **Sounds Like (IPA)** |
| :--- | :--- | :--- | :--- |
| 1 | DA (Strong) | High | /k ae/ |
| 2 | da (Weak) | Low | /t/ |
Instruction Update (prompts/system_instruction.md):

"The 'Sounds Like' column contains the raw phonetic sounds the user mumbled. Constraint: Prioritize words that share vowels (Assonance) or consonants (Consonance) with these sounds. Example: If 'Sounds Like' is /m uh n/, valid generations include 'Money', 'Monday', 'Month'."

Step 4: Phonetic Validator (validator.py)
The validator currently uses g2p_en to convert Text → ARPABET Phonemes for syllable counting. We need to compare these ARPABET phonemes against Allosaurus's IPA phonemes.

Challenge: Mapping ARPABET (Text) to IPA (Audio). Solution: Use a simplified mapping or a phonetic feature distance library (like panphon or simple Levenshtein on simplified characters).

Logic Update:

Get Candidate Phonemes: g2p_en(text) → ['M', 'AH1', 'N', 'IY0'] (ARPABET).

Get Audio Phonemes: segment.audio_phonemes → 'm a n i' (IPA).

Normalize: Map ARPABET to simplified IPA (e.g., AH1 → a).

Score: Calculate similarity (0.0 to 1.0).

Python

# validator.py update

class LyricValidator:
    # ... existing methods ...

    def calculate_phonetic_match(self, text_phonemes: list, audio_ipa: str) -> float:
        # 1. Convert Text ARPABET to simplified string
        # 2. Calculate Levenshtein distance vs Audio IPA
        # 3. Return normalized score (1.0 = perfect match)
        pass

    def validate_line(self, text, target_segments):
        # ... existing syllable check ...
        
        # New Scoring Formula
        groove_score = self.calculate_groove_score(...)
        phonetic_score = self.calculate_phonetic_match(...)
        
        # Weighted Final Score (Rhythm > Phonetics)
        total_score = (groove_score * 0.6) + (phonetic_score * 0.4)
4. Execution Roadmap
Phase A: Environment & Core (1-2 Days)
Update requirements.txt: Add allosaurus, librosa (update if needed).

Task: Implement PhoneticAnalyzer class in audio_engine.py.

Task: Update process() pipeline to resample to 16kHz and run phonetic analysis on every segment.

Verification: Run audio_engine.py on a sample mumble track. Inspect PivotJSON to ensure audio_phonemes fields are populated with IPA strings.

Phase B: Prompt Integration (1 Day)
Task: Modify prompt_engine.py to read audio_phonemes from PivotJSON.

Task: Update user_template.md to display the phonetic column.

Verification: Run core_pipeline.py. Check the generated prompt (printed in logs) to ensure phonetic data is visible to the LLM.

Phase C: Validation Logic (1-2 Days)
Task: Implement ARPABET-to-IPA mapping in validator.py.

Task: Implement calculate_phonetic_match.

Task: Tune the weights. If the weight is too high, the LLM generates nonsense words just to match the sound. Start with 0.3 weight.

Phase D: Testing
Test Case: Use audio samples/3_syllabes_test.mp3.

Action: Mumble distinct vowel sounds (e.g., "Bee Bah Boo").

Success Criteria: The system generates words matching those vowels (e.g., "See", "Car", "You") rather than random words.

5. Potential Risks & Mitigations
Risk: Allosaurus is slow on CPU.

Mitigation: Only run it on short segments (the identified syllable blocks), not the whole file at once.

Risk: g2p_en (ARPABET) vs Allosaurus (IPA) mismatch.

Mitigation: Use "Broad Phonetic Class" matching (e.g., match any Plosive with any Plosive) instead of exact character matching if strict mapping fails.