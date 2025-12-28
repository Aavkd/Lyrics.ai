# Phase 1: Precision Engine - Changelog

**Date:** December 28, 2025  
**Version:** 1.0  
**Focus:** Backend precision improvements for short vocal samples

---

## Summary

Phase 1 implements the "Precision Engine" refactor as specified in `NEXT_PHASES.md`. This phase focuses on maximizing accuracy by adding pitch detection, exposing all LLM candidates, and creating a precision tuning harness.

---

## Changes Made

### 1. Pitch Detection (`audio_engine.py`)

**Added `pitch_contour` field to `Segment` dataclass:**
- New optional field: `pitch_contour: str = "mid"` 
- Values: `"low"`, `"mid"`, `"high"`, `"rising"`, `"falling"`

**Implemented `_detect_pitch()` method in `PivotFormatter`:**
- Uses `librosa.pyin` for accurate vocal pitch tracking
- Frequency thresholds:
  - `low`: < 150 Hz
  - `mid`: 150-300 Hz (typical speech)
  - `high`: > 300 Hz
- Contour detection: rising/falling with >20% pitch change

**Updated `PivotJSON.to_dict()`:**
- Now serializes `pitch_contour` per segment

**CRITICAL: Applied optimal onset detection config to `LibrosaAnalyzer.analyze()`:**
- Integrated the "Less Sensitive" config (`delta=0.1`) from precision tuning
- This fixed the over-detection issue (7 syllables → 5 syllables on test file)

---

### 2. Multi-Candidate Exposure (`core_pipeline.py`)

**Created `GenerationResult` dataclass:**
```python
@dataclass
class GenerationResult:
    candidates: list[str]           # All 5 LLM options
    validations: list[ValidationResult]
    best_line: Optional[str]        # Auto-selected winner
    best_score: float               # Groove score
    metadata: dict                  # tempo, duration, stress_pattern, pitch_pattern
    pivot_json: Optional[PivotJSON]
```

**Refactored `run_full_pipeline()`:**
- Now the preferred method for Co-Pilot workflow
- Returns rich metadata including:
  - `stress_pattern`: e.g., "DA-da-da-da-DA-da-da"
  - `pitch_pattern`: e.g., "falling-mid-mid-rising-falling-mid-mid"
  - `syllable_target`, `tempo`, `duration`

---

### 3. Groove Score Calibration (`validator.py`)

**Updated `calculate_groove_score()` with weighted scoring:**

| Match Type | Old Points | New Points |
|------------|-----------|------------|
| Stressed match (audio + text both stressed) | 1 | **2** |
| Unstressed match (both unstressed) | 1 | 1 |
| Secondary stress on stressed audio | 0.5 | 0.5 |
| Mismatch | 0 | 0 |

**New formula:**
```
max_points = (stressed_count * 2) + unstressed_count
score = earned_points / max_points
```

This gives 2x weight to hitting stressed beats, addressing the "0.29 score issue" from testing.

---

### 4. Prompt Engineering (`prompt_engine.py` + `prompts/user_template.md`)

**Added `_generate_pitch_guidance()` method:**
- Converts pitch contours to natural language LLM guidance
- Example output:
  ```
  - Syllable 1 **falls** in pitch. Use it for emphasis or resolution.
  - Syllable 4 **rises** in pitch. Build energy into the word.
  ```

**Updated `prompts/user_template.md`:**
- Added `## Melodic Guidance` section with `{{pitch_guidance}}` placeholder

---

### 5. Precision Tuning Script (`tests/test_precision_tuning.py`)

**Created precision tuning harness:**
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

**Recommended Configuration:**
```python
OnsetConfig(
    name="Less Sensitive",
    delta=0.1,  # Higher = fewer false positives
    wait=1, pre_max=1, post_max=1
)
```

---

## Verification

All tests pass:
```
✅ Syllable Counting: PASSED
✅ Stress Extraction: PASSED
✅ Groove Score: PASSED
✅ Validator Logic: PASSED
✅ Best Candidate Selection: PASSED
✅ Pipeline Initialization: PASSED
✅ Invalid File Handling: PASSED
✅ Full Pipeline: PASSED

✅ ALL TESTS PASSED!
```

---

## Files Modified

| File | Changes |
|------|---------|
| `audio_engine.py` | Added `pitch_contour` to Segment, `_detect_pitch()` method |
| `core_pipeline.py` | Added `GenerationResult`, refactored `run_full_pipeline()` |
| `validator.py` | Updated `calculate_groove_score()` with weighted scoring |
| `prompt_engine.py` | Added `_generate_pitch_guidance()`, updated `_process_block()` |
| `prompts/user_template.md` | Added Melodic Guidance section |
| `tests/test_precision_tuning.py` | **NEW** - Precision tuning harness |
| `tests/test_end_to_end.py` | Updated groove score test expectations |

---

## Next Steps (Phase 2)

Per `NEXT_PHASES.md`:
1. Implement "Slicer" logic for files > 4 seconds
2. Create "Co-Pilot" API endpoint (`POST /generate/interactive`)
3. Build Candidate List UI component
