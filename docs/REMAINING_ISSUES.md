# Remaining Issues & Known Limitations

**Date:** 2025-12-28  
**Status:** Active Development  
**Context:** Post Phase D (Full-Audio Whisper + Syllable Alignment)

---

## Summary

After implementing Phase D (Full-Audio Whisper with syllable-aware alignment), phonetic analysis now achieves **100% alignment** for most audio files. This document tracks remaining issues for future refinement.

---

## Issue 1: Syllable Under-Detection

### Description
The breath/noise filter sometimes removes valid syllables.

### Evidence
| Audio | Expected Syllables | Detected | Issue |
|-------|-------------------|----------|-------|
| `trying_to_take_my_time.m4a` | 6 ("try-ing to take my time") | 5 | 1 syllable filtered as breath |

### Root Cause
`PivotFormatter` filters low-energy segments (< 15% of max) as breaths. Soft-spoken syllables may be incorrectly filtered.

### Potential Fix
- Adjust energy threshold dynamically based on overall audio RMS
- Add config option `BREATH_FILTER_THRESHOLD`

---

## Issue 2: Whisper Short Segment Accuracy ✅ FULLY RESOLVED

### Description
Whisper struggled with very short segments (<300ms), producing phonemes that don't match expected words.

### ✅ Fix Implemented (Phase D - 2025-12-28)
Implemented **full-audio transcription with syllable-aware alignment**:

1. **Full-audio transcription**: Transcribes entire audio once with `word_timestamps=True`
2. **Syllable splitting**: Converts words to syllables using onset maximization principle
3. **Sequential assignment**: Maps syllable[i] → segment[i] for proper 1:1 alignment

### Current Status
| Audio | Alignment Rate | Notes |
|-------|----------------|-------|
| `talk_to_me_i_said_what.m4a` | 100% (6/6) | Perfect syllable-phoneme matching |
| `what_bout_you.m4a` | 100% (3/3) | Full alignment |

### Configuration
```bash
# Enable full-audio mode (recommended, default: true)
WHISPER_USE_FULL_AUDIO=true

# Use larger model for better accuracy (optional)
WHISPER_MODEL_SIZE=small  # or medium/large
```

---

## Issue 3: Stress Pattern Detection

### Description
Stress detection is based purely on RMS amplitude, which may not accurately reflect perceptual stress.

### Evidence
| Audio | Stress Pattern | Expected |
|-------|---------------|----------|
| `trying_to_take_my_time.m4a` | da-DA-da-da-da | TRY-ing to TAKE my TIME (DA-da-da-DA-da-DA?) |

### Root Cause
RMS amplitude doesn't account for pitch accent or duration as stress indicators.

### Potential Fix
- Combine amplitude + pitch change + duration for multi-factor stress detection

---

## Issue 4: Pitch Tracking Accuracy

### Description
All segments show `low` pitch contour even when audio contains pitch variation.

### Evidence
```
Syllable 1: mid
Syllable 2-6: low (all same)
```

### Root Cause
Pitch detection may be miscalibrated for the frequency range of the vocals.

### Potential Fix
- Recalibrate `pyin` pitch thresholds based on vocal fundamental frequency

---

## Recommendations

### Short-term
1. ✅ ~~Implement hallucination mitigation~~ (DONE)
2. Allow `WHISPER_MODEL_SIZE=small` for better accuracy
3. Add logging to track detection rates across samples

### Medium-term
4. Implement full-audio Whisper transcription with word alignment
5. Multi-factor stress detection (amplitude + pitch + duration)
6. Dynamic breath filter threshold

### Long-term
7. Fine-tune Whisper on mumbled vocal samples
8. Investigate Whisper's word-level timestamps API

---

## Test Files

| File | Content | Syllables | Notes |
|------|---------|-----------|-------|
| `talk_to_me_i_said_what.m4a` | "talk to me I said what" | 6 | Good test for connected speech |
| `trying_to_take_my_time.m4a` | "trying to take my time" | 6 | Tests "ing" ending and soft syllables |

---

*Document created: 2025-12-28*
