"""
Flow-to-Lyrics: Configuration Module
=====================================
Centralizes all application configuration with `.env` file support.

This module provides:
- Environment variable loading from `.env` file
- Type-safe configuration access
- Sensible defaults for all settings

Usage:
    from config import config
    
    model = config.OLLAMA_MODEL  # e.g., "mistral:7b"
    url = config.OLLAMA_URL      # e.g., "http://localhost:11434"
"""

from __future__ import annotations

import os
from pathlib import Path


# =============================================================================
# .ENV FILE LOADING
# =============================================================================

def _load_dotenv():
    """Load environment variables from .env file if it exists."""
    env_path = Path(__file__).parent / ".env"
    
    if not env_path.exists():
        return
    
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            
            # Parse KEY=VALUE (handle inline comments)
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.split("#")[0].strip()  # Remove inline comments
                
                # Remove surrounding quotes if present
                if value and value[0] in ('"', "'") and value[-1] == value[0]:
                    value = value[1:-1]
                
                # Only set if not already in environment
                if key and key not in os.environ:
                    os.environ[key] = value


# Load .env file on module import
_load_dotenv()


# =============================================================================
# CONFIGURATION CLASS
# =============================================================================

class Config:
    """Application configuration with environment variable support.
    
    All configuration options can be overridden via environment variables
    or a `.env` file in the project root.
    
    Attributes:
        OLLAMA_MODEL: LLM model name (default: "ministral-3:8b").
        OLLAMA_URL: Ollama API base URL (default: "http://localhost:11434").
        OLLAMA_TEMPERATURE: Generation temperature (default: 0.7).
        OLLAMA_TIMEOUT: Request timeout in seconds (default: 60).
        MOCK_MODE: Enable mock mode for development (default: True).
        API_HOST: Server host (default: "0.0.0.0").
        API_PORT: Server port (default: 8000).
        MAX_FILE_SIZE_MB: Max upload size in MB (default: 100).
    """
    
    # =========================================================================
    # LLM CONFIGURATION
    # =========================================================================
    
    @property
    def OLLAMA_MODEL(self) -> str:
        """LLM model name for Ollama."""
        return os.getenv("OLLAMA_MODEL", "ministral-3:8b")
    
    @property
    def OLLAMA_URL(self) -> str:
        """Ollama API base URL."""
        return os.getenv("OLLAMA_URL", "http://localhost:11434")
    
    @property
    def OLLAMA_TEMPERATURE(self) -> float:
        """LLM generation temperature (0.0 to 1.0)."""
        try:
            return float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
        except ValueError:
            return 0.7
    
    @property
    def OLLAMA_TIMEOUT(self) -> int:
        """Request timeout in seconds."""
        try:
            return int(os.getenv("OLLAMA_TIMEOUT", "60"))
        except ValueError:
            return 60
    
    @property
    def OLLAMA_API_KEY(self) -> str | None:
        """API key for cloud Ollama services (None for local Ollama)."""
        key = os.getenv("OLLAMA_API_KEY", "")
        return key if key else None
    
    # =========================================================================
    # AUDIO ENGINE
    # =========================================================================
    
    @property
    def MOCK_MODE(self) -> bool:
        """Enable mock mode (skips Demucs)."""
        return os.getenv("MOCK_MODE", "true").lower() == "true"
    
    @property
    def ONSET_DELTA(self) -> float:
        """Onset detection sensitivity threshold.
        
        Lower values = more sensitive (more onsets detected).
        Higher values = less sensitive (fewer false positives).
        
        Recommended range: 0.03 (very sensitive) to 0.15 (conservative).
        Default: 0.05 (balanced for vocals).
        """
        try:
            return float(os.getenv("ONSET_DELTA", "0.05"))
        except ValueError:
            return 0.05
    
    @property
    def ONSET_USE_ENERGY(self) -> bool:
        """Use energy-based onset detection in addition to spectral flux.
        
        When enabled, combines spectral flux detection with energy peak
        detection for more robust syllable identification.
        """
        return os.getenv("ONSET_USE_ENERGY", "true").lower() == "true"
    
    @property
    def MAX_SEGMENT_DURATION(self) -> float:
        """Maximum segment duration before automatic splitting.
        
        Segments longer than this threshold will be split at energy
        valleys to prevent multi-syllable segments.
        
        Default: 1.0 seconds. Only very long segments will be split.
        (Typical syllables are 0.1-0.4s, sustained notes can be 0.5-0.8s)
        """
        try:
            return float(os.getenv("MAX_SEGMENT_DURATION", "1.0"))
        except ValueError:
            return 1.0
    
    @property
    def ONSET_WAIT(self) -> int:
        """Minimum frames between consecutive detected onsets.
        
        Helps prevent detecting the same event multiple times.
        Default: 1 frame.
        """
        try:
            return int(os.getenv("ONSET_WAIT", "1"))
        except ValueError:
            return 1
    
    # =========================================================================
    # PHONETIC ANALYSIS
    # =========================================================================
    
    @property
    def PHONETIC_MODEL(self) -> str:
        """Phonetic recognition backend.
        
        Options:
            - "whisper": Whisper + g2p_en (recommended for mumbled/sung vocals)
            - "allosaurus": Universal phone recognizer (original)
        
        Default: "whisper" for better accuracy on non-standard speech.
        """
        model = os.getenv("PHONETIC_MODEL", "whisper").lower()
        if model not in ("whisper", "allosaurus"):
            return "whisper"  # Default to whisper if invalid
        return model
    
    @property
    def WHISPER_MODEL_SIZE(self) -> str:
        """Whisper model size (only used when PHONETIC_MODEL=whisper).
        
        Options:
            - "tiny": 39MB, fastest, least accurate
            - "base": 140MB, balanced (default)
            - "small": 244MB, good accuracy
            - "medium": 769MB, high accuracy
            - "large": 2.9GB, highest accuracy
        """
        size = os.getenv("WHISPER_MODEL_SIZE", "base").lower()
        valid_sizes = ("tiny", "base", "small", "medium", "large")
        if size not in valid_sizes:
            return "base"  # Default to base if invalid
        return size
    
    @property
    def WHISPER_USE_FULL_AUDIO(self) -> bool:
        """Use full-audio transcription with word alignment.
        
        When True (default), transcribes the entire audio once and aligns
        words to segments based on timing. Much more accurate for short
        segments (<500ms) because Whisper has full linguistic context.
        
        When False, uses per-segment transcription (legacy behavior).
        """
        return os.getenv("WHISPER_USE_FULL_AUDIO", "true").lower() == "true"
    
    @property
    def PHONETIC_ENABLED(self) -> bool:
        """Enable phonetic analysis."""
        return os.getenv("PHONETIC_ENABLED", "true").lower() == "true"
    
    @property
    def PHONETIC_MIN_DURATION(self) -> float:
        """Minimum segment duration for phonetic analysis (seconds).
        
        Segments shorter than this will return empty phonemes.
        Default: 0.10 (100ms) - Allosaurus needs sufficient context.
        """
        try:
            return float(os.getenv("PHONETIC_MIN_DURATION", "0.10"))
        except ValueError:
            return 0.10
    
    @property
    def PHONETIC_PADDING(self) -> float:
        """Padding on each side of segment for acoustic context (seconds).
        
        Adds audio context before/after each segment to improve
        Allosaurus recognition at segment boundaries.
        Default: 0.05 (50ms on each side).
        """
        try:
            return float(os.getenv("PHONETIC_PADDING", "0.05"))
        except ValueError:
            return 0.05
    
    @property
    def PHONETIC_RETRY_PADDING(self) -> float:
        """Expanded retry padding when first attempt fails (seconds).
        
        If Allosaurus returns empty on first try, retry with this
        additional padding on each side.
        Default: 0.10 (100ms additional context).
        """
        try:
            return float(os.getenv("PHONETIC_RETRY_PADDING", "0.10"))
        except ValueError:
            return 0.10
    
    @property
    def PHONETIC_FALLBACK_ENABLED(self) -> bool:
        """Enable vowel/consonant fallback when Allosaurus fails.
        
        When enabled, uses spectral features to classify segments
        as [vowel], [consonant], or [mid] when Allosaurus returns empty.
        """
        return os.getenv("PHONETIC_FALLBACK_ENABLED", "true").lower() == "true"
    
    # =========================================================================
    # SERVER CONFIGURATION
    # =========================================================================
    
    @property
    def API_HOST(self) -> str:
        """API server host."""
        return os.getenv("API_HOST", "0.0.0.0")
    
    @property
    def API_PORT(self) -> int:
        """API server port."""
        try:
            return int(os.getenv("API_PORT", "8000"))
        except ValueError:
            return 8000
    
    @property
    def MAX_FILE_SIZE_MB(self) -> int:
        """Maximum file upload size in MB."""
        try:
            return int(os.getenv("MAX_FILE_SIZE_MB", "100"))
        except ValueError:
            return 100
    
    @property
    def MAX_FILE_SIZE(self) -> int:
        """Maximum file upload size in bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def __repr__(self) -> str:
        """Return a string representation showing current config."""
        api_key_display = "***" if self.OLLAMA_API_KEY else "(not set)"
        return (
            f"Config(\n"
            f"  OLLAMA_MODEL={self.OLLAMA_MODEL!r},\n"
            f"  OLLAMA_URL={self.OLLAMA_URL!r},\n"
            f"  OLLAMA_TEMPERATURE={self.OLLAMA_TEMPERATURE},\n"
            f"  OLLAMA_TIMEOUT={self.OLLAMA_TIMEOUT},\n"
            f"  OLLAMA_API_KEY={api_key_display},\n"
            f"  MOCK_MODE={self.MOCK_MODE},\n"
            f"  API_HOST={self.API_HOST!r},\n"
            f"  API_PORT={self.API_PORT},\n"
            f"  MAX_FILE_SIZE_MB={self.MAX_FILE_SIZE_MB}\n"
            f")"
        )
    
    def print_config(self) -> None:
        """Print current configuration to console."""
        print("\n" + "=" * 50)
        print("  🔧 Flow-to-Lyrics Configuration")
        print("=" * 50)
        api_key_status = "✓ Set" if self.OLLAMA_API_KEY else "✗ Not set (local mode)"
        print(f"  LLM Model:    {self.OLLAMA_MODEL}")
        print(f"  Ollama URL:   {self.OLLAMA_URL}")
        print(f"  Temperature:  {self.OLLAMA_TEMPERATURE}")
        print(f"  Timeout:      {self.OLLAMA_TIMEOUT}s")
        print(f"  API Key:      {api_key_status}")
        print(f"  Mock Mode:    {self.MOCK_MODE}")
        print(f"  API:          {self.API_HOST}:{self.API_PORT}")
        print(f"  Max Upload:   {self.MAX_FILE_SIZE_MB} MB")
        print("=" * 50 + "\n")


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

config = Config()


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    print("🔧 Flow-to-Lyrics Configuration Module")
    config.print_config()
    print(repr(config))
