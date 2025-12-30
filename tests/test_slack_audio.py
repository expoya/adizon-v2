"""
Tests for Slack Audio File Support

Tests audio file handling in Slack adapter.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from tools.chat.slack_adapter import SlackAdapter
from tools.chat.interface import StandardMessage, WebhookParseError


class TestSlackAudioSupport:
    """Test suite for Slack audio file support"""
    
    @patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token-123"})
    def test_parse_audio_file_success(self):
        """Test: Audio file wird korrekt erkannt und transkribiert"""
        webhook_data = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "user": "U123456",
                "channel": "C789",
                "files": [{
                    "id": "F123",
                    "mimetype": "audio/mp3",
                    "url_private": "https://files.slack.com/files-pri/T123/file.mp3",
                    "size": 50000
                }]
            }
        }
        
        adapter = SlackAdapter()
        
        # Mock download and transcription
        with patch.object(adapter, '_download_audio_file', return_value="/tmp/test.mp3"):
            with patch.object(adapter, '_get_user_name', return_value="Max Test"):
                with patch('tools.transcription.get_transcriber') as mock_get_transcriber:
                    mock_transcriber = Mock()
                    mock_transcriber.is_enabled.return_value = True
                    mock_result = Mock()
                    mock_result.text = "This is an audio test"
                    mock_transcriber.transcribe.return_value = mock_result
                    mock_get_transcriber.return_value = mock_transcriber
                    
                    with patch('os.path.exists', return_value=True):
                        with patch('os.remove'):
                            msg = adapter.parse_incoming(webhook_data)
        
        assert msg.text == "This is an audio test"
        assert msg.user_id == "slack:U123456"
        assert msg.platform == "slack"
    
    @patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token-123"})
    def test_parse_text_message_still_works(self):
        """Test: Normale Text-Messages funktionieren weiterhin"""
        webhook_data = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "user": "U123456",
                "channel": "C789",
                "text": "Normal text message"
            }
        }
        
        adapter = SlackAdapter()
        
        with patch.object(adapter, '_get_user_name', return_value="Max Test"):
            msg = adapter.parse_incoming(webhook_data)
        
        assert msg.text == "Normal text message"
        assert msg.user_id == "slack:U123456"
    
    @patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token-123"})
    def test_parse_audio_missing_url_private(self):
        """Test: Error wenn audio file ohne url_private"""
        webhook_data = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "user": "U123456",
                "channel": "C789",
                "files": [{
                    "id": "F123",
                    "mimetype": "audio/wav"
                    # url_private fehlt!
                }]
            }
        }
        
        adapter = SlackAdapter()
        
        with patch.object(adapter, '_get_user_name', return_value="Max Test"):
            with pytest.raises(WebhookParseError, match="Missing 'url_private'"):
                adapter.parse_incoming(webhook_data)
    
    @patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token-123"})
    def test_parse_audio_transcriber_disabled(self):
        """Test: Error Message wenn Whisper nicht verfügbar"""
        webhook_data = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "user": "U123456",
                "channel": "C789",
                "files": [{
                    "id": "F123",
                    "mimetype": "audio/ogg",
                    "url_private": "https://files.slack.com/file.ogg",
                    "size": 30000
                }]
            }
        }
        
        adapter = SlackAdapter()
        
        with patch.object(adapter, '_download_audio_file', return_value="/tmp/test.ogg"):
            with patch.object(adapter, '_get_user_name', return_value="Max Test"):
                with patch('tools.transcription.get_transcriber') as mock_get_transcriber:
                    mock_transcriber = Mock()
                    mock_transcriber.is_enabled.return_value = False  # Disabled!
                    mock_get_transcriber.return_value = mock_transcriber
                    
                    with pytest.raises(WebhookParseError, match="nicht verfügbar"):
                        adapter.parse_incoming(webhook_data)
    
    @patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token-123"})
    def test_audio_cleanup_on_success(self):
        """Test: Temp file wird nach Success gelöscht"""
        webhook_data = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "user": "U123456",
                "channel": "C789",
                "files": [{
                    "id": "F123",
                    "mimetype": "audio/m4a",
                    "url_private": "https://files.slack.com/file.m4a",
                    "size": 40000
                }]
            }
        }
        
        adapter = SlackAdapter()
        
        with patch.object(adapter, '_download_audio_file', return_value="/tmp/test_slack.m4a"):
            with patch.object(adapter, '_get_user_name', return_value="Max Test"):
                with patch('tools.transcription.get_transcriber') as mock_get_transcriber:
                    mock_transcriber = Mock()
                    mock_transcriber.is_enabled.return_value = True
                    mock_result = Mock()
                    mock_result.text = "Test"
                    mock_transcriber.transcribe.return_value = mock_result
                    mock_get_transcriber.return_value = mock_transcriber
                    
                    with patch('os.path.exists', return_value=True):
                        with patch('os.remove') as mock_remove:
                            msg = adapter.parse_incoming(webhook_data)
                            
                            # Check that cleanup was called
                            mock_remove.assert_called_once_with("/tmp/test_slack.m4a")
    
    @patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token-123"})
    def test_audio_cleanup_on_error(self):
        """Test: Temp file wird auch bei Error gelöscht (finally block)"""
        webhook_data = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "user": "U123456",
                "channel": "C789",
                "files": [{
                    "id": "F123",
                    "mimetype": "audio/wav",
                    "url_private": "https://files.slack.com/file.wav",
                    "size": 30000
                }]
            }
        }
        
        adapter = SlackAdapter()
        
        with patch.object(adapter, '_download_audio_file', return_value="/tmp/test_error.wav"):
            with patch.object(adapter, '_get_user_name', return_value="Max Test"):
                with patch('tools.transcription.get_transcriber') as mock_get_transcriber:
                    mock_transcriber = Mock()
                    mock_transcriber.is_enabled.return_value = True
                    mock_transcriber.transcribe.side_effect = Exception("Transcription failed")
                    mock_get_transcriber.return_value = mock_transcriber
                    
                    with patch('os.path.exists', return_value=True):
                        with patch('os.remove') as mock_remove:
                            with pytest.raises(WebhookParseError):
                                adapter.parse_incoming(webhook_data)
                            
                            # Cleanup should still happen
                            mock_remove.assert_called_once_with("/tmp/test_error.wav")
    
    @patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token-123"})
    @patch('tools.chat.slack_adapter.requests.get')
    def test_download_audio_file_success(self, mock_get):
        """Test: Audio file download from Slack"""
        adapter = SlackAdapter()
        
        # Mock download response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake_audio_data"
        mock_get.return_value = mock_response
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            file_url = "https://files.slack.com/files-pri/T123/test.mp3"
            file_path = adapter._download_audio_file(file_url, "audio/mp3")
            
            # Check file path format
            assert file_path.startswith("/tmp/slack_audio_")
            assert file_path.endswith(".mp3")
            
            # Check that file was written
            mock_file.write.assert_called_once_with(b"fake_audio_data")
            
            # Check that Authorization header was sent
            call_headers = mock_get.call_args[1]["headers"]
            assert "Authorization" in call_headers
            assert call_headers["Authorization"].startswith("Bearer ")
    
    @patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token-123"})
    @patch('tools.chat.slack_adapter.requests.get')
    def test_download_audio_file_error(self, mock_get):
        """Test: Error handling bei download failure"""
        adapter = SlackAdapter()
        
        # Mock download error
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_get.return_value = mock_response
        
        with pytest.raises(Exception, match="download failed"):
            adapter._download_audio_file("https://files.slack.com/file.mp3", "audio/mp3")
    
    @patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token-123"})
    def test_download_audio_mimetype_variants(self):
        """Test: Verschiedene MIME types werden korrekt gemapped"""
        adapter = SlackAdapter()
        
        with patch('tools.chat.slack_adapter.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"data"
            mock_get.return_value = mock_response
            
            with patch('builtins.open', create=True):
                # Test various mimetypes
                test_cases = [
                    ("audio/mp3", ".mp3"),
                    ("audio/mpeg", ".mp3"),
                    ("audio/wav", ".wav"),
                    ("audio/ogg", ".ogg"),
                    ("audio/m4a", ".m4a"),
                    ("audio/x-m4a", ".m4a"),
                ]
                
                for mimetype, expected_ext in test_cases:
                    path = adapter._download_audio_file("https://test.com/file", mimetype)
                    assert path.endswith(expected_ext), f"Failed for {mimetype}"


class TestSlackAudioEdgeCases:
    """Edge cases for audio file handling"""
    
    @patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token-123"})
    def test_files_array_but_not_audio(self):
        """Test: Files array vorhanden, aber kein Audio → fallback zu text"""
        webhook_data = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "user": "U123456",
                "channel": "C789",
                "text": "Check this image",
                "files": [{
                    "id": "F123",
                    "mimetype": "image/png",  # Not audio!
                    "url_private": "https://files.slack.com/image.png"
                }]
            }
        }
        
        adapter = SlackAdapter()
        
        with patch.object(adapter, '_get_user_name', return_value="Max Test"):
            msg = adapter.parse_incoming(webhook_data)
        
        # Should use text, not try to transcribe image
        assert msg.text == "Check this image"
    
    @patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token-123"})
    def test_audio_with_empty_transcript(self):
        """Test: Error wenn Transcript leer ist"""
        webhook_data = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "user": "U123456",
                "channel": "C789",
                "files": [{
                    "id": "F123",
                    "mimetype": "audio/wav",
                    "url_private": "https://files.slack.com/file.wav",
                    "size": 10000
                }]
            }
        }
        
        adapter = SlackAdapter()
        
        with patch.object(adapter, '_download_audio_file', return_value="/tmp/test.wav"):
            with patch.object(adapter, '_get_user_name', return_value="Max Test"):
                with patch('tools.transcription.get_transcriber') as mock_get_transcriber:
                    mock_transcriber = Mock()
                    mock_transcriber.is_enabled.return_value = True
                    mock_result = Mock()
                    mock_result.text = ""  # Empty!
                    mock_transcriber.transcribe.return_value = mock_result
                    mock_get_transcriber.return_value = mock_transcriber
                    
                    with patch('os.path.exists', return_value=True):
                        with patch('os.remove'):
                            with pytest.raises(WebhookParseError, match="audio file"):
                                adapter.parse_incoming(webhook_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

