# Phonetic Update: Refinements Status

**Last Updated**: 2025-12-28  
**Version**: 2.2-alpha (Post Syllable Detection Overhaul)

---

## Summary

This document tracked phonetic analysis issues and their fixes. **Most critical issues have been resolved** as of 2025-12-28.

---

## Issue 1: Under-Detection of Syllables - ✅ RESOLVED

### Original Problem
- **Input**: Vocal mumble of "Talk to me, I said what" (6 syllables)
- **Expected**: 6 segments detected
- **Actual**: 3 segments detected

### Root Cause
The `LibrosaAnalyzer` onset detection was configured with conservative parameters (`delta=0.1`) that caused **under-detection** of syllables in continuous speech/mumbles.

### Solution Implemented (2025-12-28)

1. **Lowered onset detection threshold**: Changed default `delta` from `0.1` to `0.05` for more sensitive detection.

2. **Added energy-based fallback detection**: A secondary detection strategy using RMS energy peaks, activated when spectral flux finds fewer than 3 onsets.

3. **Configurable via `.env`**:
   ```ini
   ONSET_DELTA=0.05          # Lower = more sensitive
   ONSET_USE_ENERGY=true     # Enable energy-based fallback
   ```

### Result
- **Before**: 3 segments detected
- **After**: 6 segments detected ✓

---

## Issue 2: Long Segment Durations - ✅ RESOLVED

### Original Problem
- Segment durations stretching to 1.045s (too long for single syllable)

### Solution Implemented (2025-12-28)

1. **Automatic segment splitting**: Segments longer than `MAX_SEGMENT_DURATION` (default: 1.0s) are split at energy valleys.

2. **Valley depth checking**: Only splits when energy drops >30% from surrounding peaks, preventing incorrect splits during sustained notes.

3. **Configurable via `.env`**:
   ```ini
   MAX_SEGMENT_DURATION=1.0  # Only very long segments split
   ```

---

## Issue 3: Breath Sound Detection - ✅ RESOLVED

### Original Problem (Identified during overhaul)
Lowering detection threshold risked detecting breath intakes as syllables.

### Solution Implemented (2025-12-28)

1. **Low-energy segment filtering**: Short segments (<150ms) with low energy (<15% of track max) are filtered out as likely breaths/noise.

2. **Automatic in pipeline**: `_filter_low_energy_segments()` runs after splitting, before phonetic analysis.

---

## Issue 4: Sustained Note Handling - ✅ RESOLVED

### Original Problem
Segment splitting could chop "loooove" (sustained vowel) into "loo" + "oove".

### Solution Implemented (2025-12-28)

1. **Valley depth requirement**: `_find_energy_valleys()` now requires `min_valley_depth=0.3` (30% energy drop) to consider a split point valid.

2. **Flat valleys = sustained notes**: If energy stays relatively flat within a segment, it's marked as sustained (not split).

---

## Issue 5: Phoneme Quality - ⚠️ PARTIALLY ADDRESSED

### Current Status
- Allosaurus returns valid IPA symbols (e.g., `t͡ɕ ʌ ɒ`)
- These are universal phones, may differ from English-specific phonemes
- Phonetic matching score remains low (0.00-0.08 in tests)

### Impact
- LLM gets approximate sound hints but not precise matches
- This is expected behavior for universal phone recognition

### Assessment
This is **partially expected behavior**. The broad phonetic class matching helps, but exact matching is unreliable. Consider simplifying to consonant/vowel class matching only.

---

## Issue 6: Transcription Order - ✅ VERIFIED CORRECT

### Concern
Segment splitting must happen BEFORE phonetic analysis to ensure Allosaurus receives correct timestamps.

### Status
Verified in `PivotFormatter.format()`:
1. Line 1067-1068: `_split_long_segments()` runs first
2. Line 1070: `_filter_low_energy_segments()` runs second
3. Line 1091: `phonetic_analyzer.analyze_segments()` runs AFTER

Correct order confirmed. ✓

---

## Configuration Options

All syllable detection parameters are now configurable via `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ONSET_DELTA` | `0.05` | Detection sensitivity (lower = more sensitive) |
| `ONSET_USE_ENERGY` | `true` | Enable energy-based fallback detection |
| `MAX_SEGMENT_DURATION` | `1.0` | Max segment length before auto-splitting |
| `ONSET_WAIT` | `1` | Min frames between onsets |

---

## Remaining Work

### Priority 1: Phonetic Matching Improvement
- [ ] Simplify to broad phonetic class matching only
- [ ] Weight vowel sounds more heavily than consonants
- [ ] Add confidence score from Allosaurus to weight phonetic score

### Priority 2: UI/UX Improvements
- [ ] Display detected segments visually for user validation
- [ ] Allow user to edit/split/merge segments before generation
- [ ] Show phonetic transcription for human review

---

## Test Commands

To test syllable detection:
```powershell
python audio_engine.py "audio samples/test_audio_2-1.m4a" --mock
```

To run precision tuning test:
```powershell
python tests/test_precision_tuning.py
```
