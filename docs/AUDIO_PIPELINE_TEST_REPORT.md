# 🎵 Audio Pipeline Test Report

**Generated:** 2025-12-28 20:56  
**Test Type:** Syllable Detection Analysis (No LLM)  
**Phoneme Analysis:** Disabled (testing audio/syllable pipeline only)

---

## 📋 Test Summary

| Metric | Value |
|--------|-------|
| Files Tested | 6 |
| Perfect Matches | 3/6 |
| Close Matches (±1) | 4/6 |
| Total Expected Syllables | 31 |
| Total Detected Syllables | 35 |
| Total Absolute Error | 6 |

---

## 📊 Results by File

### talk_to_me_i_said_what.m4a

**Status:** ✅ PASS

| Property | Value |
|----------|-------|
| Expected Phrase | "Talk to me, I said what" |
| Syllable Breakdown | Talk(1) to(1) me(1) I(1) said(1) what(1) |
| Expected Syllables | 6 |
| Detected Syllables | 6 |
| Error | 0 |
| Tempo | 143.55 BPM |
| Duration | 2.965s |

**Detected Segments:**

| # | Start (s) | Duration (s) | Stressed | Sustained | Pitch |
|---|-----------|--------------|----------|-----------|-------|
| 1 | 0.046 | 0.302 |  |  | mid |
| 2 | 0.348 | 0.441 | 🔊 | ⏸ | low |
| 3 | 0.789 | 0.209 | 🔊 |  | low |
| 4 | 0.998 | 0.836 |  | ⏸ | low |
| 5 | 1.834 | 0.186 |  |  | low |
| 6 | 2.020 | 0.200 |  |  | low |

---

### 99_problems.m4a

**Status:** ✅ PASS

| Property | Value |
|----------|-------|
| Expected Phrase | "99 problems" |
| Syllable Breakdown | Nine(1) ty(1) nine(1) prob(1) lems(1) |
| Expected Syllables | 5 |
| Detected Syllables | 5 |
| Error | 0 |
| Tempo | 71.78 BPM |
| Duration | 2.603s |

**Detected Segments:**

| # | Start (s) | Duration (s) | Stressed | Sustained | Pitch |
|---|-----------|--------------|----------|-----------|-------|
| 1 | 0.186 | 0.372 |  |  | low |
| 2 | 0.557 | 0.070 | 🔊 |  | low |
| 3 | 0.627 | 0.441 |  | ⏸ | low |
| 4 | 1.068 | 0.093 |  |  | low |
| 5 | 1.161 | 0.200 |  |  | low |

---

### everybody_equal.m4a

**Status:** ❌ FAIL

| Property | Value |
|----------|-------|
| Expected Phrase | "Everybody equal" |
| Syllable Breakdown | Ev(1) ry(1) bo(1) dy(1) e(1) qual(1) |
| Expected Syllables | 6 |
| Detected Syllables | 8 |
| Error | +2 |
| Tempo | 136.0 BPM |
| Duration | 2.389s |

**Detected Segments:**

| # | Start (s) | Duration (s) | Stressed | Sustained | Pitch |
|---|-----------|--------------|----------|-----------|-------|
| 1 | 0.046 | 0.163 |  |  | mid |
| 2 | 0.209 | 0.279 | 🔊 |  | mid |
| 3 | 0.488 | 0.186 |  |  | mid |
| 4 | 0.673 | 0.395 |  |  | mid |
| 5 | 1.068 | 0.093 |  |  | mid |
| 6 | 1.161 | 0.604 | 🔊 | ⏸ | mid |
| 7 | 1.765 | 0.232 |  |  | mid |
| 8 | 1.997 | 0.200 |  |  | mid |

---

### mumble_on_this_beat.m4a

**Status:** ❌ FAIL

| Property | Value |
|----------|-------|
| Expected Phrase | "Mumble on this beat" |
| Syllable Breakdown | Mum(1) ble(1) on(1) this(1) beat(1) |
| Expected Syllables | 5 |
| Detected Syllables | 8 |
| Error | +3 |
| Tempo | 66.26 BPM |
| Duration | 2.24s |

**Detected Segments:**

| # | Start (s) | Duration (s) | Stressed | Sustained | Pitch |
|---|-----------|--------------|----------|-----------|-------|
| 1 | 0.046 | 0.372 |  |  | mid |
| 2 | 0.418 | 0.116 | 🔊 |  | low |
| 3 | 0.534 | 0.232 | 🔊 |  | mid |
| 4 | 0.766 | 0.186 |  |  | low |
| 5 | 0.952 | 0.232 |  |  | low |
| 6 | 1.184 | 0.163 |  |  | low |
| 7 | 1.347 | 0.650 | 🔊 | ⏸ | low |
| 8 | 1.997 | 0.200 |  |  | mid |

---

### trying_to_take_my_time.m4a

**Status:** ⚠️ CLOSE

| Property | Value |
|----------|-------|
| Expected Phrase | "Trying to take my time" |
| Syllable Breakdown | Try(1) ing(1) to(1) take(1) my(1) time(1) |
| Expected Syllables | 6 |
| Detected Syllables | 5 |
| Error | -1 |
| Tempo | 143.55 BPM |
| Duration | 2.368s |

**Detected Segments:**

| # | Start (s) | Duration (s) | Stressed | Sustained | Pitch |
|---|-----------|--------------|----------|-----------|-------|
| 1 | 0.139 | 0.302 |  |  | mid |
| 2 | 0.441 | 0.325 | 🔊 |  | low |
| 3 | 0.766 | 0.139 |  |  | low |
| 4 | 0.906 | 0.418 |  | ⏸ | low |
| 5 | 1.324 | 0.200 |  |  | low |

---

### what_bout_you.m4a

**Status:** ✅ PASS

| Property | Value |
|----------|-------|
| Expected Phrase | "What 'bout you" |
| Syllable Breakdown | What(1) 'bout(1) you(1) |
| Expected Syllables | 3 |
| Detected Syllables | 3 |
| Error | 0 |
| Tempo | 107.67 BPM |
| Duration | 2.24s |

**Detected Segments:**

| # | Start (s) | Duration (s) | Stressed | Sustained | Pitch |
|---|-----------|--------------|----------|-----------|-------|
| 1 | 0.046 | 0.488 |  | ⏸ | mid |
| 2 | 0.534 | 0.511 | 🔊 | ⏸ | low |
| 3 | 1.045 | 0.200 | 🔊 |  | low |

---

## 🔍 Analysis

### Observations

- **Perfect Detection (3 files):** `talk_to_me_i_said_what.m4a`, `99_problems.m4a`, `what_bout_you.m4a`
- **Under-Detection (1 files):** `trying_to_take_my_time.m4a` (expected 6, got 5)
- **Over-Detection (2 files):** `everybody_equal.m4a` (expected 6, got 8), `mumble_on_this_beat.m4a` (expected 5, got 8)

### Potential Issues

**Long Segments Detected (may indicate missed syllables):**

- `talk_to_me_i_said_what.m4a`: 1 segment(s) > 0.5s (max: 0.836s)
- `everybody_equal.m4a`: 1 segment(s) > 0.5s (max: 0.604s)
- `mumble_on_this_beat.m4a`: 1 segment(s) > 0.5s (max: 0.650s)
- `what_bout_you.m4a`: 1 segment(s) > 0.5s (max: 0.511s)


### Recommendations

Based on this analysis:

1. **If under-detection is observed:** Consider lowering `ONSET_DELTA` in `.env` for higher sensitivity
2. **If over-detection is observed:** Consider raising `ONSET_DELTA` or enabling breath filtering
3. **Long segments:** May need `MAX_SEGMENT_DURATION` adjustment for auto-splitting

---

*Report generated by `tests/test_new_audio_samples.py`*
