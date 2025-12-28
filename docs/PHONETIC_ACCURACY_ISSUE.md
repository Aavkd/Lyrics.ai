# Phonetic Recognition Accuracy Issue

**Date:** 2025-12-28  
**Status:** Known Limitation  
**Severity:** Medium - Affects LLM guidance quality

---

## Summary

Allosaurus phoneme recognition produces **incorrect IPA tokens** for mumbled/sung vocals, even when detection rate is high. This is a fundamental model limitation, not a code bug.

---

## Evidence

**Test file:** `audio samples/talk_to_me_i_said_what.m4a`  
**Spoken content:** "talk to me I said what" (6 syllables)

| Syllable | Expected Word | Expected IPA | Allosaurus Output | Match? |
|----------|---------------|--------------|-------------------|--------|
| 1 | talk | /tɔːk/ | [vowel] (fallback) | ❌ |
| 2 | to | /tuː/ | tʂ ɹ̩ ɒ | ❌ |
| 3 | me | /miː/ | tʂ ɨ ŋ̟ ә m | ❌ |
| 4 | I | /aɪ/ | m e | ❌ |
| 5 | said | /sɛd/ | ɒ | ❌ |
| 6 | what | /wʌt/ | tʲ ɾ ɒ | ⚠️ Partial |

**Detection Rate:** 83.3% (5/6 with 1 fallback)  
**Accuracy Rate:** ~0% (phonemes don't match expected sounds)

---

## Root Cause

Allosaurus is a **universal phone recognizer** trained on clean multilingual speech. It struggles with:

1. **Mumbled vocals** - Unclear articulation
2. **Sung audio** - Pitch variations distort formants
3. **Non-studio quality** - Background noise, compression artifacts
4. **Context-free recognition** - No language model to correct errors

The model outputs IPA tokens from its ~200 universal phone inventory, but these don't map to the actual English sounds being produced.

---

## Impact on LLM Generation

The phonetic hints sent to the LLM are misleading:

```markdown
## Phonetic Hints (Sound-Alike)
- Syllable 1 sounds like: **/[vowel]/**     ← Should be "talk" /tɔːk/
- Syllable 2 sounds like: **/tʂ ɹ̩ ɒ/**      ← Should be "to" /tuː/
```

This causes the LLM to generate lyrics that don't match the original vocal sounds, defeating the purpose of phonetic guidance.

---

## Implemented Mitigations (Phase A & B)

| Feature | Benefit | Limitation |
|---------|---------|------------|
| Segment padding (+50ms) | More context for Allosaurus | Doesn't fix accuracy |
| Retry with expanded padding | Catches edge cases | Doesn't fix accuracy |
| Fallback classification | Returns `[vowel]`/`[consonant]` | Generic, no specific sounds |
| Increased min_duration | Filters noise | Doesn't fix accuracy |

---

## Recommended Solution: Phase C

Replace Allosaurus with **Whisper + g2p** pipeline:

```
Audio Segment → Whisper (transcribe) → "talk" → g2p_en → /tɔːk/
```

### Advantages
- Whisper handles noisy/mumbled audio better
- Returns actual English words (context-aware)
- g2p_en converts words to accurate English phonemes

### Implementation Path

1. Add `PHONETIC_MODEL` config option (`allosaurus` | `whisper`)
2. Create `WhisperPhoneticAnalyzer` class
3. Use OpenAI Whisper (`small` or `base` model)
4. Convert transcribed words to IPA via g2p_en
5. Fall back to Allosaurus if Whisper returns empty

### Dependencies
- `openai-whisper` package (~1.5GB model download)
- GPU recommended but CPU works

---

## Configuration Added

These config options were added but don't solve the accuracy issue:

```ini
PHONETIC_ENABLED=true          # Enable phonetic analysis
PHONETIC_MIN_DURATION=0.10     # 100ms minimum segment
PHONETIC_PADDING=0.05          # 50ms context padding
PHONETIC_RETRY_PADDING=0.10    # 100ms retry padding
PHONETIC_FALLBACK_ENABLED=true # Vowel/consonant fallback
```

---

## Files Modified

- `config.py` - Added 5 phonetic config properties
- `audio_engine.py` - Enhanced `PhoneticAnalyzer` with padding, retry, fallback
- `.env.example` - Documented new config options
- `tests/test_phonetic_padding.py` - New test suite (8 tests)

---

*Document created: 2025-12-28*
