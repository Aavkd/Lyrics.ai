"""
Flow-to-Lyrics: API Server
==========================
Phase 1 - Audio Analysis Backend

FastAPI application that:
1. Accepts audio file uploads (MP3/WAV)
2. Processes them through the audio engine
3. Returns the Pivot JSON for frontend consumption

Configuration:
    All settings are loaded from .env file via config module.
    See .env.example for available options.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from audio_engine import AudioEngine, PivotJSON
from config import config


# =============================================================================
# CONFIGURATION
# =============================================================================

# Use centralized config module
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}


# =============================================================================
# APPLICATION SETUP
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("=" * 60)
    print("  Flow-to-Lyrics API v1.0")
    print("=" * 60)
    print(f"  LLM Model: {config.OLLAMA_MODEL}")
    print(f"  Mock Mode: {config.MOCK_MODE}")
    print(f"  Allowed Extensions: {ALLOWED_EXTENSIONS}")
    print(f"  Max File Size: {config.MAX_FILE_SIZE_MB} MB")
    print("=" * 60)
    
    yield
    
    # Shutdown
    print("Flow-to-Lyrics API shutting down...")


app = FastAPI(
    title="Flow-to-Lyrics API",
    description="Audio Analysis Backend for vocal-to-lyrics conversion",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def validate_file_extension(filename: str) -> bool:
    """Check if file has an allowed extension."""
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def save_upload_file(upload_file: UploadFile, destination: Path) -> None:
    """Save uploaded file to destination."""
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)


# =============================================================================
# ROUTES
# =============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "Flow-to-Lyrics API v1.0",
        "mock_mode": config.MOCK_MODE,
        "llm_model": config.OLLAMA_MODEL
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "mock_mode": config.MOCK_MODE,
        "llm_model": config.OLLAMA_MODEL,
        "ollama_url": config.OLLAMA_URL,
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "max_file_size_mb": config.MAX_FILE_SIZE_MB
    }


@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    """
    Upload an audio file for analysis.
    
    Accepts: MP3, WAV, M4A, FLAC, OGG
    Returns: Pivot JSON with tempo, duration, and onset segments
    
    The pipeline:
    1. Save uploaded file to temp directory
    2. Isolate vocals via Demucs (or skip if mock_mode)
    3. Analyze rhythm via Librosa (BPM, onsets)
    4. Format and return Pivot JSON
    5. Clean up temp files
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    if not validate_file_extension(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Create temp directory for processing
    temp_dir = tempfile.mkdtemp(prefix="flow_to_lyrics_")
    temp_file_path = Path(temp_dir) / file.filename
    
    try:
        # Save uploaded file
        save_upload_file(file, temp_file_path)
        print(f"[API] Saved upload to: {temp_file_path}")
        
        # Check file size
        file_size = temp_file_path.stat().st_size
        if file_size > config.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {config.MAX_FILE_SIZE_MB} MB"
            )
        
        print(f"[API] File size: {file_size / 1024 / 1024:.2f} MB")
        
        # Process through audio engine
        engine = AudioEngine(mock_mode=config.MOCK_MODE)
        pivot_json = engine.process(str(temp_file_path), output_dir=temp_dir)
        
        # Convert to dict for JSON response
        result = pivot_json.to_dict()
        
        # Add processing metadata
        result["_meta"] = {
            "filename": file.filename,
            "file_size_bytes": file_size,
            "mock_mode": config.MOCK_MODE,
            "llm_model": config.OLLAMA_MODEL
        }
        
        print(f"[API] Processing complete. Tempo: {result['meta']['tempo']} BPM")
        print(f"[API] Segments detected: {len(result['blocks'][0]['segments'])}")
        
        return JSONResponse(content=result)
    
    except HTTPException:
        raise
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        print(f"[API] Error processing file: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
    finally:
        # Cleanup temp files
        try:
            shutil.rmtree(temp_dir)
            print(f"[API] Cleaned up temp dir: {temp_dir}")
        except Exception as cleanup_error:
            print(f"[API] Warning: Failed to cleanup temp dir: {cleanup_error}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
