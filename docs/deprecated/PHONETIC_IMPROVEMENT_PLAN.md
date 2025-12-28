# Phonetic Detection Improvement Plan

**Date:** December 28, 2025  
**Version:** 1.0  
**Objective:** Achieve >95% phoneme detection rate for all audio segments

---

## 1. Executive Summary

### The Problem
The current phonetic analysis pipeline using Allosaurus achieves only **25-67% detection rate** across test samples. Several syllables receive `(none)` for phonemes, which degrades the LLM's ability to generate sound-alike lyrics.

### Test Results (Current State)

| Audio File | Expected | Phonemes Detected | Detection Rate |
|------------|----------|-------------------|----------------|
| `everybody_equal.m4a` | 8 | 2 | **25%** ❌ |
| `mumble_on_this_beat.m4a` | 8 | 3 | **37.5%** ❌ |
| `trying_to_take_my_time.m4a` | 5 | 3 | **60%** ⚠️ |
| `talk_to_me_i_said_what.m4a` | 6 | 4 | **67%** ⚠️ |

### Target
- **Immediate:** >80% detection rate
- **Full system:** >95% detection rate with fallback mechanisms

---

## 2. Root Cause Analysis

### Issue 1: Segments Too Short for Allosaurus

**Problem:** Allosaurus requires sufficient audio context to recognize phonemes. The current `min_duration=0.05` (50ms) threshold allows segments that are too short for reliable recognition.

**Evidence:**
```
Segment 1: 0.139s duration → (none)   # Too short
Segment 5: 0.200s duration → (none)   # Short, context-poor
```

**Recommendation:** 
- Increase minimum analysis duration to `min_duration=0.10` (100ms)
- Add **padding** before and after each segment (50-100ms on each side) to give Allosaurus more acoustic context

### Issue 2: No Context Padding

**Problem:** Allosaurus analyzes each segment in isolation. Phonemes at segment boundaries are cut off, causing recognition failures.

**Evidence:**
- First and last segments consistently fail more often
- Syllables like "I", "to", "me" (short vowels/consonants) are missed

**Recommendation:**
- Add configurable padding: `PHONETIC_PADDING=0.05` (50ms before and after segment)
- Extract `segment_audio = y[start - padding : end + padding]` instead of just `y[start:end]`

### Issue 3: No Fallback When Allosaurus Fails

**Problem:** When Allosaurus returns empty, there's no alternative detection. The segment gets `(none)` which provides no guidance to the LLM.

**Recommendation:**
- **Tier 1 Fallback:** Re-analyze with expanded segment boundaries (+100ms padding)
- **Tier 2 Fallback:** Use simple spectral analysis to classify as vowel/consonant
- **Tier 3 Fallback:** Mark as "unknown" but still provide duration-based hints

### Issue 4: Single-Pass Analysis

**Problem:** Allosaurus is called once per segment. If it fails, there's no retry with adjusted parameters.

**Recommendation:**
- Implement retry with increasing padding: 50ms → 100ms → 150ms
- Use segment-merge analysis for very short segments (combine adjacent short segments)

### Issue 5: Allosaurus Model Limitations

**Problem:** Allosaurus is optimized for clean speech, not mumbled/sung vocals.

**Evidence:**
- IPA symbols returned are often universal phonemes, not English-specific
- Confidence scores not exposed (Allosaurus doesn't provide per-phone confidence)

**Recommendation:**
- Consider alternative models for sung vocals:
  - **Whisper** (OpenAI): Better for varied audio quality
  - **wav2vec2** (Meta): Phoneme-level recognition pretrained
  - **Speechbrain**: Phoneme recognition with fine-tuning support
- Long-term: Train/fine-tune on mumbled/sung vocal data

---

## 3. Proposed Implementation

### Phase A: Quick Wins (High Impact, Low Effort)

#### A.1: Add Segment Padding

**File:** `audio_engine.py` → `PhoneticAnalyzer.analyze_segments()`

```python
# Before (current):
start_sample = int(onset_time * sr)
end_sample = int((onset_time + duration) * sr)

# After (with padding):
padding_seconds = 0.05  # 50ms padding
padding_samples = int(padding_seconds * sr)
start_sample = max(0, int(onset_time * sr) - padding_samples)
end_sample = min(len(y), int((onset_time + duration) * sr) + padding_samples)
```

#### A.2: Increase Minimum Duration

**File:** `audio_engine.py` → `PhoneticAnalyzer.analyze_segment()`

```python
# Before:
min_duration: float = 0.05

# After:
min_duration: float = 0.10  # 100ms minimum
```

#### A.3: Add Retry with Expanded Padding

**File:** `audio_engine.py` → `PhoneticAnalyzer.analyze_segment()`

```python
def analyze_segment(self, y_segment, sr, min_duration=0.10):
    # First attempt
    ipa = self._run_allosaurus(y_segment, sr)
    
    # If failed and segment is short, try with expanded context
    if not ipa and len(y_segment) / sr < 0.2:
        # This would require passing the full audio and segment bounds
        # to enable re-extraction with more context
        pass
    
    return ipa
```

### Phase B: Architectural Improvements (Medium Effort)

#### B.1: Merge Adjacent Short Segments

For very short consecutive segments (each <100ms), merge them for analysis, then split the resulting phonemes proportionally.

```python
def merge_short_segments(onset_times, durations, min_merge_duration=0.15):
    """Merge adjacent segments shorter than threshold."""
    merged = []
    i = 0
    while i < len(onset_times):
        if durations[i] < min_merge_duration and i + 1 < len(onset_times):
            # Check if next segment is also short and close
            gap = onset_times[i+1] - (onset_times[i] + durations[i])
            if gap < 0.05 and durations[i+1] < min_merge_duration:
                # Merge segments
                merged_duration = onset_times[i+1] + durations[i+1] - onset_times[i]
                merged.append((onset_times[i], merged_duration, [i, i+1]))
                i += 2
                continue
        merged.append((onset_times[i], durations[i], [i]))
        i += 1
    return merged
```

#### B.2: Add Vowel/Consonant Classification Fallback

When Allosaurus fails, use spectral features to classify the segment:

```python
def classify_sound_type(y_segment, sr):
    """Fallback: classify as vowel, consonant, or fricative."""
    # Spectral centroid (high = fricative, low = vowel)
    centroid = librosa.feature.spectral_centroid(y=y_segment, sr=sr)
    mean_centroid = np.mean(centroid)
    
    # Zero crossing rate (high = fricative/plosive, low = vowel)
    zcr = librosa.feature.zero_crossing_rate(y_segment)
    mean_zcr = np.mean(zcr)
    
    if mean_zcr > 0.1:
        return "[consonant]"  # Fricative/plosive
    elif mean_centroid < 2000:
        return "[vowel]"  # Open vowel sound
    else:
        return "[mid]"  # Uncertain
```

### Phase C: Alternative Model Integration (Higher Effort)

#### C.1: Whisper-based Phoneme Extraction

OpenAI's Whisper has better robustness to audio quality variations:

```python
# Option: Use whisper for transcription, then g2p for phonemes
import whisper

class WhisperPhoneticAnalyzer:
    def __init__(self):
        self.model = whisper.load_model("small")
        self.g2p = G2p()  # For English phoneme conversion
    
    def analyze_segment(self, audio_path, start, end):
        # Transcribe segment
        result = self.model.transcribe(audio_path)
        text = result["text"]
        
        # Convert to phonemes via g2p_en
        phonemes = self.g2p(text)
        return phonemes
```

#### C.2: wav2vec2 Phoneme Recognition

Meta's wav2vec2 can be fine-tuned for phoneme recognition:

```python
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

# Pre-trained phoneme model
model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-lv-60-espeak-cv-ft")
processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-lv-60-espeak-cv-ft")
```

---

## 4. Configuration Additions

Add new environment variables to `.env`:

```ini
# Phonetic Analysis Settings
PHONETIC_ENABLED=true
PHONETIC_MIN_DURATION=0.10       # Minimum segment duration for analysis
PHONETIC_PADDING=0.05            # Padding on each side of segment (seconds)
PHONETIC_RETRY_PADDING=0.10      # Retry padding when first attempt fails
PHONETIC_FALLBACK_ENABLED=true   # Enable vowel/consonant fallback
```

---

## 5. Verification Plan

### Test 1: Pipeline Inspector Comparison

```powershell
# Before changes
python tests/test_pipeline_inspector.py "audio samples/talk_to_me_i_said_what.m4a"
# Note phoneme count: X / 6

# After changes
python tests/test_pipeline_inspector.py "audio samples/talk_to_me_i_said_what.m4a"
# Expect phoneme count: 6 / 6
```

### Test 2: Full Audio Sample Suite

Run all 6 audio samples and compare detection rates:

```powershell
# Create batch test script
foreach ($file in (Get-ChildItem "audio samples/*.m4a")) {
    python tests/test_pipeline_inspector.py $file.FullName
}
```

**Success criteria:** All samples achieve >80% phoneme detection.

### Test 3: Unit Tests for Padding Logic

Create `tests/test_phonetic_padding.py`:
- Verify padding is applied correctly
- Verify padding doesn't exceed audio boundaries
- Verify short segments get merged analyzed

### Test 4: Manual Verification

Using `talk_to_me_i_said_what.m4a`:
- **Expected phonemes:** "talk" (tɔːk), "to" (tuː), "me" (miː), "I" (aɪ), "said" (sɛd), "what" (wʌt)
- **Verify:** Each phoneme approximates the expected sound

---

## 6. Implementation Priority

| Priority | Task | Effort | Impact |
|----------|------|--------|--------|
| **P0** | Add segment padding (50ms) | Low | High |
| **P0** | Increase min_duration to 100ms | Low | Medium |
| **P1** | Add retry with expanded padding | Medium | High |
| **P1** | Add vowel/consonant fallback | Medium | Medium |
| **P2** | Merge adjacent short segments | Medium | Medium |
| **P3** | Integrate Whisper as alternative | High | High |
| **P3** | Fine-tune wav2vec2 for vocals | Very High | Very High |

---

## 7. Estimated Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase A (Quick Wins) | 2-3 hours | >80% detection rate |
| Phase B (Architecture) | 4-6 hours | >90% detection rate |
| Phase C (Alternative Models) | 1-2 weeks | >95% detection rate |

---

## 8. Summary of Changes Required

### Files to Modify

1. **`audio_engine.py`**
   - `PhoneticAnalyzer.analyze_segments()`: Add padding logic
   - `PhoneticAnalyzer.analyze_segment()`: Increase min_duration, add retry
   - Add `classify_sound_type()` fallback function

2. **`config.py`**
   - Add `PHONETIC_MIN_DURATION`, `PHONETIC_PADDING`, `PHONETIC_FALLBACK_ENABLED`

3. **`.env.example`**
   - Document new phonetic configuration options

4. **`tests/test_phonetic_padding.py`** (NEW)
   - Unit tests for padding and fallback logic

---

## 9. Next Steps

1. **User Decision Required:**
   - Implement Phase A only (quick wins)?
   - Implement Phase A + B (full improvement)?
   - Include Phase C (alternative models)?

2. **Trade-offs:**
   - Phase A: Fastest, may get 80% detection
   - Phase B: More robust, 90%+ detection
   - Phase C: Best quality, requires additional dependencies (Whisper/wav2vec2)

---

*Document created during phonetic detection investigation on 2025-12-28.*
