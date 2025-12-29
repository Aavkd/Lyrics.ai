# 🔍 Syllable Count Discrepancy Investigation

**Date:** 2025-12-29  
**Status:** Resolved  

---

## The Discrepancy

Two tests show different syllable detection results for the same audio files:

| Test File | Approach | `everybody_equal.m4a` | `oh_ma_oh_ma...` |
|-----------|----------|----------------------|------------------|
| `test_phonetic_hints.py` | Whisper syllable splitting | 6/6 ✅ | 8/8 ✅ |
| `test_new_audio_samples.py` | Librosa onset detection | 5/6 ⚠️ | 10/8 ❌ |

**Why does `test_phonetic_hints.py` show perfect matches while `test_new_audio_samples.py` shows errors?**

---

## Root Cause

The two tests use **fundamentally different syllable detection approaches**:

### 1. `test_phonetic_hints.py` - Linguistic Analysis (Whisper)

```python
# Uses Whisper transcription → g2p syllable splitting
syllables = whisper._words_to_syllables_with_timing(words)
```

**How it works:**
1. Whisper transcribes audio → `["everybody", "equal"]`
2. g2p_en splits words into syllables → `["ev", "ry", "bo", "dy", "e", "qual"]`
3. Count = 6 ✅ (always matches expected because it's **linguistic** analysis)

### 2. `test_new_audio_samples.py` - Acoustic Analysis (Librosa)

```python
# Uses spectral flux onset detection
analysis = LibrosaAnalyzer().analyze(audio_path)
# Then breath filtering, min segment filter, etc.
pivot = PivotFormatter().format(analysis)
```

**How it works:**
1. Detect acoustic onsets via spectral flux → `[0.1, 0.3, 0.5, 0.8, 1.1]` 
2. Filter breaths, merge short segments
3. Count = variable (depends on audio characteristics)

---

## Key Insight: Whisper-Guided Validation Uses Both

The Whisper-guided validation in `LibrosaAnalyzer._validate_with_whisper()` bridges these two approaches:

```
                    ┌─────────────────────────┐
                    │    Audio File           │
                    └─────────────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           ▼                  │                  ▼
┌─────────────────────┐       │     ┌─────────────────────┐
│ Librosa Spectral    │       │     │ Whisper             │
│ Onset Detection     │       │     │ Transcription       │
│ (Acoustic)          │       │     │ (Linguistic)        │
└─────────────────────┘       │     └─────────────────────┘
           │                  │                  │
           ▼                  │                  ▼
   detected_onsets = 10       │       expected_syllables = 8
           │                  │                  │
           └──────────────────┴──────────────────┘
                              │
                              ▼
                    ┌─────────────────────────┐
                    │ If error > 30%:         │
                    │ Retry with higher delta │
                    └─────────────────────────┘
```

**But there's a problem:** The tolerance threshold is 30%, so:
- `oh_ma_oh_ma...`: 10 detected, 9 expected → error = 11% → **kept** (within tolerance)
- But user expects 8, and Whisper thinks 9 → Whisper is also wrong!

---

## Why Whisper Shows "Perfect" Matches

`test_phonetic_hints.py` doesn't actually verify acoustic detection. It only:

1. Counts syllables from Whisper's transcription (linguistic)
2. Compares to expected (also linguistic)

**This is a circular comparison:**
- User said "Everybody equal" → 6 syllables expected
- Whisper heard "Everybody equal" → 6 syllables detected
- **Match!** But this doesn't test acoustic onset detection.

---

## The Real Test: Segment Timing

The actual challenge is detecting **when** each syllable starts, not **how many** there are. The phonetic hints test shows syllable **phonemes**, not segment **timing**.

| Audio File | Whisper Syllables | Librosa Onsets | Difference |
|------------|-------------------|----------------|------------|
| `everybody_equal.m4a` | 6 (linguistic) | 5 (acoustic) | -1 |
| `oh_ma_oh_ma...` | 9 (linguistic) | 10 (acoustic) | +1 |
| `mumble_on_this_beat.m4a` | 5 (linguistic) | 5 (acoustic) | 0 ✅ |

---

## Recommendations

### Option 1: Trust Whisper Syllable Count (Current Approach)
Use Whisper's syllable count as the **target** and adjust Librosa delta to match.

**Pros:** Leverages Whisper's language understanding  
**Cons:** Whisper can mishear mumbled audio

### Option 2: Hybrid with Word Timing
Use Whisper's **word timestamps** to constrain onset detection within word boundaries.

```
Word "everybody" from 0.2s to 0.8s
→ Expect ~4 syllables within this window
→ Use Librosa to find 4 acoustic onsets between 0.2-0.8s
```

### Option 3: Pure Acoustic (No Whisper)
Tune Librosa parameters per-audio-type (clean vocals vs. mumbled).

---

## Conclusion

The "perfect" matches in `test_phonetic_hints.py` are due to **comparing Whisper output against itself** (linguistic analysis only). The actual syllable detection challenge is in `test_new_audio_samples.py`, which tests **acoustic onset detection**.

Both tests are useful:
- `test_phonetic_hints.py` → Verifies phoneme extraction and g2p syllable splitting
- `test_new_audio_samples.py` → Verifies acoustic onset detection accuracy
