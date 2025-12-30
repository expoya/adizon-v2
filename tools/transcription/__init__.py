"""
Transcription Module - Voice-to-Text Services

Provides abstraction layer for various Speech-to-Text services.
Currently supports: Whisper (self-hosted on trooper.ai)
"""

from .whisper_transcriber import WhisperTranscriber, get_transcriber

__all__ = ["WhisperTranscriber", "get_transcriber"]

