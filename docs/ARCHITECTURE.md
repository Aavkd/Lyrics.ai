# 🏗️ Flow-to-Lyrics Architecture

**Generated**: 2025-12-27  
**Context**: Technical documentation for "Flow-to-Lyrics" MVP.

---

## 🔭 High-Level Overview

**Flow-to-Lyrics** is a full-stack application designed to transform raw vocal flows (mumbling/yaourt) into rhythmic lyrics.  
It operates on a **Python Backend** (audio processing & lyric validation) and a **Next.js Frontend** (interactive visualization).

### 📐 Architecture Diagram

```mermaid
graph TD
    User[User] -->|Uploads Audio| UI[Next.js Frontend]
    UI -->|POST /upload| API[FastAPI Backend]
    
    subgraph "Backend (Python)"
        API -->|Audio Data| Engine[AudioEngine]
        Engine -->|Isolation| Demucs[Demucs (Mock/Real)]
        Engine -->|Analysis| Librosa[Librosa]
        Librosa -->|BPM & Onsets| Formatter[PivotFormatter]
        
        Formatter -->|JSON| API
        
        API -.->|Future: Gen Lyrics| Phase0[Lyric Generator]
        Phase0 -->|Validation| G2P[g2p_en]
    end
    
    subgraph "Frontend (React)"
        Store[Zustand Store] <-->|State| Editor[AudioEditor]
        Editor -->|Render| Wavesurfer[Wavesurfer.js]
        API -->|Analysis Data| Store
    end
```

---

## 🛠️ Tech Stack & Components

### 1. Backend Service (`/`)
**Role**: Audio Processing, DSP, and Logic Core.  
**Tech**: Python 3.10+, FastAPI, Librosa, Demucs, g2p_en.

| File | Type | Responsibilities |
|------|------|------------------|
| `main.py` | API Entry | FastAPI app definition, CORS, `/upload` endpoint, temp file management. |
| `audio_engine.py` | DSP Core | **DemucsProcessor**: Vocal separation (supports mock mode).<br>**LibrosaAnalyzer**: Detects onsets (syllables) and BPM.<br>**PivotFormatter**: Structures data into the Pivot JSON format. |
| `phase0_blind_test.py` | Logic | Standalone script for lyric generation & phonetic validation (Phase 0). Contains `SyllableValidator` & `LyricGenerator`. |

### 2. Frontend Application (`/frontend`)
**Role**: User Interface, Visualization, and Interaction.  
**Tech**: Next.js 14, React, TypeScript, Tailwind CSS, Wavesurfer.js, Zustand.

| Path | Type | Responsibilities |
|------|------|------------------|
| `app/page.tsx` | Page | Main UI layout, integrates `AudioEditor`. |
| `components/AudioEditor.tsx` | Component | **Core Editor**. Wraps Wavesurfer.js, handles region rendering, cleanup, and user interaction (drag/resize). |
| `components/SegmentList.tsx` | Component | Displays segment data in a table format. |
| `store/useAudioStore.ts` | State | Global state (Zustand). Manages `analysisData` (Pivot JSON), playback status, and zoom levels. |
| `lib/api.ts` | Utility | Typed API client for communicating with the backend. |

---

## 🔄 Data Pipeline

The system revolves around a **Pivot JSON** structure that normalizes audio data for the frontend and generation engine.

1.  **Ingestion**: User uploads audio (MP3/WAV) -> `main.py`.
2.  **Processing** (`audio_engine.py`):
    *   **Demucs**: Isolates vocals (or mocks it).
    *   **Librosa**: Detects `onsets` (syllable starts) and `tempo`.
3.  **Formatting**: Converted into **Pivot JSON**:
    ```json
    {
      "meta": { "tempo": 120, "duration": 10.5 },
      "blocks": [{
        "id": 1, 
        "syllable_target": 12,
        "segments": [{ "time_start": 0.5, "duration": 0.2, "is_stressed": false }]
      }]
    }
    ```
4.  **Visualization**: Frontend receives JSON -> Zustand -> Wavesurfer renders regions.

---

## 📂 Directory Structure

```text
Lyrics.ai/
├── main.py                     # 🚀 API Entry & File Upload
├── audio_engine.py             # 🧠 Audio Processing Logic (DSP)
├── phase0_blind_test.py        # 🧪 Lyric Gen & Validation Script
├── requirements.txt            # 📦 Python Dependencies
├── PROJECT_STATUS.md           # 📊 Master Tracking Document
├── PHASE*_CHANGELOG.md         # 📝 Phase-specific logs
└── frontend/                   # 🖥️ Next.js Monorepo
    ├── app/                    #    App Router Pages
    ├── components/             #    React UI Components
    ├── lib/                    #    Utilities (API)
    └── store/                  #    Zustand State Store
```
