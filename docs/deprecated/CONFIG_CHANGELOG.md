# Configuration Refactor - Changelog

**Date:** December 28, 2025  
**Version:** 1.1  
**Focus:** Centralized configuration with `.env` file support

---

## Summary

This update introduces a centralized configuration system that allows easy switching of the LLM model and other settings via a `.env` file, without modifying source code.

---

## Problem Solved

Previously, the model name (`ministral-3:8b`) was hardcoded in multiple files:
- `generation_engine.py`
- `core_pipeline.py`
- `tests/test_generation.py`

Switching models required editing code in multiple locations.

---

## Solution

Created a new `config.py` module that:
1. Reads configuration from a `.env` file in the project root
2. Provides sensible defaults if no `.env` file exists
3. Exposes type-safe properties for all settings

---

## How to Switch Models

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and change the model:
   ```bash
   # Change from:
   OLLAMA_MODEL=ministral-3:8b
   
   # To (for example):
   OLLAMA_MODEL=mistral:7b
   # or
   OLLAMA_MODEL=llama3:8b
   # or
   OLLAMA_MODEL=qwen2:7b
   ```

3. Restart the backend - the new model will be used automatically.

---

## Available Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `ministral-3:8b` | LLM model name for Ollama |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_TEMPERATURE` | `0.7` | Generation creativity (0.0-1.0) |
| `OLLAMA_TIMEOUT` | `60` | Request timeout in seconds |
| `MOCK_MODE` | `true` | Skip Demucs for faster dev testing |
| `API_HOST` | `0.0.0.0` | Server bind address |
| `API_PORT` | `8000` | Server port |
| `MAX_FILE_SIZE_MB` | `100` | Maximum upload size |

---

## Files Created

| File | Purpose |
|------|---------|
| `config.py` | Centralized configuration module |
| `.env.example` | Template showing all available options |

---

## Files Modified

| File | Changes |
|------|---------|
| `generation_engine.py` | Uses `config` module for defaults |
| `core_pipeline.py` | Uses `config` module for defaults |
| `main.py` | Uses `config` module for all settings |
| `tests/test_generation.py` | Uses `config` module, model-agnostic tests |

---

## Verification

Run the config module directly to see current settings:

```bash
python config.py
```

Output:
```
🔧 Flow-to-Lyrics Configuration Module

==================================================
  🔧 Flow-to-Lyrics Configuration
==================================================
  LLM Model:    ministral-3:8b
  Ollama URL:   http://localhost:11434
  Temperature:  0.7
  Timeout:      60s
  Mock Mode:    True
  API:          0.0.0.0:8000
  Max Upload:   100 MB
==================================================
```

---

## API Changes

The `/health` endpoint now returns LLM configuration:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "mock_mode": true,
  "llm_model": "ministral-3:8b",
  "ollama_url": "http://localhost:11434",
  "allowed_extensions": [".mp3", ".wav", ".m4a", ".flac", ".ogg"],
  "max_file_size_mb": 100
}
```

---

## Next Steps

1. Create your `.env` file from the template
2. Test with different models (e.g., `mistral:7b`, `llama3:8b`)
3. Find a more reliable model for your use case
