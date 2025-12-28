"""
Flow-to-Lyrics: Generation Engine
==================================
Step 3 of the Tech Roadmap - The "Brain"

This module handles LLM interactions with a local Ollama instance to generate
lyric candidates from structured prompts. Model is configurable via .env file.

Key Features:
- HTTP-based communication with Ollama (no custom library dependencies)
- Robust JSON parsing for "chatty" model output
- Mock mode for testing without Ollama
- Configurable model and temperature settings via .env file

Configuration (in .env file):
    OLLAMA_MODEL=mistral:7b     # Switch to any Ollama model
    OLLAMA_URL=http://localhost:11434
    OLLAMA_TEMPERATURE=0.7
    OLLAMA_TIMEOUT=60
"""

from __future__ import annotations

import json
import re
from typing import Optional

import requests

from config import config


# =============================================================================
# GENERATION ENGINE
# =============================================================================

class GenerationEngine:
    """
    LLM interface for generating lyric candidates via Ollama.
    
    Communicates with a local Ollama instance using standard HTTP requests.
    Model configuration is loaded from .env file via the config module.
    
    Usage:
        engine = GenerationEngine()  # Uses config defaults
        candidates = engine.generate_candidates(system_prompt, user_prompt)
        # Returns: ["line 1", "line 2", "line 3", ...]
    
    Mock Mode:
        engine = GenerationEngine(mock_mode=True)
        # Returns predefined candidates without making API calls
    
    Configuration via .env:
        OLLAMA_MODEL=mistral:7b
        OLLAMA_URL=http://localhost:11434
        OLLAMA_TEMPERATURE=0.7
        OLLAMA_TIMEOUT=60
    
    Attributes:
        model: Name of the Ollama model (from config or override).
        base_url: Ollama API base URL (from config or override).
        temperature: Generation temperature (from config or override).
        mock_mode: If True, return mock data without API calls.
    """
    
    # Default mock candidates for testing
    MOCK_CANDIDATES = [
        "Riding through the city",
        "Never looking back now",
        "Money on my mind state",
        "Living for the moment",
        "Sky is not the limit"
    ]
    
    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        candidate_count: int = 5,
        mock_mode: bool = False,
        timeout: Optional[int] = None
    ):
        """
        Initialize the Generation Engine.
        
        Args:
            model: Ollama model name. Defaults to config.OLLAMA_MODEL.
            base_url: Ollama API base URL. Defaults to config.OLLAMA_URL.
            temperature: LLM sampling temperature (0.0-1.0). Higher = more creative.
                        Defaults to config.OLLAMA_TEMPERATURE.
            candidate_count: Number of candidates to request (default: 5).
            mock_mode: If True, skip API calls and return mock data.
            timeout: Request timeout in seconds. Defaults to config.OLLAMA_TIMEOUT.
        """
        # Use config defaults if not explicitly provided
        self.model = model if model is not None else config.OLLAMA_MODEL
        self.base_url = (base_url if base_url is not None else config.OLLAMA_URL).rstrip("/")
        self.temperature = temperature if temperature is not None else config.OLLAMA_TEMPERATURE
        self.timeout = timeout if timeout is not None else config.OLLAMA_TIMEOUT
        
        self.candidate_count = candidate_count
        self.mock_mode = mock_mode
        
        # API endpoint for chat completions
        self.chat_endpoint = f"{self.base_url}/api/chat"
    
    def generate_candidates(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> list[str]:
        """
        Generate lyric candidates from the given prompts.
        
        Sends the system and user prompts to Ollama, receives the response,
        and parses it into a list of candidate strings.
        
        Args:
            system_prompt: The system instruction (persona, rules, examples).
            user_prompt: The user request (syllable count, stress pattern, etc.).
            
        Returns:
            List of candidate lyric strings.
            
        Raises:
            requests.RequestException: If the API call fails.
            ValueError: If the response cannot be parsed.
        """
        if self.mock_mode:
            return self._generate_mock_response()
        
        # Construct the Ollama chat payload
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,  # Get complete response at once
            "options": {
                "temperature": self.temperature
            }
        }
        
        try:
            response = requests.post(
                self.chat_endpoint,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Parse the Ollama response
            result = response.json()
            content = result.get("message", {}).get("content", "")
            
            if not content:
                raise ValueError("Empty response from Ollama")
            
            # Clean and parse the JSON from potentially "chatty" output
            return self._clean_and_parse_json(content)
            
        except requests.RequestException as e:
            raise RuntimeError(f"Ollama API request failed: {e}") from e
    
    def _generate_mock_response(self) -> list[str]:
        """
        Generate mock candidates for testing.
        
        Returns:
            List of predefined candidate strings.
        """
        return self.MOCK_CANDIDATES.copy()
    
    def _clean_and_parse_json(self, response_text: str) -> list[str]:
        """
        Robustly extract and parse JSON from LLM response.
        
        Small local models often wrap their JSON output in:
        - Markdown code blocks (```json ... ```)
        - Conversational text ("Here is the result: ...")
        - Extra whitespace or newlines
        
        This method handles all these cases by:
        1. Stripping markdown code block markers
        2. Finding the first '{' and last '}' to extract pure JSON
        3. Handling common JSON errors (trailing commas)
        4. Falling back to line splitting if JSON parsing fails
        
        Args:
            response_text: Raw LLM response text.
            
        Returns:
            List of candidate strings from the parsed JSON.
            If JSON parsing fails, returns the response split by newlines.
        """
        text = response_text.strip()
        
        # Step 1: Remove markdown code block markers
        # Pattern: ```json ... ``` or just ``` ... ```
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Step 2: Find the JSON object boundaries
        # Look for first '{' and last '}'
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        
        if first_brace == -1 or last_brace == -1 or first_brace >= last_brace:
            # No valid JSON object found, fall back to line splitting
            return self._fallback_line_split(response_text)
        
        json_str = text[first_brace:last_brace + 1]
        
        # Step 3: Try to parse the JSON
        try:
            parsed = json.loads(json_str)
            candidates = parsed.get("candidates", [])
            
            if isinstance(candidates, list) and all(isinstance(c, str) for c in candidates):
                return candidates
            else:
                return self._fallback_line_split(response_text)
                
        except json.JSONDecodeError:
            # Step 4: Try fixing common JSON errors
            fixed_json = self._fix_common_json_errors(json_str)
            
            try:
                parsed = json.loads(fixed_json)
                candidates = parsed.get("candidates", [])
                
                if isinstance(candidates, list) and all(isinstance(c, str) for c in candidates):
                    return candidates
                    
            except json.JSONDecodeError:
                pass
        
        # All JSON parsing failed, use fallback
        return self._fallback_line_split(response_text)
    
    def _fix_common_json_errors(self, json_str: str) -> str:
        """
        Attempt to fix common JSON syntax errors from LLMs.
        
        Common errors from 3B models:
        - Trailing commas: {"candidates": ["a", "b", ]}
        - Unescaped quotes within strings
        - Missing quotes around keys
        
        Args:
            json_str: Potentially malformed JSON string.
            
        Returns:
            Fixed JSON string (best effort).
        """
        # Fix trailing commas before closing brackets
        # Match: comma + optional whitespace + closing bracket
        fixed = re.sub(r',\s*]', ']', json_str)
        fixed = re.sub(r',\s*}', '}', fixed)
        
        return fixed
    
    def _fallback_line_split(self, text: str) -> list[str]:
        """
        Fallback parsing method when JSON extraction fails.
        
        Splits the text by newlines and filters out empty lines
        and obvious non-lyric content (like "Here is..." phrases).
        
        Args:
            text: Raw LLM response text.
            
        Returns:
            List of non-empty lines that look like lyrics.
        """
        lines = text.strip().split('\n')
        
        # Filter criteria for actual lyric lines
        candidates = []
        skip_patterns = [
            r'^(here|sure|okay|of course)',  # Common chatty prefixes
            r'^```',                          # Code block markers
            r'^{',                            # JSON starts
            r'^}',                            # JSON ends
            r'^\d+\.',                         # Numbered lists
            r'^-\s*$',                         # Just dashes
            r'^\s*$',                          # Empty lines
        ]
        
        for line in lines:
            line = line.strip()
            
            # Skip lines matching skip patterns
            skip = False
            for pattern in skip_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    skip = True
                    break
            
            if not skip and line:
                # Clean up any remaining artifacts
                line = re.sub(r'^["\']\s*', '', line)  # Leading quotes
                line = re.sub(r'\s*["\']$', '', line)  # Trailing quotes
                line = re.sub(r'^-\s*', '', line)      # Leading dashes
                
                if line and len(line) > 3:  # Must have some content
                    candidates.append(line)
        
        return candidates[:self.candidate_count]
    
    def test_connection(self) -> bool:
        """
        Test if Ollama is accessible and the model is available.
        
        Returns:
            True if connection successful, False otherwise.
        """
        if self.mock_mode:
            return True
        
        try:
            # Check if Ollama is running
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            response.raise_for_status()
            
            # Check if the specified model is available
            models = response.json().get("models", [])
            model_names = [m.get("name", "").split(":")[0] for m in models]
            
            if self.model.split(":")[0] not in model_names:
                print(f"⚠️ Model '{self.model}' not found. Available: {model_names}")
                return False
            
            return True
            
        except requests.RequestException as e:
            print(f"❌ Cannot connect to Ollama at {self.base_url}: {e}")
            return False


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    print("\n🧠 Testing GenerationEngine...")
    print("=" * 60)
    
    # Test 1: Mock mode
    print("\n1️⃣ Testing Mock Mode:")
    engine = GenerationEngine(mock_mode=True)
    candidates = engine.generate_candidates(
        system_prompt="You are a lyricist.",
        user_prompt="Write a line with 5 syllables."
    )
    print(f"   Candidates: {candidates}")
    assert len(candidates) == 5, "Expected 5 mock candidates"
    print("   ✅ Mock mode works correctly")
    
    # Test 2: JSON parsing
    print("\n2️⃣ Testing JSON Parsing:")
    dirty_response = '''
    Sure! Here are 5 variations:
    
    ```json
    {
        "candidates": [
            "Riding through the night",
            "Breaking all the rules",
            "Living on the edge",
            "Running from the past",
            "Chasing down my dreams"
        ]
    }
    ```
    
    Hope these work for you!
    '''
    
    parsed = engine._clean_and_parse_json(dirty_response)
    print(f"   Parsed {len(parsed)} candidates from dirty response")
    assert len(parsed) == 5, f"Expected 5 candidates, got {len(parsed)}"
    print("   ✅ JSON parsing works correctly")
    
    # Test 3: Connection test (if not mock)
    print("\n3️⃣ Testing Ollama Connection:")
    real_engine = GenerationEngine(mock_mode=False)
    if real_engine.test_connection():
        print("   ✅ Connected to Ollama successfully")
    else:
        print("   ⚠️ Ollama not running or model not found (this is OK for tests)")
    
    print("\n" + "=" * 60)
    print("✅ GenerationEngine module ready!")
    print("=" * 60)
