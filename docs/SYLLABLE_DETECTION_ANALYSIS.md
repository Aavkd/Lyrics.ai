# 🎯 Syllable Detection Analysis

**Date:** 2025-12-29  
**Status:** ✅ Overhaul Complete  
**Context:** Improved from 3/7 acceptable to **6/7 acceptable** (≤1 error) with Whisper-guided validation.

---

## 📊 Test Results Summary (After Full Overhaul)

| File | Expected | Detected | Error | Status |
|------|----------|----------|-------|--------|
| `talk_to_me_i_said_what.m4a` | 6 | 6 | 0 | ✅ Perfect |
| `99_problems.m4a` | 5 | 4 | -1 | ⚠️ Acceptable |
| `what_bout_you.m4a` | 3 | 3 | 0 | ✅ Perfect |
| `everybody_equal.m4a` | 6 | 5 | -1 | ⚠️ Acceptable |
| `mumble_on_this_beat.m4a` | 5 | 5 | 0 | ✅ Perfect |
| `oh_ma_oh_ma_on_my_tec_nine.m4a` | 8 | 10 | +2 | ❌ Over-detection |
| `trying_to_take_my_time.m4a` | 6 | 5 | -1 | ⚠️ Acceptable |

**Summary:** **3/7 perfect, 6/7 acceptable** (≤1 error). Total error reduced from 10 to **5**.

---

## 🔍 Root Cause Analysis

### Issue 1: Spectral Flux Sensitivity (OVER-DETECTION)

**Location:** `audio_engine.py` → `LibrosaAnalyzer._detect_onsets_spectral()`

**Problem:** The `ONSET_DELTA` parameter (default: 0.04 in `.env`, 0.05 in config default) controls detection sensitivity. Lower values = more onsets detected.

```python
# Current code (line 1115)
delta=self.onset_delta,  # Uses config.ONSET_DELTA (0.04-0.05)
```

**Why It Fails:**
- Spectral flux detects ANY spectral change, not just syllable onsets
- Consonant clusters (e.g., "mble" in "mumble") create micro-onsets
- Pitch variations within sustained vowels trigger false positives
- Different recording styles have different noise floors

**Evidence:**
- `mumble_on_this_beat.m4a`: 8 detected vs 5 expected (+3)
  - "Mumble" likely detected as "Mum-b-le" (3 onsets)
  - Additional micro-onset in "beat"

---

### Issue 2: No Adaptive Thresholding

**Problem:** All audio files use the same fixed `ONSET_DELTA=0.04`, but different recordings have different:
- Noise floor levels
- Dynamic range
- Articulation clarity
- Recording quality

**Current Approach:**
```python
# LibrosaAnalyzer.analyze() - line 1239
spectral_onsets = self._detect_onsets_spectral(y, sr, onset_env)
# Uses global config.ONSET_DELTA for all files
```

**Better Approach (Not Implemented):**
- Calculate audio-specific threshold based on onset strength envelope statistics
- Use `median + k * MAD` (Median Absolute Deviation) for adaptive thresholding

---

### Issue 3: Minimum Segment Duration Not Enforced

**Problem:** Very short detected segments (e.g., 70ms) are kept even though real syllables are typically >100ms.

**Evidence from test:**
```
99_problems.m4a - Segment 2: 0.070s duration  ← Suspiciously short
mumble_on_this_beat.m4a - Segment 2: 0.116s duration
```

**Current Filter:**
- Breath filter only removes segments with BOTH:
  - Duration < 150ms AND
  - Energy < 15% of max
- Short segments with moderate energy are kept (false positives)

---

### Issue 4: Under-Detection from Aggressive Breath Filter

**Location:** `audio_engine.py` → `PivotFormatter._filter_low_energy_segments()`

**Problem:** The breath filter uses:
- `min_energy_ratio = 0.15` (15% of max energy)
- `max_short_duration = 0.15` (150ms)

**Evidence:**
- `trying_to_take_my_time.m4a`: 1 syllable filtered as breath
- Soft-spoken syllables with low energy get incorrectly removed

---

### Issue 5: Spectral Flux Detects Pitch Changes, Not Just Onsets

**Technical Issue:** Spectral flux measures change in spectral content between frames. This triggers on:
- ✅ True syllable onsets (desired)
- ❌ Pitch slides within sustained vowels
- ❌ Vibrato modulation
- ❌ Consonant articulation within syllables (e.g., "l" in "mumble")

---

## 📈 Current Detection Pipeline

```
Audio File
    │
    ▼
┌─────────────────────────────────┐
│  Spectral Flux Detection        │  ← Problem: Fixed delta=0.04
│  - librosa.onset.onset_detect() │     Too sensitive for some audio
│  - delta=ONSET_DELTA            │
└─────────────────────────────────┘
    │ (if < 3 onsets)
    ▼
┌─────────────────────────────────┐
│  Energy Fallback Detection      │  ← Only triggers for near-silence
│  - RMS peak detection           │
│  - threshold=0.15               │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  Long Segment Splitting         │  ← Only for >1.0s segments
│  - Split at energy valleys      │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  Breath/Noise Filtering         │  ← Can over-filter soft syllables
│  - Remove if <150ms AND <15%    │
└─────────────────────────────────┘
    │
    ▼
  Final Segments
```

---

## 💡 Implemented Solutions

### Solution 1: Adaptive Delta Based on Audio Statistics ✅ IMPLEMENTED

Instead of fixed `ONSET_DELTA`, now uses coefficient of variation (CV) to adjust ±30%:

```python
def _calculate_adaptive_delta(onset_env):
    """Calculate adaptive onset threshold based on audio statistics."""
    cv = std_env / mean_env  # Coefficient of variation
    
    # Higher CV = more peaks = need higher delta
    adjustment = 0.8 + 0.4 * min(cv, 1.5) / 1.5
    return self.onset_delta * adjustment  # ±30% range
```

**Config:** `ADAPTIVE_DELTA_ENABLED=true`, `ADAPTIVE_DELTA_FALLBACK=true`

### Solution 2: Minimum Segment Duration Filter ✅ IMPLEMENTED

Short segments (<80ms) are now merged with neighbors:

```python
MIN_SEGMENT_DURATION = 0.08  # 80ms minimum (configurable via .env)

def _filter_short_segments(onset_times, durations):
    """Merge segments shorter than minimum syllable duration."""
    # If segment is too short, merge with next segment
```

**Config:** `MIN_SEGMENT_DURATION=0.08`

### Solution 3: Configurable Breath Filter ✅ IMPLEMENTED

Breath filter thresholds are now configurable:

**Config options:**
- `BREATH_FILTER_ENERGY_RATIO=0.15` (energy threshold)
- `BREATH_FILTER_MAX_DURATION=0.15` (duration threshold)

### Solution 4: Whisper-Guided Syllable Validation ✅ IMPLEMENTED

The most impactful fix: uses Whisper transcription to validate and adjust detection:

```python
def _validate_with_whisper(y, sr, onset_env, initial_onsets, initial_delta):
    """Use Whisper to validate and adjust syllable detection."""
    # Get expected syllable count from Whisper + g2p_en
    words = get_whisper_analyzer().transcribe_full_audio(y, sr)
    expected = count_syllables_in_words(words)
    
    # If within 30% tolerance, keep initial detection
    if abs(initial_onsets - expected) / expected <= 0.3:
        return initial_onsets, initial_delta
    
    # Otherwise, test delta range (0.5x to 2.5x) to find best match
    for test_delta in [0.5x, 0.7x, 1.0x, 1.3x, 1.5x, 2.0x, 2.5x]:
        # Pick delta that matches expected syllables best
```

**Key improvement:** `mumble_on_this_beat.m4a` went from +3 error to **0** (perfect!)

### Solution 5: Whisper Singleton Caching ✅ IMPLEMENTED

Whisper model loads only once per Python session via module-level singleton:

```python
_WHISPER_ANALYZER_SINGLETON = None

def get_whisper_analyzer():
    global _WHISPER_ANALYZER_SINGLETON
    if _WHISPER_ANALYZER_SINGLETON is None:
        _WHISPER_ANALYZER_SINGLETON = WhisperPhoneticAnalyzer()
    return _WHISPER_ANALYZER_SINGLETON
```

### Solution 4: Syllable-Aware Onset Detection

Use Whisper's word timestamps to guide onset detection:

```python
# Instead of blind spectral flux:
# 1. Get Whisper words with timing
# 2. For each word, estimate syllable count via g2p
# 3. Distribute syllable onsets within word's time range
# 4. Use energy peaks within word boundaries to refine
```

---

## ⚙️ Quick Fixes (Config Tuning)

For immediate improvement without code changes:

### For Over-Detection Issues:
```bash
# .env - Increase onset delta to reduce sensitivity
ONSET_DELTA=0.07  # or 0.08 for very noisy audio
```

### For Under-Detection Issues:
```bash
# .env - Reduce breath filter aggressiveness
# (Note: not currently configurable - needs code change)
```

---

## 🎯 Priority Recommendations

| Priority | Solution | Effort | Impact |
|----------|----------|--------|--------|
| 🔴 High | Adaptive delta per-file | Medium | Fixes over-detection |
| 🔴 High | Whisper-guided syllable count | Low | Prevents major errors |
| 🟡 Medium | Minimum segment duration | Low | Reduces micro-segments |
| 🟡 Medium | Configurable breath filter | Low | Fixes under-detection |
| 🟢 Low | Syllable-aware detection | High | Best long-term solution |

---

## 📝 Files to Modify

1. **`audio_engine.py`** (lines 1089-1118)
   - `LibrosaAnalyzer._detect_onsets_spectral()` - Add adaptive delta
   - `LibrosaAnalyzer.analyze()` - Calculate per-file threshold

2. **`config.py`** (lines 128-141)
   - Add `BREATH_FILTER_THRESHOLD` config
   - Add `MIN_SEGMENT_DURATION` config

3. **`audio_engine.py`** (lines 1478-1547)
   - `PivotFormatter._filter_low_energy_segments()` - Make thresholds configurable
