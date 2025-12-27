# 📊 Flow-to-Lyrics: Project Status Report

**Generated**: 2025-12-27  
**Version**: MVP - English Only  
**Objective**: Transform informal vocal flows ("yaourt") into coherent rap/song lyrics with strict rhythmic precision and human validation.

---

## 📋 Executive Summary

The Flow-to-Lyrics project is currently at approximately **25% completion** of the MVP roadmap from a **user perspective**. While backend infrastructure exists, the frontend is essentially a **read-only audio viewer** with no editing or generation capabilities.

### Current User Experience
Users can only:
1. **Import** an audio file (drag-and-drop)
2. **View** the waveform with auto-detected segments
3. **Play** the audio with spacebar control

**No editing, no lyric generation, no export.** The app is a visualization prototype, not a functional tool.

| Phase | Status | User-Facing? |
|-------|--------|--------------|
| Phase 0: Blind Test (Lyric Validation) | ⚠️ Script only | ❌ No UI |
| Phase 1: Segmentation Tool | ⚠️ Display only | ⚠️ Read-only |
| Phase 2: End-to-End Integration | 🔴 Not Started | ❌ None |

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
| Intensity/Stress detection | Amplitude peaks | **All `is_stressed: false`** - not detecting | 🔴 Missing |
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
- Sustained notes appear as single long segments instead of multiple syllables
- No stress pattern detection implemented

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
| `segments[].is_stressed` | Required | ⚠️ Field exists, always `false` | ⚠️ Partial |
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
| Stress pattern matching | Required | **Not implemented** | 🔴 Missing |
| LLM integration (Groq/GPT-4) | Required | **Mock only** - no real LLM calls | 🔴 Missing |
| Parallel 5-candidate generation | Required | Mock version exists | ⚠️ Partial |
| Syllabic scoring (0 or 1) | Required | ✅ Implemented | ✅ Done |
| Stress scoring (0.0 - 1.0) | Required | **Not implemented** | 🔴 Missing |
| Retry with error-specific prompts | Required | **Not implemented** | 🔴 Missing |

**Files Involved**:
- `phase0_blind_test.py` → `SyllableValidator`, `LyricGenerator` classes

**Test Results** (from Phase 0 changelog):
| Target | Status | Selected Line |
|--------|--------|---------------|
| 8 | ✓ Matched | "I rise above the city lights" |
| 10 | ⚠ Retry | No candidates matched |
| 8 | ✓ Matched | "I rise above the city lights" |
| 10 | ⚠ Retry | No candidates matched |

**Success Rate**: 50% (expected with mock data)

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
| Instructor/Outlines | Required for JSON | **Not implemented** | 🔴 Missing |
| Groq/GPT-4 | Required | **Not implemented** | 🔴 Missing |

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

---

## 🔴 What Needs Refinement

### Critical (Blocks Core Functionality)
1. **Real LLM integration** - Currently mock only
2. **Stress detection** - All segments show `is_stressed: false`
3. **Tap-to-Rhythm feature** - Manual marker placement missing
4. **Region Split/Merge/Delete** - Editing actions missing
5. **End-to-end pipeline** - No connection between audio analysis and lyric generation

### Important (Affects Quality)
1. **BPM accuracy** - ~5% variance needs improvement
2. **Sustained note detection** - Long vowels appear as single segments
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

### Phase 0: "Blind Test" (Weeks 1-2) → ⚠️ 60% Complete
- [x] Python script with syllable input
- [x] g2p_en phonetic validation
- [x] "Generate Many, Filter Best" logic
- [ ] Real LLM integration (Groq/GPT-4)
- [ ] >90% rhythmic accuracy KPI

### Phase 1: Segmentation Tool (Weeks 3-4) → ✅ 95% Complete
- [x] Wavesurfer.js frontend
- [x] Demucs backend (mock mode)
- [x] Audio → Pivot JSON pipeline
- [x] Region visualization
- [ ] Tap-to-Rhythm feature

### Phase 2: End-to-End Integration (Weeks 5-6) → 🔴 0% Complete
- [ ] Connect Phase 0 + Phase 1
- [ ] SSE streaming for lyrics
- [ ] Export functionality
- [ ] Full pipeline testing

---

## 📁 Project Structure

```
Lyrics.ai/
├── main.py                     # FastAPI server (215 lines)
├── audio_engine.py             # DSP logic: Demucs + Librosa (388 lines)
├── phase0_blind_test.py        # Syllable validation (362 lines)
├── requirements.txt            # Python dependencies
├── prd.md                      # Product Requirements Document
├── PHASE0_CHANGELOG.md         # Phase 0 implementation notes
├── PHASE1_CHANGELOG.md         # Phase 1 implementation notes
├── PHASE2_CHANGELOG.md         # Phase 2 implementation notes
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

2. **Add stress detection** in `audio_engine.py`
   - Analyze amplitude peaks
   - Map to `is_stressed` field

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
| Sustained vowels as single segment | `audio_engine.py` | Medium | Needs amplitude envelope analysis |
| No stress detection | `PivotFormatter.format()` | High | All `is_stressed: false` |
| Mock Demucs only | `DemucsProcessor` | Medium | Real processing needs GPU |
| Single block rendering | `AudioEditor.tsx` | Low | Only `blocks[0]` displayed |

---

*This document was auto-generated by analyzing the project codebase against the PRD specifications.*
