# Phonetic Update: Known Issues & Refinements Needed

**Last Updated**: 2025-12-28  
**Version**: 2.1-alpha (Post Initial Implementation)

---

## Summary of Issues Found

After implementing the phonetic "Sound-Alike" feature and testing with real vocal mumbles, several issues were identified that need refinement before the pipeline produces accurate prompts.

---

## Issue 1: Under-Detection of Syllables (CRITICAL)

### Observed Behavior
- **Input**: Vocal mumble of "Talk to me, I said what" (6 syllables)
- **Expected**: 6 segments detected
- **Actual**: 3 segments detected

### Root Cause
The `LibrosaAnalyzer` onset detection is configured with conservative parameters (`delta=0.1`) optimized for reducing false positives. However, this causes **under-detection** of syllables in continuous speech/mumbles.

### Impact
- LLM is asked to generate 3-syllable lines instead of 6
- Generated lyrics will be completely wrong length
- User has no way to manually correct syllable count

### Proposed Fixes
1. **Tune onset parameters**: Lower `delta` threshold for more sensitive detection
2. **Add manual syllable count override**: Let user specify expected syllable count
3. **Add Tap-to-Rhythm**: Let user manually tap syllable onsets (already in roadmap)
4. **Use multiple detection strategies**: Combine spectral flux with energy-based onset detection

---

## Issue 2: Long Segment Durations (HIGH)

### Observed Behavior
- Segment 1: 0.441s duration
- Segment 2: 1.045s duration (too long for single syllable)
- Segment 3: 0.200s duration

### Root Cause
When onset detection misses intermediate syllables, the duration stretches to cover multiple syllables as one segment.

### Impact
- Allosaurus analyzes the entire long segment, picking up multiple sounds
- Phoneme output like `tʂʰ ʌ m e` contains sounds from multiple syllables
- Sustain detection incorrectly marks multi-syllable segments as "sustained"

### Proposed Fixes
1. **Split long segments**: Automatically sub-divide segments > 0.5s
2. **Use Allosaurus phone boundaries**: Allosaurus can output timestamped phones
3. **Energy-based sub-segmentation**: Split on energy valleys within segments

---

## Issue 3: Phoneme Quality (MEDIUM)

### Observed Behavior
- Mumble: "Talk to me" → Detected: `t͡ɕ ʌ ɒ | tʂʰ ʌ m e`
- Expected IPA: `t ɔ k t u m i`

### Analysis
- `t͡ɕ` (voiceless alveolo-palatal affricate) is close to "t" + "ch" sounds
- `ʌ` (schwa-like) is reasonable for unstressed vowels
- `tʂʰ` (retroflex aspirated) picked up "to" but with accent characteristics
- The phonemes are **phonetically similar** but not exact matches

### Impact
- Phonetic matching score is low (0.00-0.08 in tests)
- LLM gets approximate sound hints but not precise matches

### Assessment
This is **partially expected behavior** - Allosaurus recognizes universal phones, which may differ from English-specific phonemes. The broad phonetic class matching (consonant vs vowel) helps, but exact matching is unreliable.

### Proposed Fixes
1. **Use broad phonetic classes only**: Match by manner (plosive, nasal, vowel) not exact IPA
2. **Focus on vowel matching**: Vowels are more perceptually salient
3. **Increase phonetic weight only when confidence is high**

---

## Issue 4: Missing Phonemes on Short Segments (LOW)

### Observed Behavior
- Segment 3 (0.2s): No phonemes detected `(none)`

### Root Cause
The `min_duration` check (0.05s) should pass, but Allosaurus may fail on very short audio clips.

### Proposed Fixes
1. **Pad short segments**: Add silence padding before analysis
2. **Handle gracefully**: Already returns empty string (correct behavior)

---

## Recommendations for Next Phase

### Priority 1: Fix Syllable Detection
- [ ] Experiment with lower `delta` values (0.05, 0.07)
- [ ] Test with energy-based onset detection as alternative
- [ ] Implement manual syllable count override in API
- [ ] Add Tap-to-Rhythm feature for manual onset marking

### Priority 2: Improve Segment Quality
- [ ] Implement automatic segment splitting for durations > 0.5s
- [ ] Use Allosaurus with `timestamp=True` for sub-segmentation

### Priority 3: Refine Phonetic Matching
- [ ] Simplify to broad phonetic class matching only
- [ ] Weight vowel sounds more heavily than consonants
- [ ] Add confidence score from Allosaurus to weight phonetic score

### Priority 4: UI/UX Improvements
- [ ] Display detected segments visually for user validation
- [ ] Allow user to edit/split/merge segments before generation
- [ ] Show phonetic transcription for human review

---

## Test Command

To reproduce the issues:
```powershell
python tests/test_pipeline_inspector.py "audio samples/test_audio_2-1.m4a"
```

To run without phonetic analysis (faster):
```powershell
python tests/test_pipeline_inspector.py "audio samples/test_audio_2-1.m4a" --no-phonetic
```
