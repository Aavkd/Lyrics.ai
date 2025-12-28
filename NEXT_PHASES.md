#  Technical Specification: "Dual-Workflow" & Precision Pivot

**Date:** December 28, 2025  
**Version:** 3.0 (Post-Pivot)  
**Objective:** Refactor the backend for high-precision iterative generation (Co-Pilot) and prepare the architecture for batch automation.

## 1. Executive Strategy

The project is pivoting from a linear "One-Shot" pipeline to a **Dual-Workflow Architecture**.

- **Workflow A (Batch):** Long files > Sliced chunks > Serialized Generation.
- **Workflow B (Co-Pilot):** Short loops > Multi-candidate Generation > User Selection.

**Immediate Priority (per Audio Note):** Before building the full automation, we must maximize the precision of the model on short files (1-2 bars) by integrating pitch detection and improving phonetic/rhythmic matching.

### Cloud Ollama Configuration (New)

The `GenerationEngine` now supports both local and cloud Ollama instances via `.env` configuration:

```env
# For LOCAL Ollama (no API key needed):
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=ministral-3:8b

# For CLOUD Ollama (requires API key):
OLLAMA_URL=https://ollama.com/api
OLLAMA_MODEL=gemini-3-flash-preview:latest
OLLAMA_API_KEY=your_api_key_here
```

When `OLLAMA_API_KEY` is set, the engine automatically adds `Authorization: Bearer <key>` headers to all requests.

## 2. Phase 1: The "Precision" Engine (Backend Refactor)

**Goal:** Solve the accuracy issues identified in the test audio analysis.

### 2.1 Audio Engine Upgrade (Pitch & Precision)

**Current Status:** Pitch contour is "Not implemented".

**To Build:**
- **Pitch Detection Module:** Implement \librosa.piptrack\ or \pyin\ in \zudio_engine.py\ to extract the dominant pitch for each segment.
- **Melodic Contour Mapping:** Convert pitch data into a simple abstraction for the LLM (e.g., \["low", "mid", "high", "rising"]\) to be added to the PivotJSON.
- **Syllable Sensitivity Tuning:**
    - Create a \	ests/test_harness_precision.py\ specifically for your "Set of precise files".
    - Calibrate \onset_detect\ hyperparameters (\backtrack\, \wait\, \pre_max\) to minimize the error rate on these specific files.

### 2.2 Core Pipeline: Multi-Candidate Exposure

**Current Status:** The pipeline filters and returns only the "Winning Lyric".

**To Build:**
- **Return Structure Refactor:** Modify \core_pipeline.py\ to stop discarding candidates.
    - **Old Output:** \LyricLine\ (Best one).
    - **New Output:** \GenerationResult\ object containing:
        - \candidates\: \List[LyricLine]\ (All 5 generated options).
        - \metadata\: Audio analysis data.
- **Groove Score Calibration:** The current test log shows a generic score of 0.29. We need to adjust the \LyricValidator\ weights to better punish lines that miss the "Strong Beats" (Stress).

### 2.3 Prompt Engineering: "Phonetic & Melodic" Injection

**Current Status:** Prompt only asks for syllable count and stress pattern.

**To Build:**
- **Update \user_template.md\:** Inject the new pitch data.
    - *Example:* "Segment 2 is high-pitch and sustained. Suggest vowels like 'O' or 'A'."
- **Phonetic Matching (Advanced):** If the audio analysis detects specific formants (vowel sounds), pass these as "Suggested Phonemes" to the LLM.

## 3. Phase 2: The Architecture Logic (Dual-Workflow Support)

**Goal:** Implement the logic described in Implementation Notes to handle both short and long files safely.

### 3.1 The "Slicer" Logic (Workflow A)

**Requirement:** "Any input > 4 seconds must be forced-split".

**To Build:**
- **Safe-Slicing Algorithm:** In \audio_engine.py\, before analysis:
    1. Check total duration.
    2. If > 4s, find the nearest "Silence" or "Low Energy" point between 2s and 4s.
    3. Split audio into \Chunk_1\, \Chunk_2\, etc.
- **Batch Orchestrator:** Create a new method in \core_pipeline.py\ (\process_full_song\) that iterates through chunks and aggregates the results.

### 3.2 The "Co-Pilot" API (Workflow B)

**Requirement:** "Low Latency" and "Multi-Candidate Display".

**To Build:**
- **New API Endpoint:** \POST /generate/interactive\
    - **Input:** \
egion_id\ (specific timeline segment), \context\ (previous lines).
    - **Behavior:** Calls the optimized generation engine for just that segment.
    - **Output:** Returns the 5 raw candidates + scores.

## 4. Phase 3: The Frontend "Co-Pilot" Interface

**Goal:** Move from "Read-Only" to "Interactive Instrument".

### 4.1 The "Slot Machine" UI

**Requirement:** "The system generates a batch (e.g., 5 variations) and presents all of them".

**To Build:**
- **Candidate List Component:** A UI drawer that opens when a region is selected.
    - Displays 5 lyric options.
    - Shows "Groove Score" and "Syllable Match" icons next to each.
- **Click-to-Apply:** Clicking a candidate instantly writes it into the Waveform Region.
- **"Regenerate" Button:** A prominent button to re-roll the dice on the selected region.

### 4.2 Interactive Segmentation

**Requirement:** "The tool acts as an instrument... selects the best fit".

**To Build:**
- **Tap-to-Rhythm (Spacebar):** As defined in the PRD, allow the user to play the loop and tap space to define the exact syllable grid if the AI misses.
- **Region Locking:** Allow the user to "Lock" a region once they are happy with the lyric, protecting it from future batch regenerations.

## 5. Summary of Deliverables

| Priority | Component | Task | Source Requirement |
| :--- | :--- | :--- | :--- |
| **P0 (Immediate)** | AudioEngine | Tune Onset Detection & Implement Pitch on specific test files. | Audio Note |
| **P0 (Immediate)** | CorePipeline | Refactor to return ALL 5 candidates instead of 1. | Impl. Notes |
| **P1** | Frontend | Build the Candidate List UI (The Co-Pilot View). | Impl. Notes |
| **P2** | AudioEngine | Implement Auto-Segmentation (Slicing) for files >4s. | Impl. Notes |
| **P3** | PromptEngine | Inject Melodic/Pitch constraints into LLM prompt. | Audio Note |

##  Recommended Next Step

To satisfy your request in the audio note ("I want to attack this specific part first" - accuracy on test files):

I can create a new Python script \	ests/test_precision_tuning.py\.

This script will:
1. Take your folder of "Short Test Files".
2. Run them through \librosa\ with varying sensitivity settings.
3. Output a comparison table: **Actual Syllables vs Detected Syllables** to find the "Perfect Settings" for your specific audio style.

**Would you like me to generate this tuning script now?**
