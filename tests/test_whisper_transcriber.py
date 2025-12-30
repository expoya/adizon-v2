"""
Tests for Whisper Transcriber Service

Tests transcription functionality with mocked Whisper API.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from tools.transcription.whisper_transcriber import (
    WhisperTranscriber,
    TranscriptionResult,
    TranscriptionError,
    WhisperAPIError,
    WhisperTimeoutError
)


class TestWhisperTranscriber:
    """Test suite for WhisperTranscriber"""
    
    def test_init_with_env_vars(self):
        """Test: Initialization mit Environment Variables"""
        with patch.dict(os.environ, {
            "WHISPER_API_URL": "https://trooper.ai/whisper",
            "WHISPER_API_KEY": "test-key",
            "WHISPER_TIMEOUT": "20",
            "WHISPER_RETRY_COUNT": "2"
        }):
            transcriber = WhisperTranscriber()
            
            assert transcriber.api_url == "https://trooper.ai/whisper"
            assert transcriber.api_key == "test-key"
            assert transcriber.timeout == 20
            assert transcriber.retry_count == 2
    
    def test_init_with_params(self):
        """Test: Initialization mit direkten Parametern"""
        transcriber = WhisperTranscriber(
            api_url="https://custom.ai/api",
            api_key="custom-key",
            timeout=15,
            retry_count=5
        )
        
        assert transcriber.api_url == "https://custom.ai/api"
        assert transcriber.api_key == "custom-key"
        assert transcriber.timeout == 15
        assert transcriber.retry_count == 5
    
    def test_is_enabled_true(self):
        """Test: is_enabled returns True wenn API URL gesetzt"""
        transcriber = WhisperTranscriber(api_url="https://test.ai")
        assert transcriber.is_enabled() is True
    
    def test_is_enabled_false(self):
        """Test: is_enabled returns False wenn keine API URL"""
        transcriber = WhisperTranscriber(api_url=None)
        assert transcriber.is_enabled() is False
    
    @patch('tools.transcription.whisper_transcriber.requests.post')
    @patch('builtins.open', create=True)
    def test_transcribe_success(self, mock_open, mock_post):
        """Test: Successful transcription"""
        # Mock file exists
        with patch('os.path.exists', return_value=True):
            # Mock API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "text": "Das ist ein Test",
                "language": "de",
                "confidence": 0.95
            }
            mock_post.return_value = mock_response
            
            # Mock file open
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # Transcribe
            transcriber = WhisperTranscriber(api_url="https://test.ai")
            result = transcriber.transcribe("/tmp/test.ogg")
            
            assert result.text == "Das ist ein Test"
            assert result.language == "de"
            assert result.confidence == 0.95
            assert result.duration is not None
    
    @patch('tools.transcription.whisper_transcriber.requests.post')
    @patch('builtins.open', create=True)
    def test_transcribe_alternative_response_format(self, mock_open, mock_post):
        """Test: Alternative API response format (transcription statt text)"""
        with patch('os.path.exists', return_value=True):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "transcription": "Alternative format test",
                "lang": "en"
            }
            mock_post.return_value = mock_response
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            transcriber = WhisperTranscriber(api_url="https://test.ai")
            result = transcriber.transcribe("/tmp/test.wav")
            
            assert result.text == "Alternative format test"
    
    def test_transcribe_not_enabled(self):
        """Test: TranscriptionError wenn Whisper nicht enabled"""
        transcriber = WhisperTranscriber(api_url=None)
        
        with pytest.raises(TranscriptionError, match="not configured"):
            transcriber.transcribe("/tmp/test.ogg")
    
    def test_transcribe_file_not_found(self):
        """Test: TranscriptionError wenn Audio-File nicht existiert"""
        with patch('os.path.exists', return_value=False):
            transcriber = WhisperTranscriber(api_url="https://test.ai")
            
            with pytest.raises(TranscriptionError, match="not found"):
                transcriber.transcribe("/tmp/nonexistent.ogg")
    
    @patch('tools.transcription.whisper_transcriber.requests.post')
    @patch('builtins.open', create=True)
    def test_transcribe_api_error(self, mock_open, mock_post):
        """Test: WhisperAPIError bei API-Fehler"""
        with patch('os.path.exists', return_value=True):
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            transcriber = WhisperTranscriber(
                api_url="https://test.ai",
                retry_count=1  # Nur 1 Versuch für schnellen Test
            )
            
            with pytest.raises(TranscriptionError, match="failed after"):
                transcriber.transcribe("/tmp/test.ogg")
    
    @patch('tools.transcription.whisper_transcriber.requests.post')
    @patch('builtins.open', create=True)
    def test_transcribe_timeout(self, mock_open, mock_post):
        """Test: Timeout Error"""
        with patch('os.path.exists', return_value=True):
            import requests
            mock_post.side_effect = requests.exceptions.Timeout()
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            transcriber = WhisperTranscriber(
                api_url="https://test.ai",
                retry_count=1,
                timeout=5
            )
            
            with pytest.raises(TranscriptionError, match="failed after"):
                transcriber.transcribe("/tmp/test.ogg")
    
    @patch('tools.transcription.whisper_transcriber.requests.post')
    @patch('builtins.open', create=True)
    @patch('time.sleep')  # Mock sleep um Tests zu beschleunigen
    def test_transcribe_retry_logic(self, mock_sleep, mock_open, mock_post):
        """Test: Retry Logic mit exponential backoff"""
        with patch('os.path.exists', return_value=True):
            # Erste 2 Calls: Fehler, 3. Call: Success
            mock_response_error = Mock()
            mock_response_error.status_code = 503
            mock_response_error.text = "Service Unavailable"
            
            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {"text": "Success after retry"}
            
            mock_post.side_effect = [
                mock_response_error,  # Attempt 1: Fail
                mock_response_error,  # Attempt 2: Fail
                mock_response_success  # Attempt 3: Success
            ]
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            transcriber = WhisperTranscriber(
                api_url="https://test.ai",
                retry_count=3
            )
            
            result = transcriber.transcribe("/tmp/test.ogg")
            
            assert result.text == "Success after retry"
            assert mock_post.call_count == 3
            # Check exponential backoff: sleep(1), sleep(2)
            assert mock_sleep.call_count == 2
    
    @patch('tools.transcription.whisper_transcriber.requests.post')
    @patch('builtins.open', create=True)
    def test_transcribe_empty_response(self, mock_open, mock_post):
        """Test: Error bei leerem Transcript"""
        with patch('os.path.exists', return_value=True):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"text": ""}  # Empty!
            mock_post.return_value = mock_response
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            transcriber = WhisperTranscriber(
                api_url="https://test.ai",
                retry_count=1
            )
            
            with pytest.raises(TranscriptionError, match="failed after"):
                transcriber.transcribe("/tmp/test.ogg")
    
    @patch('tools.transcription.whisper_transcriber.requests.post')
    @patch('builtins.open', create=True)
    def test_transcribe_with_custom_language(self, mock_open, mock_post):
        """Test: Transcription mit custom language parameter"""
        with patch('os.path.exists', return_value=True):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"text": "English test", "language": "en"}
            mock_post.return_value = mock_response
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            transcriber = WhisperTranscriber(api_url="https://test.ai")
            result = transcriber.transcribe("/tmp/test.wav", language="en")
            
            assert result.text == "English test"
            # Check dass language Parameter übergeben wurde
            call_data = mock_post.call_args[1]["data"]
            assert call_data["language"] == "en"
    
    @patch('tools.transcription.whisper_transcriber.requests.post')
    @patch('builtins.open', create=True)
    def test_transcribe_with_api_key(self, mock_open, mock_post):
        """Test: API Key wird im Authorization Header gesendet"""
        with patch('os.path.exists', return_value=True):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"text": "Auth test"}
            mock_post.return_value = mock_response
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            transcriber = WhisperTranscriber(
                api_url="https://test.ai",
                api_key="secret-key-123"
            )
            result = transcriber.transcribe("/tmp/test.ogg")
            
            # Check Authorization Header
            call_headers = mock_post.call_args[1]["headers"]
            assert "Authorization" in call_headers
            assert call_headers["Authorization"] == "Bearer secret-key-123"


class TestGlobalTranscriberInstance:
    """Test global transcriber singleton"""
    
    @patch('tools.transcription.whisper_transcriber.WhisperTranscriber')
    def test_get_transcriber_singleton(self, mock_class):
        """Test: get_transcriber returns same instance"""
        from tools.transcription.whisper_transcriber import get_transcriber, _transcriber
        
        # Reset global
        import tools.transcription.whisper_transcriber as module
        module._transcriber = None
        
        # Mock instance
        mock_instance = Mock()
        mock_instance.is_enabled.return_value = True
        mock_instance.api_url = "https://test.ai"
        mock_class.return_value = mock_instance
        
        # First call
        transcriber1 = get_transcriber()
        # Second call should return same instance
        transcriber2 = get_transcriber()
        
        assert transcriber1 is transcriber2
        assert mock_class.call_count == 1  # Only initialized once


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

