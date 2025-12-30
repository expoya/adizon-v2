"""
Whisper Transcriber - Self-hosted Whisper on trooper.ai

Handles audio transcription via self-hosted Whisper model.
Supports multiple audio formats (ogg, mp3, wav, m4a).
"""

import os
import time
import requests
from typing import Optional, Dict
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    """Result from audio transcription"""
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None
    confidence: Optional[float] = None


class TranscriptionError(Exception):
    """Base exception for transcription errors"""
    pass


class WhisperAPIError(TranscriptionError):
    """Whisper API returned an error"""
    pass


class WhisperTimeoutError(TranscriptionError):
    """Whisper API timeout"""
    pass


class WhisperTranscriber:
    """
    Whisper Transcriber for self-hosted Whisper on trooper.ai
    
    Supports flexible API formats:
    - REST API (POST /transcribe)
    - Direct Python library calls
    - gRPC (future)
    """
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
        retry_count: int = 3,
        language: str = "de"
    ):
        """
        Initialize Whisper Transcriber
        
        Args:
            api_url: Whisper API endpoint (default: from env WHISPER_API_URL)
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds (default: 30)
            retry_count: Number of retry attempts (default: 3)
            language: Default language for transcription (default: "de")
        """
        self.api_url = api_url or os.getenv("WHISPER_API_URL")
        self.api_key = api_key or os.getenv("WHISPER_API_KEY")
        self.timeout = int(os.getenv("WHISPER_TIMEOUT", timeout))
        self.retry_count = int(os.getenv("WHISPER_RETRY_COUNT", retry_count))
        self.language = language
        
        if not self.api_url:
            print("⚠️  WHISPER_API_URL not set - Whisper transcription disabled")
    
    def is_enabled(self) -> bool:
        """Check if Whisper transcription is enabled"""
        return bool(self.api_url)
    
    def transcribe(
        self,
        audio_file_path: str,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio file to text
        
        Args:
            audio_file_path: Path to audio file (ogg, mp3, wav, m4a)
            language: Override default language (optional)
            
        Returns:
            TranscriptionResult with text and metadata
            
        Raises:
            TranscriptionError: If transcription fails
            WhisperAPIError: If API returns error
            WhisperTimeoutError: If request times out
        """
        if not self.is_enabled():
            raise TranscriptionError("Whisper API not configured (WHISPER_API_URL missing)")
        
        if not os.path.exists(audio_file_path):
            raise TranscriptionError(f"Audio file not found: {audio_file_path}")
        
        # Use provided language or default
        lang = language or self.language
        
        # Retry logic
        last_exception = None
        for attempt in range(1, self.retry_count + 1):
            try:
                print(f"🎤 Transcribing audio (attempt {attempt}/{self.retry_count})...")
                result = self._call_whisper_api(audio_file_path, lang)
                print(f"✅ Transcription successful: {len(result.text)} chars")
                return result
            
            except WhisperTimeoutError as e:
                last_exception = e
                print(f"⏱️  Timeout on attempt {attempt}/{self.retry_count}")
                if attempt < self.retry_count:
                    time.sleep(2 ** (attempt - 1))  # Exponential backoff: 1s, 2s, 4s
                continue
            
            except WhisperAPIError as e:
                last_exception = e
                print(f"❌ API Error on attempt {attempt}/{self.retry_count}: {e}")
                if attempt < self.retry_count:
                    time.sleep(2 ** (attempt - 1))
                continue
            
            except Exception as e:
                last_exception = e
                print(f"❌ Unexpected error on attempt {attempt}/{self.retry_count}: {e}")
                if attempt < self.retry_count:
                    time.sleep(2 ** (attempt - 1))
                continue
        
        # All retries failed
        raise TranscriptionError(
            f"Transcription failed after {self.retry_count} attempts: {last_exception}"
        )
    
    def _call_whisper_api(
        self,
        audio_file_path: str,
        language: str
    ) -> TranscriptionResult:
        """
        Call Whisper API (flexible implementation)
        
        This method can be adapted based on actual Whisper API format:
        - REST API with multipart/form-data
        - JSON API with base64 audio
        - gRPC calls
        - Direct Python library calls
        
        Current implementation: REST API assumption
        """
        start_time = time.time()
        
        try:
            # Prepare request
            with open(audio_file_path, 'rb') as audio_file:
                files = {'file': audio_file}
                data = {'language': language}
                
                # Add API key if configured
                headers = {}
                if self.api_key:
                    headers['Authorization'] = f'Bearer {self.api_key}'
                
                # Make request (API URL should be complete endpoint)
                response = requests.post(
                    self.api_url,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=self.timeout
                )
            
            duration = time.time() - start_time
            
            # Check response
            if response.status_code == 408 or response.status_code == 504:
                raise WhisperTimeoutError(f"Whisper API timeout after {duration:.1f}s")
            
            if response.status_code != 200:
                raise WhisperAPIError(
                    f"Whisper API returned {response.status_code}: {response.text}"
                )
            
            # Parse response
            result_data = response.json()
            
            # Flexible response format parsing
            # Supports various Whisper API response formats
            text = result_data.get('text') or result_data.get('transcription') or ""
            
            if not text:
                raise WhisperAPIError("Empty transcription returned by Whisper API")
            
            return TranscriptionResult(
                text=text.strip(),
                language=result_data.get('language'),
                duration=duration,
                confidence=result_data.get('confidence')
            )
        
        except requests.exceptions.Timeout:
            raise WhisperTimeoutError(f"Request timeout after {self.timeout}s")
        
        except requests.exceptions.ConnectionError as e:
            raise WhisperAPIError(f"Failed to connect to Whisper API: {e}")
        
        except requests.exceptions.RequestException as e:
            raise WhisperAPIError(f"Request failed: {e}")


# Global instance (lazy initialization)
_transcriber: Optional[WhisperTranscriber] = None


def get_transcriber() -> WhisperTranscriber:
    """
    Get global WhisperTranscriber instance (singleton)
    
    Returns:
        WhisperTranscriber instance
    """
    global _transcriber
    if _transcriber is None:
        _transcriber = WhisperTranscriber()
        if _transcriber.is_enabled():
            print(f"🎤 Whisper Transcriber initialized: {_transcriber.api_url}")
        else:
            print("⚠️  Whisper Transcriber disabled (no WHISPER_API_URL)")
    return _transcriber

