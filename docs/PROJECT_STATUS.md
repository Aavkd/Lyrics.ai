# 📊 Flow-to-Lyrics: Project Status Report

**Generated**: 2025-12-27  
**Version**: MVP - English Only  
**Objective**: Transform informal vocal flows ("yaourt") into coherent rap/song lyrics with strict rhythmic precision and human validation.

---

## 📋 Executive Summary

The Flow-to-Lyrics project is currently at approximately **55% completion** of the MVP roadmap from a **user perspective**. The **backend pipeline is now COMPLETE** with all 4 core engines working end-to-end:

1. ✅ **AudioEngine** - Analyzes audio, detects segments with stress/sustain
2. ✅ **PromptEngine** - Translates PivotJSON to LLM prompts
3. ✅ **GenerationEngine** - Generates candidates via Ollama (local or cloud)
4. ✅ **LyricValidator** - The "Gatekeeper" that filters by syllable count and groove score

The frontend remains a **read-only audio viewer** with no editing or generation capabilities.

### Current User Experience
Users can only:
1. **Import** an audio file (drag-and-drop)
2. **View** the waveform with auto-detected segments
3. **Play** the audio with spacebar control

**No editing, no lyric generation UI, no export.** The app is a visualization prototype. Lyric generation works via CLI only.

| Phase | Status | User-Facing? |
|-------|--------|--------------|
| Phase 0: Blind Test (Lyric Validation) | ✅ Complete | ❌ CLI only |
| Phase 1: Segmentation Tool | ⚠️ Display only | ⚠️ Read-only |
| Phase 2: End-to-End Integration | ⚠️ Backend only | ❌ Not exposed |

---

## 🔄 PRD Pipeline vs. Current Implementation

### Étape 1: Nettoyage & Isolation (Audio Pre-processing)

| Feature | PRD Requirement | Current State | Status |
|---------|-----------------|---------------|--------|
| Input formats | WAV/MP3 | MP3, WAV, M4A, FLAC, OGG ✅ | ✅ Done |
| Demucs v4 (Hybrid Transformer) | Required | Implemented with mock mode | ⚠️ Partial |
| Vocal isolation | Separate vocals vs instrumental | Code exists but defaults to `MOCK_MODE=true` | ⚠️ Partial |
| Mono 16kHz conversion | Required for optimal analysis | **Not implemented** | 🔴 Missing |
| Normalized vocal stem | Required | **Not implemented** | 🔴 Missing |

**Files Involved**:
- `audio_engine.py` → `DemucsProcessor` class (lines 90-174)

**Notes**:
- Demucs processor is implemented but runs in mock mode by default
- Real Demucs processing requires GPU and is not tested in production
- No sample rate conversion or normalization step exists

---

### Étape 2: Extraction Structurelle & Validation UX

| Feature | PRD Requirement | Current State | Status |
|---------|-----------------|---------------|--------|
| Onset detection (Spectral Flux) | Librosa | ✅ Implemented via `librosa.onset.onset_detect()` | ✅ Done |
| Intensity/Stress detection | Amplitude peaks | ✅ Implemented via RMS amplitude analysis | ✅ Done |
| Interactive waveform | Wavesurfer.js + Regions | ✅ Fully functional | ✅ Done |
| Region drag/resize | Required | ✅ Implemented | ✅ Done |
| Merge/Split actions | Required | **Not implemented** | 🔴 Missing |
| Delete regions | Required | **Not implemented** | 🔴 Missing |
| Tap-to-Rhythm (Space key) | Manual marker placement | **Not implemented** | 🔴 Missing |

**Files Involved**:
- `audio_engine.py` → `LibrosaAnalyzer` class (lines 181-229)
- `frontend/components/AudioEditor.tsx` (526 lines)
- `frontend/components/SegmentList.tsx` (164 lines)

**Notes**:
- Onset detection works well (28 syllables detected in test audio)
- BPM detection has ~5% variance (123 vs 130 BPM actual)
| Sustained notes appear as single long segments instead of multiple syllables | ⚠️ Known Issue |
| Stress pattern detection implemented | ✅ Done |

---

### Étape 3: Le JSON Pivot

| Feature | PRD Requirement | Current State | Status |
|---------|-----------------|---------------|--------|
| `meta.tempo` | Required | ✅ Implemented | ✅ Done |
| `meta.genre` | Required | **Not implemented** | 🔴 Missing |
| `meta.theme` | Required | **Not implemented** | 🔴 Missing |
| `meta.language` | Required (en-US) | **Not implemented** | 🔴 Missing |
| `blocks[].id` | Required | ✅ Implemented | ✅ Done |
| `blocks[].rhyme_scheme` | Required | **Not implemented** | 🔴 Missing |
| `blocks[].syllable_target` | Required | ✅ Implemented (auto-calculated) | ✅ Done |
| `segments[].time_start` | Required | ✅ Implemented | ✅ Done |
| `segments[].duration` | Required | ✅ Implemented | ✅ Done |
| `segments[].is_stressed` | Required | ✅ Implemented (dynamic detection) | ✅ Done |
| `segments[].is_sustained` | Required | ✅ Implemented (duration threshold) | ✅ Done |
| `segments[].pitch_contour` | Required | **Not implemented** | 🔴 Missing |

**Current Output Structure**:
```json
{
  "meta": { "tempo": 123.05, "duration": 11.65 },
  "blocks": [{
    "id": 1,
    "syllable_target": 28,
    "segments": [
      { "time_start": 0.07, "duration": 0.186, "is_stressed": false }
    ]
  }],
  "_meta": { "filename": "test.mp3", "mock_mode": true }
}
```

**Files Involved**:
- `audio_engine.py` → `PivotJSON`, `PivotFormatter` classes
- `frontend/store/useAudioStore.ts` → TypeScript interfaces

---

### Étape 4: Génération & Validation Phonétique

| Feature | PRD Requirement | Current State | Status |
|---------|-----------------|---------------|--------|
| "Generate Many, Filter Best" strategy | Required | ✅ Logic exists in `phase0_blind_test.py` | ✅ Done |
| g2p_en phonetic validation | Required | ✅ Fully implemented | ✅ Done |
| Syllable counting (auditory) | Required | ✅ Works correctly | ✅ Done |
| Stress pattern matching | Required | ✅ `LyricValidator.calculate_groove_score()` | ✅ Done |
| LLM integration (Local Ollama) | Required | ✅ `GenerationEngine` with ministral-3 | ✅ Done |
| Parallel 5-candidate generation | Required | ✅ Full pipeline: Prompt → Ollama → JSON parsing | ✅ Done |
| Syllabic scoring (0 or 1) | Required | ✅ `LyricValidator.validate_line()` | ✅ Done |
| Stress scoring (0.0 - 1.0) | Required | ✅ `LyricValidator` Groove Score (0.0-1.0) | ✅ Done |
| Retry with error-specific prompts | Required | **Not implemented** | 🔴 Missing |
| **Prompt Engine (JSON→Prompt)** | Required | ✅ `PromptEngine` class with external templates | ✅ Done |
| **Core Pipeline (Orchestrator)** | Required | ✅ `CorePipeline` class orchestrates all engines | ✅ Done |

**Files Involved**:
- `validator.py` → `LyricValidator` class (The Gatekeeper - g2p_en phonetic validation)
- `core_pipeline.py` → `CorePipeline` class (The Orchestrator - end-to-end flow)
- `generation_engine.py` → `GenerationEngine` class (Ollama HTTP integration)
- `phase0_blind_test.py` → `SyllableValidator`, `LyricGenerator` classes
- `prompt_engine.py` → `PromptEngine` class (JSON-to-Prompt translation)
- `prompts/system_instruction.md` → System prompt with persona and few-shot examples
- `prompts/user_template.md` → User prompt template with placeholders
- `tests/test_generation.py` → Test suite for GenerationEngine
- `tests/test_end_to_end.py` → Test suite for Validator and CorePipeline

**Test Results** (Real LLM Generation - 2025-12-27):

| Step | Result | Details |
|------|--------|---------|
| Audio Analysis | ✅ | 7 syllables detected, pattern: DA-da-da-da-DA-da-da |
| LLM Generation | ✅ | 5 candidates from Ollama ministral-3 |
| Validation | ✅ | 3/5 matched syllable count |
| Best Match | ✅ | "No **way** to stop me, I **glide**" (score: 0.29) |

**Latest Pipeline Output:**
```
🧠 Generated 5 candidates:
  1. "I **soar** the skies so free" (6 syllables ✗)
  2. "No **way** to stop me, I **glide**" (7 syllables ✓)
  3. "The **glow** of gold in my eyes" (7 syllables ✓)
  4. "**Fly** fast, I'm wild in the night" (7 syllables ✓)
  5. "**Go** hard, no one can hide" (6 syllables ✗)

🏆 WINNING LYRIC: "No **way** to stop me, I **glide**"
📊 GROOVE SCORE: 0.29
```

**Success Rate**: 60% (3/5 valid syllable matches)

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
| Torchaudio | Required | Not used | 🔴 Missing |
| Librosa | Required | ✅ Installed & used | ✅ Done |
| Demucs | Required | ✅ Installed (mock mode) | ⚠️ Partial |
| g2p_en | Required | ✅ Fully functional | ✅ Done |
| nltk (CMU Dict) | Required | Not used directly | ⚠️ Partial |
| Instructor/Outlines | Required for JSON | Regex-based parsing in GenerationEngine | ⚠️ Alternative |
| Local Ollama (ministral-3) | Required | ✅ Fully integrated | ✅ Done |
| Cloud Ollama Support | Optional | ✅ API key authentication via `OLLAMA_API_KEY` | ✅ Done |

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

Based on the current frontend interface, users can perform **3 core actions only**:

| Action | Works? | Notes |
|--------|--------|-------|
| 🎵 **Import audio file** | ✅ | Drag-and-drop or click to select (MP3, WAV, etc.) |
| 👁️ **View waveform + segments** | ✅ | See detected syllable regions overlaid on waveform |
| ▶️ **Play/pause audio** | ✅ | Button or Spacebar shortcut |

**That's it.** Everything else is either backend-only or code that exists but isn't exposed to the user.

### What Appears to Work But Doesn't

| Feature | Visual State | Reality |
|---------|--------------|---------|
| Drag/resize regions | Regions appear draggable | Changes aren't saved or exported |
| Segment table | Shows data | Read-only display, no editing |
| Zoom controls | Slider exists | Works but has no practical use |
| BPM display | Shows value | Informational only |

### Backend Infrastructure (Not User-Facing)
1. **FastAPI server** (`main.py`) - Runs on `localhost:8000`
2. **Audio upload endpoint** (`POST /upload`) - Returns Pivot JSON
3. **BPM/Onset detection** - Librosa analysis (~5% BPM variance)
4. **Phonetic syllable counting** - g2p_en works in `phase0_blind_test.py`
5. **Mock LLM generation** - Test script only, no API integration
6. **Prompt Engine** - `prompt_engine.py` translates PivotJSON to LLM prompts

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

## 📅 Roadmap Progress

### Phase 0: "Blind Test" (Weeks 1-2) → ✅ 100% Complete
- [x] Python script with syllable input
- [x] g2p_en phonetic validation
- [x] "Generate Many, Filter Best" logic
- [x] Prompt Engine (Step 2: JSON-to-Prompt translation)
- [x] Real LLM integration (Local Ollama with ministral-3)
- [x] Validator with Groove Score (0.0-1.0)
- [x] Core Pipeline orchestrating all engines

### Phase 1: Segmentation Tool (Weeks 3-4) → ✅ 95% Complete
- [x] Wavesurfer.js frontend
- [x] Demucs backend (mock mode)
- [x] Audio → Pivot JSON pipeline
- [x] Region visualization
- [x] Stress & Sustain detection (Enhanced Audio Analysis)
- [ ] Tap-to-Rhythm feature

### Phase 2: End-to-End Integration (Weeks 5-6) → ⚠️ 40% Complete
- [x] Connect Phase 0 + Phase 1 (via `core_pipeline.py`)
- [x] Full pipeline testing (8 tests passing)
- [ ] API endpoint for lyrics generation
- [ ] SSE streaming for lyrics
- [ ] Export functionality

---

## 📁 Project Structure

```
Lyrics.ai/
├── main.py                     # FastAPI server (215 lines)
├── audio_engine.py             # Step 1: DSP logic - Demucs + Librosa (523 lines)
├── prompt_engine.py            # Step 2: JSON-to-Prompt translation (270 lines)
├── generation_engine.py        # Step 3: Ollama LLM integration (330 lines)
├── validator.py                # Step 4: LyricValidator - The Gatekeeper (280 lines) ⭐ NEW
├── core_pipeline.py            # Step 4: CorePipeline - The Orchestrator (267 lines) ⭐ NEW
├── phase0_blind_test.py        # Original syllable validation script (362 lines)
├── requirements.txt            # Python dependencies
├── test_audio_real.mp3         # Real test audio file
├── prompts/                    # LLM prompt templates
│   ├── system_instruction.md   # Persona + few-shot examples
│   └── user_template.md        # Jinja2-style user prompt
├── tests/
│   ├── test_audio_analysis.py  # Step 1 tests
│   ├── test_prompt_engine.py   # Step 2 tests
│   ├── test_generation.py      # Step 3 tests (Ollama integration)
│   └── test_end_to_end.py      # Step 4 tests (Full pipeline) ⭐ NEW
├── docs/                       # Documentation
│   ├── prd.md                  # Product Requirements Document
│   ├── PROJECT_STATUS.md       # This file
│   ├── TECH_ROADMAP.md         # Technical roadmap
│   ├── PHASE0_CHANGELOG.md     # Phase 0 changes
│   ├── PHASE1_CHANGELOG.md     # Phase 1 changes
│   ├── PHASE2_CHANGELOG.md     # Phase 2 changes
│   └── PHASE3_CHANGELOG.md     # Phase 3 changes (Validator + Pipeline) ⭐ NEW
└── frontend/
    ├── app/
    │   ├── page.tsx            # Main page layout
    │   ├── layout.tsx          # Root layout
    │   └── globals.css         # Dark theme styles
    ├── components/
    │   ├── AudioEditor.tsx     # Waveform editor (526 lines)
    │   └── SegmentList.tsx     # Segment table (164 lines)
    ├── store/
    │   └── useAudioStore.ts    # Zustand state (138 lines)
    └── lib/
        └── api.ts              # Backend API client (48 lines)
```

---

## 🚀 Recommended Next Steps

### Immediate (This Week)
1. **Implement real LLM integration** in `phase0_blind_test.py`
   - Add Groq API client
   - Replace mock `LyricGenerator` with real calls
   - Test >90% syllabic accuracy

2. **Refine Stress/Sustain Thresholds**
   - Tune `audio_engine.py` parameters based on real-world testing

### Short-term (Next 2 Weeks)
3. **Implement Tap-to-Rhythm** in `AudioEditor.tsx`
   - Add keyboard event listener for tap mode
   - Create new regions on tap
   - Sync with Zustand store

4. **Add Split/Merge/Delete actions**
   - Region context menu
   - Keyboard shortcuts

### Medium-term (Weeks 3-4)
5. **Connect Phase 0 + Phase 1**
   - New API endpoint for lyric generation
   - SSE streaming response
   - Frontend display component

6. **Export functionality**
   - Download edited Pivot JSON
   - Export as subtitle file (SRT/VTT)

---

## 🧪 Known Issues

| Issue | Location | Severity | Notes |
|-------|----------|----------|-------|
| BPM variance ~5% | `LibrosaAnalyzer.analyze()` | Medium | May need prior estimation |
| Mock Demucs only | `DemucsProcessor` | Medium | Real processing needs GPU |
| Single block rendering | `AudioEditor.tsx` | Low | Only `blocks[0]` displayed |

---

*This document was auto-generated by analyzing the project codebase against the PRD specifications.*
