# 📊 Flow-to-Lyrics: Project Status Report

**Last Updated**: 2025-12-28  
**Version**: MVP - English Only (Post Phase D - Full-Audio Whisper)  
**Objective**: Transform informal vocal flows ("yaourt") into coherent rap/song lyrics with strict rhythmic precision and human validation.

---

## 📋 Executive Summary

The Flow-to-Lyrics project is currently at approximately **75% completion** of the MVP roadmap. The **backend pipeline is COMPLETE** with all 5 core engines working end-to-end:

1. ✅ **AudioEngine** - Analyzes audio, detects segments with stress/sustain/pitch
2. ✅ **PromptEngine** - Translates PivotJSON to LLM prompts with melodic guidance
3. ✅ **GenerationEngine** - Generates candidates via Ollama (local or cloud)
4. ✅ **LyricValidator** - The "Gatekeeper" that filters by syllable count and groove score
5. ✅ **CorePipeline** - End-to-end orchestrator with multi-candidate exposure
6. ✅ **WhisperPhoneticAnalyzer** - Whisper + g2p_en for phonetic transcription (Phase C)
7. ✅ **Full-Audio Syllable Alignment** - Word-level timestamps with syllable distribution (Phase D)

The frontend remains a **read-only audio viewer** with no editing or generation capabilities exposed.

### Current User Experience
Users can only:
1. **Import** an audio file (drag-and-drop or file picker)
2. **View** the waveform with auto-detected segments
3. **Play** the audio with spacebar control
4. **View** segment details in synchronized data table

**No editing, no lyric generation UI, no export.** Lyric generation works via CLI only.

| Phase | Status | User-Facing? |
|-------|--------|--------------|
| Phase 0: Blind Test (Lyric Validation) | ✅ Complete | ❌ CLI only |
| Phase 1: Precision Engine | ✅ Complete | ❌ Backend only |
| Phase 2: End-to-End Integration | ⚠️ 75% Complete | ❌ Not exposed |
| Phase 3: Co-Pilot UI | 🔴 Not Started | 🔴 Missing |

---

## 🔄 PRD Pipeline vs. Current Implementation

### Étape 1: Nettoyage & Isolation (Audio Pre-processing)

| Feature | PRD Requirement | Current State | Status |
|---------|-----------------|---------------|--------|
| Input formats | WAV/MP3 | MP3, WAV, M4A, FLAC, OGG ✅ | ✅ Done |
| Demucs v4 (Hybrid Transformer) | Required | Implemented with mock mode | ⚠️ Partial |
| Vocal isolation | Separate vocals vs instrumental | Code exists, defaults to `MOCK_MODE=true` | ⚠️ Partial |
| Mono 16kHz conversion | Required for optimal analysis | **Not implemented** | 🔴 Missing |
| Normalized vocal stem | Required | **Not implemented** | 🔴 Missing |

**Files Involved**:
- `audio_engine.py` → `DemucsProcessor` class (lines 95-179)

---

### Étape 2: Extraction Structurelle & Validation UX

| Feature | PRD Requirement | Current State | Status |
|---------|-----------------|---------------|--------|
| Onset detection (Spectral Flux) | Librosa | ✅ `librosa.onset.onset_detect()` with adaptive params | ✅ Done |
| **Adaptive onset detection** | Required | ✅ Spectral + energy-based fallback | ✅ Done |
| **Segment auto-splitting** | Required | ✅ Long segments split at energy valleys | ✅ Done |
| **Breath filtering** | Required | ✅ Low-energy segments filtered | ✅ Done |
| Intensity/Stress detection | Amplitude peaks | ✅ RMS amplitude analysis | ✅ Done |
| Sustain detection | Duration threshold | ✅ Duration-based detection | ✅ Done |
| **Pitch detection** | Required | ✅ `librosa.pyin` pitch tracking | ✅ Done |
| Interactive waveform | Wavesurfer.js + Regions | ✅ Fully functional | ✅ Done |
| Region drag/resize | Required | ⚠️ Visual only, not persisted | ⚠️ Partial |
| Merge/Split actions | Required | **Not implemented** | 🔴 Missing |
| Delete regions | Required | **Not implemented** | 🔴 Missing |
| Tap-to-Rhythm (Space key) | Manual marker placement | **Not implemented** | 🔴 Missing |

**Files Involved**:
- `audio_engine.py` → `LibrosaAnalyzer`, `PivotFormatter` classes
- `frontend/components/AudioEditor.tsx` (527 lines)
- `frontend/components/SegmentList.tsx` (164 lines)

---

### Étape 3: Le JSON Pivot

| Feature | PRD Requirement | Current State | Status |
|---------|-----------------|---------------|--------|
| `meta.tempo` | Required | ✅ Implemented | ✅ Done |
| `meta.duration` | Required | ✅ Implemented | ✅ Done |
| `meta.genre` | Required | **Not implemented** | 🔴 Missing |
| `meta.theme` | Required | **Not implemented** | 🔴 Missing |
| `meta.language` | Required (en-US) | **Not implemented** | 🔴 Missing |
| `blocks[].id` | Required | ✅ Implemented | ✅ Done |
| `blocks[].rhyme_scheme` | Required | **Not implemented** | 🔴 Missing |
| `blocks[].syllable_target` | Required | ✅ Auto-calculated | ✅ Done |
| `segments[].time_start` | Required | ✅ Implemented | ✅ Done |
| `segments[].duration` | Required | ✅ Implemented | ✅ Done |
| `segments[].is_stressed` | Required | ✅ Dynamic RMS detection | ✅ Done |
| `segments[].is_sustained` | Required | ✅ Duration threshold | ✅ Done |
| `segments[].pitch_contour` | Required | ✅ **NEW** - pyin detection | ✅ Done |

**Current Output Structure**:
```json
{
  "meta": { "tempo": 123.05, "duration": 11.65 },
  "blocks": [{
    "id": 1,
    "syllable_target": 5,
    "segments": [
      { 
        "time_start": 0.07, 
        "duration": 0.186, 
        "is_stressed": true,
        "is_sustained": false,
        "pitch_contour": "mid"
      }
    ]
  }],
  "_meta": { "filename": "test.mp3", "mock_mode": true, "llm_model": "ministral-3:8b" }
}
```

---

### Étape 4: Génération & Validation Phonétique

| Feature | PRD Requirement | Current State | Status |
|---------|-----------------|---------------|--------|
| "Generate Many, Filter Best" strategy | Required | ✅ 5-candidate generation | ✅ Done |
| g2p_en phonetic validation | Required | ✅ Fully implemented | ✅ Done |
| Syllable counting (auditory) | Required | ✅ Works correctly | ✅ Done |
| Stress pattern matching | Required | ✅ `LyricValidator.calculate_groove_score()` | ✅ Done |
| **Weighted Groove Scoring** | Required | ✅ 2x weight for stressed beats | ✅ Done |
| LLM integration (Local Ollama) | Required | ✅ `GenerationEngine` | ✅ Done |
| **Cloud Ollama support** | Optional | ✅ API key authentication | ✅ Done |
| Parallel 5-candidate generation | Required | ✅ Full pipeline | ✅ Done |
| Syllabic scoring (0 or 1) | Required | ✅ `LyricValidator.validate_line()` | ✅ Done |
| Stress scoring (0.0 - 1.0) | Required | ✅ Groove Score | ✅ Done |
| Retry with error-specific prompts | Required | **Not implemented** | 🔴 Missing |
| **Prompt Engine** | Required | ✅ External templates | ✅ Done |
| **Pitch/Melodic Guidance** | Required | ✅ **NEW** - Injected in prompts | ✅ Done |
| **Core Pipeline** | Required | ✅ `CorePipeline` orchestrator | ✅ Done |
| **Multi-Candidate Exposure** | Required | ✅ `GenerationResult` returns all 5 | ✅ Done |

**Files Involved**:
- `validator.py` → `LyricValidator` class
- `core_pipeline.py` → `CorePipeline`, `GenerationResult` classes
- `generation_engine.py` → `GenerationEngine` class
- `prompt_engine.py` → `PromptEngine` class
- `prompts/system_instruction.md` → System prompt
- `prompts/user_template.md` → User template with `{{pitch_guidance}}`

**Test Results** (Precision Tuning - 2025-12-28):

| Test File | Expected Syllables | Detected | Error |
|-----------|-------------------|----------|-------|
| 3_syllabes(sustained)_test.mp3 | 3 | 3 | ✓ 0 |
| 3_syllabes_test.mp3 | 3 | 3 | ✓ 0 |
| 5_syllabes_test.mp3 | 5 | 5 | ✓ 0 |
| 10_syllabes_test.mp3 | 10 | 11 | +1 |
| **test_audio_2-1.m4a** | **6** | **6** | **✓ 0** |

---

### Étape 5: Alignement & Rendu

| Feature | PRD Requirement | Current State | Status |
|---------|-----------------|---------------|--------|
| CTC-Segmentation | Optional | **Not implemented** | 🔴 Missing |
| Linear alignment | Alternative | **Not implemented** | 🔴 Missing |
| Word-by-word text display | Required | **Not implemented** | 🔴 Missing |
| Audio-text synchronization | Required | **Not implemented** | 🔴 Missing |
| SSE streaming | Required | **Not implemented** | 🔴 Missing |
| Export functionality | Required | **Not implemented** | 🔴 Missing |

---

## 🛠️ Technology Stack Comparison

### Backend (Python)

| Technology | PRD | Current | Status |
|------------|-----|---------|--------|
| FastAPI (Async, Websockets) | Required | ✅ FastAPI implemented | ⚠️ No Websockets |
| Librosa | Required | ✅ Installed & used | ✅ Done |
| Demucs | Required | ✅ Installed (mock mode) | ⚠️ Partial |
| g2p_en | Required | ✅ Fully functional | ✅ Done |
| Instructor/Outlines | Required for JSON | Robust regex parsing | ⚠️ Alternative |
| Local Ollama | Required | ✅ Fully integrated | ✅ Done |
| Cloud Ollama | Optional | ✅ API key authentication | ✅ Done |
| **Config Module** | Implied | ✅ Centralized `.env` loading | ✅ Done |

### Frontend (Next.js / React)

| Technology | PRD | Current | Status |
|------------|-----|---------|--------|
| Next.js 14 | Implied | ✅ Installed | ✅ Done |
| Wavesurfer.js v7 | Required | ✅ Fully integrated | ✅ Done |
| Regions Plugin | Required | ✅ Working | ✅ Done |
| Timeline Plugin | Required | **Not implemented** | 🔴 Missing |
| Zustand | Required | ✅ Fully integrated | ✅ Done |
| SSE (Server-Sent Events) | Required | **Not implemented** | 🔴 Missing |

---

## ✅ What The User Can Actually Do (Current UX)

Based on the current frontend interface, users can perform **4 core actions only**:

| Action | Works? | Notes |
|--------|--------|-------|
| 🎵 **Import audio file** | ✅ | Drag-and-drop or click (MP3, WAV, M4A, FLAC, OGG) |
| 👁️ **View waveform + segments** | ✅ | See detected syllable regions overlaid on waveform |
| ▶️ **Play/pause audio** | ✅ | Button or Spacebar shortcut |
| 📊 **View segment table** | ✅ | Bi-directional sync with waveform hover/active |

**That's it.** Everything else is backend-only or not exposed to the user.

### What Appears to Work But Doesn't

| Feature | Visual State | Reality |
|---------|--------------|---------|
| Drag/resize regions | Regions appear draggable | Changes aren't saved or exported |
| Zoom controls | Slider exists | Works but has no practical use |
| BPM display | Shows value | Informational only |

### Backend Infrastructure (Working but Not User-Facing)
1. **FastAPI server** (`main.py`) - Runs on `localhost:8000`
2. **Audio upload endpoint** (`POST /upload`) - Returns PivotJSON
3. **Full lyric generation pipeline** (`CorePipeline`) - Works via CLI
4. **5-candidate LLM generation** (`GenerationEngine`) - Returns all options
5. **Phonetic validation** (`LyricValidator`) - g2p_en groove scoring
6. **Pitch detection** (`PivotFormatter`) - librosa.pyin integration
7. **Prompt Engine** (`prompt_engine.py`) - Melodic guidance injection

---
## 🎯 Target Frontend Experience (Missing vs Current)
The current frontend is a **temporary testing prototype** with poor UX ("trash" tier). The final implementation requires a complete overhaul to support true interactivity.
### 1. Interactivity Requirements (Currently Missing)
The user **IS NOT** currently able to effectively edit the segmentation. The target experience requires:
- [ ] **Drag & Resize**: Users must be able to freely move and resize segment regions.
- [ ] **Split & Merge**: Ability to cut a segment in two or join two segments.
- [ ] **Delete & Add**: Intuitive controls to remove false positives or add missing syllables.
- [ ] **Snap-to-Grid**: Segments should optionally snap to rhythm quantization.
### 2. Visual Requirements (Currently Basic)
The current waveform overlay is merely functional. The target design needs:
- [ ] **Distinct Blocks**: Regions should look like solid, interactive blocks that are **superposed directly onto the waveform** for easy edits.
- [ ] **Clear Handles**: Visual cues for resizing (left/right handles).
- [ ] **Hover Effects**: Clear visual feedback when hovering over editable zones.
- [ ] **Context Menus**: Right-click actions for specific segment operations.
> **Status**: The current UI exists purely to validate the backend data flow. A dedicated UI/UX phase is pending to build the actual editor.
---
## 🔴 What Needs Refinement
### Critical (Blocks Core Functionality)
1. **Real LLM integration** - Currently mock only
3. **Tap-to-Rhythm feature** - Manual marker placement missing
4. **Region Split/Merge/Delete** - Editing actions missing
5. **End-to-end pipeline** - No connection between audio analysis and lyric generation
### Important (Affects Quality)
1. **BPM accuracy** - ~5% variance needs improvement
3. **Mono 16kHz conversion** - Missing audio preprocessing
4. **Stress pattern matching** - No scoring implemented
5. **Pitch contour detection** - Missing from Pivot JSON
### Nice to Have
1. **Timeline plugin** - Visual time markers
2. **SSE streaming** - Real-time lyric display
3. **Export functionality** - Save edited segments
4. **Genre/Theme metadata** - Not captured
5. **Multi-block support** - Only `blocks[0]` is rendered

---

## ⚙️ Syllable Detection Configuration

As of 2025-12-28, onset detection parameters are configurable via `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ONSET_DELTA` | `0.05` | Detection sensitivity (lower = more sensitive) |
| `ONSET_USE_ENERGY` | `true` | Enable energy-based fallback detection |
| `MAX_SEGMENT_DURATION` | `1.0` | Max segment length before auto-splitting |
| `ONSET_WAIT` | `1` | Min frames between onsets |

## ⚙️ Phonetic Analysis Configuration (Phase C)

As of 2025-12-28, phonetic analysis uses Whisper + g2p_en with Allosaurus fallback:

| Variable | Default | Description |
|----------|---------|-------------|
| `PHONETIC_MODEL` | `whisper` | Backend: `whisper` (recommended) or `allosaurus` |
| `WHISPER_MODEL_SIZE` | `base` | Model size: `tiny`, `base`, `small`, `medium`, `large` |
| `PHONETIC_ENABLED` | `true` | Enable IPA phoneme extraction |
| `PHONETIC_MIN_DURATION` | `0.10` | Min segment duration for analysis (100ms) |
| `PHONETIC_PADDING` | `0.05` | Context padding on each side (50ms) |
| `PHONETIC_RETRY_PADDING` | `0.10` | Expanded retry padding on failure (100ms) |
| `PHONETIC_FALLBACK_ENABLED` | `true` | Return `[vowel]`/`[consonant]` when detection fails |

> ℹ️ **Phase C Complete:** Whisper + g2p_en pipeline improves accuracy for mumbled vocals. Detection rate 60-83% depending on audio quality. See [REMAINING_ISSUES.md](./REMAINING_ISSUES.md) for known limitations.

---

## 📅 Roadmap Progress

### Phase 0: "Blind Test" (Weeks 1-2) → ✅ 100% Complete
- [x] Python script with syllable input
- [x] g2p_en phonetic validation
- [x] "Generate Many, Filter Best" logic
- [x] Prompt Engine (JSON-to-Prompt translation)
- [x] Real LLM integration (Ollama)
- [x] Validator with Groove Score (0.0-1.0)
- [x] Core Pipeline orchestrating all engines

### Phase 1: Precision Engine → ✅ 100% Complete
- [x] Pitch detection (`librosa.pyin`)
- [x] Pitch contour mapping (low/mid/high/rising/falling)
- [x] Multi-candidate exposure (`GenerationResult`)
- [x] Groove score calibration (2x weight for stressed beats)
- [x] Melodic guidance in prompts (`{{pitch_guidance}}`)
- [x] Precision tuning script (`test_precision_tuning.py`)
- [x] Onset detection optimization (delta=0.1)

### Phase 2: Segmentation Tool → ⚠️ 75% Complete
- [x] Wavesurfer.js frontend
- [x] Demucs backend (mock mode)
- [x] Audio → Pivot JSON pipeline
- [x] Region visualization
- [x] Stress & Sustain detection
- [x] Config module (`.env` support)
- [x] Cloud Ollama support
- [ ] Tap-to-Rhythm feature
- [ ] Region editing (split/merge/delete)

### Phase 3: End-to-End Integration → ⚠️ 50% Complete
- [x] Connect Phase 0 + Phase 1 (via `core_pipeline.py`)
- [x] Full pipeline testing (all tests passing)
- [ ] API endpoint for lyrics generation (`POST /generate/interactive`)
- [ ] SSE streaming for lyrics
- [ ] Export functionality

### Phase 4: Co-Pilot UI → 🔴 0% Complete
- [ ] Candidate List UI component ("Slot Machine")
- [ ] Click-to-Apply lyric selection
- [ ] "Regenerate" button
- [ ] Region locking
- [ ] Context menu for segment actions

### Phonetic Improvement: Phase A & B → ✅ 100% Complete
- [x] Add segment padding (50ms context on each side)
- [x] Increase min_duration (100ms minimum)
- [x] Add retry with expanded padding (100ms on failure)
- [x] Add `[vowel]`/`[consonant]` fallback classification
- [x] Add 5 new config options (`PHONETIC_*`)
- [x] Create `classify_sound_type()` spectral fallback
- [x] Tests: 8 new tests in `test_phonetic_padding.py`

> **Result:** Detection rate improved from 67% → 83%, but **accuracy issue remains** (see `docs/PHONETIC_ACCURACY_ISSUE.md`).

### Phonetic Improvement: Phase C → ✅ 100% Complete
- [x] Create `WhisperPhoneticAnalyzer` class
- [x] Integrate Whisper for transcription
- [x] Convert words → phonemes via g2p_en
- [x] Add `PHONETIC_MODEL` config option (`allosaurus`/`whisper`)
- [x] Add `WHISPER_MODEL_SIZE` config option
- [x] Automatic fallback to Allosaurus when Whisper unavailable
- [x] Tests: 7 new tests in `test_whisper_phonetic.py`

> **Result:** Whisper integration provides context-aware transcription for mumbled vocals, with g2p_en converting words to accurate English phonemes.

---

## 📁 Project Structure

```
Lyrics.ai/
├── main.py                     # FastAPI server (223 lines)
├── audio_engine.py             # DSP: Demucs + Librosa + Pitch (631 lines)
├── prompt_engine.py            # JSON-to-Prompt translation (351 lines)
├── generation_engine.py        # Ollama LLM integration (421 lines)
├── validator.py                # LyricValidator - The Gatekeeper (365 lines)
├── core_pipeline.py            # CorePipeline - The Orchestrator (422 lines)
├── config.py                   # Centralized config with .env (211 lines)
├── phase0_blind_test.py        # Original validation script (362 lines)
├── requirements.txt            # Python dependencies
├── .env / .env.example         # Configuration
├── test_audio_real.mp3         # Test audio files
├── prompts/                    # LLM prompt templates
│   ├── system_instruction.md   # Persona + few-shot examples
│   └── user_template.md        # User prompt with pitch guidance
├── tests/
│   ├── test_audio_analysis.py  # Stress/sustain tests
│   ├── test_prompt_engine.py   # Prompt generation tests
│   ├── test_generation.py      # LLM integration tests
│   ├── test_end_to_end.py      # Full pipeline tests
│   └── test_precision_tuning.py # Onset calibration
├── audio samples/              # Precision tuning audio files
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md
│   ├── PROJECT_STATUS.md       # This file
│   ├── NEXT_PHASES.md
│   ├── PHASE1_PRECISION_CHANGELOG.md
│   └── prd.md
└── frontend/
    ├── app/
    │   ├── page.tsx            # Main page layout
    │   ├── layout.tsx          # Root layout
    │   └── globals.css         # Dark theme styles
    ├── components/
    │   ├── AudioEditor.tsx     # Waveform editor (527 lines)
    │   └── SegmentList.tsx     # Segment table (164 lines)
    ├── store/
    │   └── useAudioStore.ts    # Zustand state (138 lines)
    └── lib/
        └── api.ts              # Backend API client
```

---

## 🚀 Recommended Next Steps

### Immediate (This Week)
1. **Create `/generate/interactive` API endpoint**
   - Accept `region_id` and `context` parameters
   - Return all 5 candidates with scores
   - Connect frontend to this endpoint

2. **Build Candidate List UI Component**
   - Display 5 lyric options with scores
   - Click-to-apply functionality
   - "Regenerate" button

### Short-term (Next 2 Weeks)
3. **Implement Tap-to-Rhythm** in `AudioEditor.tsx`
4. **Add Region Split/Merge/Delete actions**
5. **File Slicing** for audio > 4 seconds

### Medium-term (Weeks 3-4)
6. **SSE streaming** for real-time lyric display
7. **Export functionality** (JSON, SRT/VTT)
8. **Region locking** for approved lyrics

---

## 🧪 Known Issues

| Issue | Location | Severity | Notes |
|-------|----------|----------|-------|
| BPM variance ~5% | `LibrosaAnalyzer.analyze()` | Medium | May need prior estimation |
| Mock Demucs only | `DemucsProcessor` | Medium | Real processing needs GPU |
| Single block rendering | `AudioEditor.tsx` | Low | Only `blocks[0]` displayed |
| 10-syllable file +1 error | `test_precision_tuning.py` | Low | Edge case in onset detection |
| Frontend not connected to generation | `frontend/` | High | No lyric generation UI |

---

*This document was last updated by analyzing the project codebase on 2025-12-28.*
