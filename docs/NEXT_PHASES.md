#  Technical Specification: "Dual-Workflow" & Precision Pivot

**Date:** December 28, 2025  
**Version:** 3.1 (Post Phase 1 Completion)  
**Objective:** Refactor the backend for high-precision iterative generation (Co-Pilot) and prepare the architecture for batch automation.

## 1. Executive Strategy

The project is pivoting from a linear "One-Shot" pipeline to a **Dual-Workflow Architecture**.

- **Workflow A (Batch):** Long files > Sliced chunks > Serialized Generation.
- **Workflow B (Co-Pilot):** Short loops > Multi-candidate Generation > User Selection.

**Immediate Priority (per Audio Note):** Before building the full automation, we must maximize the precision of the model on short files (1-2 bars) by integrating pitch detection and improving phonetic/rhythmic matching.

### Cloud Ollama Configuration

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

---

## 2. Phase 1: The "Precision" Engine (Backend Refactor) - ✅ COMPLETE

**Goal:** Solve the accuracy issues identified in the test audio analysis.

**Status:** ✅ 100% Complete (2025-12-28)

### 2.1 Audio Engine Upgrade (Pitch & Precision) - ✅ Done

**Original Status:** Pitch contour was "Not implemented".

**What Was Built:**
- ✅ **Pitch Detection Module:** Implemented `librosa.pyin` in `audio_engine.py` to extract the dominant pitch for each segment.
- ✅ **Melodic Contour Mapping:** Converted pitch data into a simple abstraction for the LLM (e.g., `["low", "mid", "high", "rising", "falling"]`) added to the PivotJSON.
- ✅ **Syllable Sensitivity Tuning:**
    - Created `tests/test_precision_tuning.py` for the "Set of precise files".
    - Calibrated `onset_detect` hyperparameters (`delta=0.1`) to minimize error rate.

**Files Modified:**
- `audio_engine.py` → Added `pitch_contour` to `Segment`, `_detect_pitch()` method in `PivotFormatter`

### 2.2 Core Pipeline: Multi-Candidate Exposure - ✅ Done

**Original Status:** The pipeline filtered and returned only the "Winning Lyric".

**What Was Built:**
- ✅ **Return Structure Refactor:** Modified `core_pipeline.py` to stop discarding candidates.
    - **Old Output:** `LyricLine` (Best one).
    - **New Output:** `GenerationResult` object containing:
        - `candidates`: `List[str]` (All 5 generated options).
        - `validations`: `List[ValidationResult]` (Score per candidate).
        - `best_line`: Auto-selected winner.
        - `best_score`: Groove score (0.0-1.0).
        - `metadata`: Audio analysis data (tempo, duration, stress_pattern, pitch_pattern).
        - `pivot_json`: Full PivotJSON from audio analysis.
- ✅ **Groove Score Calibration:** Adjusted the `LyricValidator` weights to 2x penalty for missing "Strong Beats" (Stress).

**Files Modified:**
- `core_pipeline.py` → Added `GenerationResult` dataclass, refactored `run_full_pipeline()`
- `validator.py` → Updated `calculate_groove_score()` with weighted scoring

### 2.3 Prompt Engineering: "Phonetic & Melodic" Injection - ✅ Done

**Original Status:** Prompt only asked for syllable count and stress pattern.

**What Was Built:**
- ✅ **Updated `user_template.md`:** Injected the new pitch data via `{{pitch_guidance}}` placeholder.
    - *Example:* "Syllable 2 is high-pitch and sustained. Suggest vowels like 'O' or 'A'."
- ✅ **Added `_generate_pitch_guidance()` method** in `prompt_engine.py`

**Files Modified:**
- `prompt_engine.py` → Added `_generate_pitch_guidance()`, updated `_process_block()`
- `prompts/user_template.md` → Added `## Melodic Guidance` section

### 2.4 Precision Tuning Script - ✅ Done

**Created `tests/test_precision_tuning.py`:**
- Loads audio samples from `audio samples/` folder
- Tests 6 onset detection configurations
- Outputs comparison table with error analysis
- Recommends best configuration

**Test Results:**

| File | Expected | Best Config | Error |
|------|----------|-------------|-------|
| 3_syllabes(sustained)_test.mp3 | 3 | Less Sensitive | ✓ 0 |
| 3_syllabes_test.mp3 | 3 | Less Sensitive | ✓ 0 |
| 5_syllabes_test.mp3 | 5 | Less Sensitive | ✓ 0 |
| 10_syllabes_test.mp3 | 10 | Less Sensitive | +1 |

**Recommended Configuration Applied:**
```python
OnsetConfig(
    name="Less Sensitive",
    delta=0.1,  # Higher = fewer false positives
    wait=1, pre_max=1, post_max=1
)
```

---

## 3. Phase 2: The Architecture Logic (Dual-Workflow Support)

**Goal:** Implement the logic described in Implementation Notes to handle both short and long files safely.

**Status:** 🟡 In Progress (50% complete)

### 3.1 The "Slicer" Logic (Workflow A) - 🔴 Not Started

**Requirement:** "Any input > 4 seconds must be forced-split".

**To Build:**
- **Safe-Slicing Algorithm:** In `audio_engine.py`, before analysis:
    1. Check total duration.
    2. If > 4s, find the nearest "Silence" or "Low Energy" point between 2s and 4s.
    3. Split audio into `Chunk_1`, `Chunk_2`, etc.
- **Batch Orchestrator:** Create a new method in `core_pipeline.py` (`process_full_song`) that iterates through chunks and aggregates the results.

### 3.2 The "Co-Pilot" API (Workflow B) - 🔴 Not Started

**Requirement:** "Low Latency" and "Multi-Candidate Display".

**To Build:**
- **New API Endpoint:** `POST /generate/interactive`
    - **Input:** `region_id` (specific timeline segment), `context` (previous lines).
    - **Behavior:** Calls the optimized generation engine for just that segment.
    - **Output:** Returns the 5 raw candidates + scores.

---

## 4. Phase 3: The Frontend "Co-Pilot" Interface

**Goal:** Move from "Read-Only" to "Interactive Instrument".

**Status:** 🔴 Not Started (0% complete)

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

---

## 5. Phase 4: Export & Polish

**Goal:** Complete the user workflow with export capabilities.

**Status:** 🔴 Not Started (0% complete)

### 5.1 Export Functionality

**To Build:**
- **Export Buttons** in UI:
  - "Export JSON" → Download full PivotJSON with lyrics
  - "Export SRT" → Download subtitles in SRT format
  - "Export VTT" → Download subtitles in WebVTT format
- **Backend Endpoints:**
  ```python
  @app.post("/export/json")
  @app.post("/export/srt")
  @app.post("/export/vtt")
  ```

### 5.2 SSE Streaming

**For Future:** Real-time lyric display during generation
- Replace REST with SSE for `/generate/interactive`
- Stream each candidate as it's generated
- Show progress indicator during LLM processing

---

## 6. Summary of Deliverables

| Priority | Component | Task | Status |
| :--- | :--- | :--- | :--- |
| **P0 (Done)** | AudioEngine | ~~Tune Onset Detection & Implement Pitch~~ | ✅ Complete |
| **P0 (Done)** | CorePipeline | ~~Refactor to return ALL 5 candidates~~ | ✅ Complete |
| **P0 (Done)** | Validator | ~~Calibrate Groove Score (2x weight)~~ | ✅ Complete |
| **P0 (Done)** | PromptEngine | ~~Inject Melodic/Pitch constraints~~ | ✅ Complete |
| **P1** | main.py | Add `/generate/interactive` endpoint | 🔴 Not Started |
| **P1** | Frontend | Build the Candidate List UI (Co-Pilot View) | 🔴 Not Started |
| **P2** | AudioEngine | Implement Auto-Segmentation (Slicing) for files >4s | 🔴 Not Started |
| **P2** | AudioEditor | Tap-to-Rhythm feature | 🔴 Not Started |
| **P2** | AudioEditor | Region Split/Merge/Delete | 🔴 Not Started |
| **P3** | Frontend | Export functionality (JSON/SRT) | 🔴 Not Started |
| **P3** | main.py | SSE streaming for lyrics | 🔴 Not Started |

---

## 7. Technical Debt & Improvements

### High Priority
1. **Connect frontend to generation pipeline**
   - Currently generation only works via CLI
   - Need API endpoint + frontend integration

2. **Real Demucs processing**
   - Currently defaults to mock mode
   - Needs GPU testing and validation

### Medium Priority
3. **Sample rate normalization**
   - PRD requires mono 16kHz conversion
   - Not implemented in current pipeline

4. **Multi-block support**
   - Frontend only renders `blocks[0]`
   - Need to handle multiple blocks for full songs

### Low Priority
5. **BPM accuracy improvement**
   - ~5% variance on some files
   - Consider prior BPM estimation

6. **Timeline plugin**
   - Visual time markers on waveform
   - Helps with manual editing

---

##  8. Recommended Next Step

**Immediate Action:** Create the `/generate/interactive` API endpoint.

This is the **critical blocker** for all frontend work. Once this endpoint exists:
1. Frontend can call it when a region is selected
2. CandidateList can display the 5 options
3. User can click to apply a lyric

**Estimated effort:** 2-4 hours

```python
# main.py - Add this endpoint

@app.post("/generate/interactive")
async def generate_interactive(
    file: UploadFile = File(...),
    block_index: int = 0
):
    """
    Generate lyric candidates for the given audio file.
    Returns all 5 candidates with validation scores.
    """
    # Save file temporarily
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir) / file.filename
    save_upload_file(file, temp_path)
    
    try:
        # Run full pipeline
        pipeline = CorePipeline(mock_mode=config.MOCK_MODE)
        result = pipeline.run_full_pipeline(str(temp_path), block_index)
        
        # Return structured result
        return {
            "candidates": result.candidates,
            "validations": [
                {
                    "is_valid": v.is_valid,
                    "score": v.score,
                    "syllable_count": v.syllable_count,
                    "reason": v.reason
                }
                for v in result.validations
            ],
            "best_line": result.best_line,
            "best_score": result.best_score,
            "metadata": result.metadata
        }
    finally:
        shutil.rmtree(temp_dir)
```

**Would you like me to implement this endpoint now?**
