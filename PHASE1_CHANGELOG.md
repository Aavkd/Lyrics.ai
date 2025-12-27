# Phase 1 Implementation Changelog

## 2025-12-27: Audio Analysis Backend Implementation

### Created Files

| File | Description |
|------|-------------|
| `main.py` | FastAPI application with `/upload` endpoint |
| `audio_engine.py` | Core DSP logic (Demucs + Librosa) |
| `requirements.txt` | All Python dependencies |

---

### Key Components

#### 1. **AudioEngine Class** (`audio_engine.py`)
Main processing pipeline combining:
- **DemucsProcessor**: Vocal isolation with mock mode support
- **LibrosaAnalyzer**: BPM and onset detection
- **PivotFormatter**: JSON output formatting

#### 2. **FastAPI Application** (`main.py`)
- `GET /` - Health check
- `GET /health` - Detailed status
- `POST /upload` - File upload and analysis
- CORS enabled for frontend integration
- Secure temp file handling with cleanup

#### 3. **Environment Configuration**
- `MOCK_MODE=true` - Skips Demucs for development
- Supports: `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`
- Max file size: 100 MB

---

### Dependencies Added
```
fastapi>=0.109.0
uvicorn>=0.27.0
python-multipart>=0.0.6
demucs>=4.0.0
librosa>=0.10.0
torch>=2.0.0
numpy>=1.24.0
soundfile>=0.12.0
```

---

### Verification Results

**Server Test:**
```
curl http://127.0.0.1:8000/
→ {"status":"ok","message":"Flow-to-Lyrics API v1.0","mock_mode":true}
```

**Synthetic Test (2s sine wave):**
| Metric | Value |
|--------|-------|
| Tempo | 0.0 BPM (expected for pure tone) |
| Duration | 2.00s |
| Onsets Detected | 18 |

**Real Audio Test (vocal mumbling MP3):**
| Metric | Value |
|--------|-------|
| Tempo (Detected) | 123.05 BPM |
| Tempo (Actual) | **130 BPM** (~5% variance) |
| Duration | 11.65s |
| Onsets Detected | **28 syllables** |
| Segment Durations | 0.116s - 2.02s (variable) |
| File Size | 295 KB |

---

### Pivot JSON Output Structure
```json
{
  "meta": { "tempo": 0.0, "duration": 2.0 },
  "blocks": [{
    "id": 1,
    "syllable_target": 18,
    "segments": [
      { "time_start": 0.07, "duration": 0.186, "is_stressed": false }
    ]
  }],
  "_meta": { "filename": "test_audio.wav", "mock_mode": true }
}
```

### Known Limitations (MVP)

| Issue | Description | Phase 2 Fix |
|-------|-------------|-------------|
| **BPM Accuracy** | ~5% variance from actual tempo (123 vs 130) | Use `librosa.beat.tempo()` with prior estimation |
| **Sustained Notes** | "Meeeee" (3.7s-5.7s) appears as long single segment, not multiple syllables | Add amplitude envelope analysis to detect held vowels |
| **No Stress Detection** | All `is_stressed: false` | Use amplitude peaks for syllable stress |

> **Note**: The 2.02s segment at 3.715s represents a sustained vowel ("Me" → "Meeeee"), not a pause. Current onset detection only finds syllable starts, not continuations.

---

### Next Steps (Phase 2)
- Connect to real Demucs (disable mock mode)
- Add stress pattern detection (amplitude peaks)
- Implement bar/phrase block splitting
- Add sustained note detection via amplitude envelope
- Connect with Phase 0 lyric generation engine
