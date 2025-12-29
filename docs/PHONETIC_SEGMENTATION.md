# 🔊 Phonetic Analysis & Syllable Segmentation

**Last Updated**: 2025-12-29  
**Version**: 1.1 (Phase D - Full-Audio Whisper + Syllable Validation)  
**Context**: Technical documentation for the phonetic analysis and syllable alignment system.

---

## 📋 Overview

The phonetic analysis system extracts IPA phonemes from detected audio segments to provide "sound-alike" hints for lyric generation. This helps the LLM understand what sounds the user is humming/singing.

### Key Features
- **Full-audio transcription**: Whisper processes entire audio for linguistic context
- **Word-level timestamps**: Accurate timing for each transcribed word
- **Syllable splitting**: Words split into syllables using onset maximization principle
- **Sequential alignment**: 1:1 mapping of syllables to detected segments

---

## 🔄 Pipeline Flow

```
Audio File
    │
    ▼
┌─────────────────────────┐
│  LibrosaAnalyzer        │  ← Detects segment onsets via spectral flux
│  - Onset detection      │
│  - BPM/duration         │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  WhisperPhoneticAnalyzer│  ← Full-audio transcription
│  - word_timestamps=True │
│  - Returns: [{word, start, end}, ...]
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  Syllable Splitting     │  ← Using g2p_en + onset maximization
│  - "asawa" → [a][sa][wa]│
│  - Consonants → following vowel
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  Sequential Alignment   │  ← 1:1 mapping
│  - syllable[0] → segment[0]
│  - syllable[1] → segment[1]
│  - ...
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  PivotJSON              │  ← Each segment has audio_phonemes
│  - "d er t" | "t uw" | "m iy" | ...
└─────────────────────────┘
```

---

## 🧠 Key Algorithms

### 1. Full-Audio Transcription

```python
# Whisper transcribes entire audio with word-level timestamps
result = whisper.transcribe(
    audio_16k,
    language="en",
    word_timestamps=True,  # KEY: Get timing per word
    temperature=0.0,       # Deterministic output
    condition_on_previous_text=True  # Use context
)

# Returns segments with words:
# [{"word": "talk", "start": 0.5, "end": 0.8}, ...]
```

### 2. Syllable Splitting (Onset Maximization)

English syllables follow the **onset maximization principle**: consonants prefer to attach to the **following** vowel, not the preceding one.

| Word | Naive Split | Correct Split |
|------|-------------|---------------|
| `asawa` | `[a-s] [a-w] [a]` | `[a] [s-a] [w-a]` |
| `hello` | `[hel] [lo]` | `[he] [llo]` |
| `trying` | `[try] [ing]` | `[try] [ing]` |

**Algorithm:**
1. Convert word to phonemes via g2p_en
2. Track `pending_consonants` buffer
3. When encountering a vowel:
   - If current syllable already has a vowel → save syllable, start new with pending consonants
   - Else → add pending consonants to current, then add vowel
4. Consonants after vowel go to `pending_consonants` (for next syllable onset)

### 3. Sequential Alignment

Simple 1:1 mapping preserving temporal order:

```python
syllables.sort(key=lambda x: x["start"])
for i in range(min(len(syllables), len(segments))):
    segment_phonemes[i] = syllables[i]["phonemes"]
```

---

## ⚙️ Configuration

```bash
# .env options

# Phonetic model: "whisper" (recommended) or "allosaurus"
PHONETIC_MODEL=whisper

# Whisper model size: tiny/base/small/medium/large
WHISPER_MODEL_SIZE=base

# Full-audio mode (recommended for accuracy)
WHISPER_USE_FULL_AUDIO=true

# Enable phonetic fallback classification
PHONETIC_FALLBACK_ENABLED=true

# Syllable detection validation (NEW)
WHISPER_VALIDATION_ENABLED=true
ADAPTIVE_DELTA_ENABLED=true
MIN_SEGMENT_DURATION=0.08
```

---

## 📊 Detection Rates

| Audio File | Segments | Aligned | Rate |
|------------|----------|---------|------|
| `talk_to_me_i_said_what.m4a` | 6 | 6 | 100% |
| `what_bout_you.m4a` | 3 | 3 | 100% |
| `trying_to_take_my_time.m4a` | 5 | 5 | 100% |

---

## 🔧 Classes & Methods

### WhisperPhoneticAnalyzer (`audio_engine.py`)

| Method | Purpose |
|--------|---------|
| `transcribe_full_audio(y, sr)` | Transcribe entire audio with word timestamps |
| `count_syllables_in_words(words)` | **NEW** - Count syllables using g2p_en |
| `_words_to_syllables_with_timing(words)` | Split words into syllables with estimated timing |
| `_align_words_to_segments(words, onsets, durations)` | Sequential syllable-to-segment assignment |
| `analyze_segments_full_audio(y, sr, onsets, durations)` | High-level API combining all steps |

### LibrosaAnalyzer (`audio_engine.py`)

| Method | Purpose |
|--------|---------|
| `analyze(audio_path)` | Main entry point for audio analysis |
| `_calculate_adaptive_delta(onset_env)` | **NEW** - Calculate per-file delta using CV |
| `_validate_with_whisper(y, sr, ...)` | **NEW** - Whisper-guided syllable validation |

### Module-Level Functions

| Function | Purpose |
|----------|---------|
| `get_whisper_analyzer()` | **NEW** - Singleton accessor for cached Whisper model |

### PhoneticAnalyzer (`audio_engine.py`)

| Method | Purpose |
|--------|---------|
| `analyze_segments(y, sr, onsets, durations)` | Main entry point; uses full-audio mode if configured |
| `analyze_segment(y_segment, sr)` | Single segment analysis (legacy/fallback) |

---

## 🔍 Troubleshooting

### Issue: Missing phonemes on some segments
**Cause**: More segments than syllables (Whisper detected fewer words)  
**Fix**: Fallback classification provides `[vowel]`/`[consonant]` tags

### Issue: Wrong transcription (e.g., "dirt" instead of "talk")
**Cause**: Mumbled/yaourt audio is intentionally unclear  
**Expected**: Whisper provides best-guess phonemes; actual words don't matter for rhythm

### Issue: Syllables split incorrectly
**Check**: Onset maximization logic in `_words_to_syllables_with_timing()`  
**Debug**: Print syllable list before assignment
