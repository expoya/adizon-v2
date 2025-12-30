"""
Tests for Telegram Voice Message Support

Tests voice message handling in Telegram adapter.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from tools.chat.telegram_adapter import TelegramAdapter
from tools.chat.interface import StandardMessage, WebhookParseError


class TestTelegramVoiceSupport:
    """Test suite for Telegram voice message support"""
    
    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token-123"})
    def test_parse_voice_message_success(self):
        """Test: Voice message wird korrekt erkannt und transkribiert"""
        webhook_data = {
            "message": {
                "from": {"id": 123456, "first_name": "Max", "last_name": "Test"},
                "chat": {"id": 789},
                "voice": {
                    "file_id": "AwACAgQAAxkBAAI...",
                    "duration": 5,
                    "mime_type": "audio/ogg"
                }
            }
        }
        
        adapter = TelegramAdapter()
        
        # Mock download and transcription
        with patch.object(adapter, '_download_voice_file', return_value="/tmp/test.ogg"):
            with patch('tools.transcription.get_transcriber') as mock_get_transcriber:
                mock_transcriber = Mock()
                mock_transcriber.is_enabled.return_value = True
                mock_result = Mock()
                mock_result.text = "Das ist ein Test"
                mock_transcriber.transcribe.return_value = mock_result
                mock_get_transcriber.return_value = mock_transcriber
                
                with patch('os.path.exists', return_value=True):
                    with patch('os.remove'):
                        msg = adapter.parse_incoming(webhook_data)
        
        assert msg.text == "Das ist ein Test"
        assert msg.user_id == "telegram:123456"
        assert msg.platform == "telegram"
    
    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token-123"})
    def test_parse_text_message_still_works(self):
        """Test: Normale Text-Messages funktionieren weiterhin"""
        webhook_data = {
            "message": {
                "from": {"id": 123456, "first_name": "Max"},
                "chat": {"id": 789},
                "text": "Normal text message"
            }
        }
        
        adapter = TelegramAdapter()
        msg = adapter.parse_incoming(webhook_data)
        
        assert msg.text == "Normal text message"
        assert msg.user_id == "telegram:123456"
    
    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token-123"})
    def test_parse_voice_missing_file_id(self):
        """Test: Error wenn voice ohne file_id"""
        webhook_data = {
            "message": {
                "from": {"id": 123456, "first_name": "Max"},
                "chat": {"id": 789},
                "voice": {"duration": 5}  # file_id fehlt!
            }
        }
        
        adapter = TelegramAdapter()
        
        with pytest.raises(WebhookParseError, match="Missing 'file_id'"):
            adapter.parse_incoming(webhook_data)
    
    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token-123"})
    def test_parse_voice_transcriber_disabled(self):
        """Test: Error Message wenn Whisper nicht verfügbar"""
        webhook_data = {
            "message": {
                "from": {"id": 123456, "first_name": "Max"},
                "chat": {"id": 789},
                "voice": {"file_id": "ABC123", "duration": 5}
            }
        }
        
        adapter = TelegramAdapter()
        
        with patch.object(adapter, '_download_voice_file', return_value="/tmp/test.ogg"):
            with patch('tools.transcription.get_transcriber') as mock_get_transcriber:
                mock_transcriber = Mock()
                mock_transcriber.is_enabled.return_value = False  # Disabled!
                mock_get_transcriber.return_value = mock_transcriber
                
                with pytest.raises(WebhookParseError, match="nicht verfügbar"):
                    adapter.parse_incoming(webhook_data)
    
    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token-123"})
    def test_voice_cleanup_on_success(self):
        """Test: Temp file wird nach Success gelöscht"""
        webhook_data = {
            "message": {
                "from": {"id": 123456, "first_name": "Max"},
                "chat": {"id": 789},
                "voice": {"file_id": "ABC123", "duration": 5}
            }
        }
        
        adapter = TelegramAdapter()
        
        with patch.object(adapter, '_download_voice_file', return_value="/tmp/test_voice.ogg"):
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
                        mock_remove.assert_called_once_with("/tmp/test_voice.ogg")
    
    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token-123"})
    def test_voice_cleanup_on_error(self):
        """Test: Temp file wird auch bei Error gelöscht (finally block)"""
        webhook_data = {
            "message": {
                "from": {"id": 123456, "first_name": "Max"},
                "chat": {"id": 789},
                "voice": {"file_id": "ABC123", "duration": 5}
            }
        }
        
        adapter = TelegramAdapter()
        
        with patch.object(adapter, '_download_voice_file', return_value="/tmp/test_error.ogg"):
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
                        mock_remove.assert_called_once_with("/tmp/test_error.ogg")
    
    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token-123"})
    @patch('tools.chat.telegram_adapter.requests.get')
    def test_download_voice_file_success(self, mock_get):
        """Test: Voice file download from Telegram"""
        adapter = TelegramAdapter()
        
        # Mock getFile response
        get_file_response = Mock()
        get_file_response.status_code = 200
        get_file_response.json.return_value = {
            "ok": True,
            "result": {"file_path": "voice/file_123.oga"}
        }
        
        # Mock download response
        download_response = Mock()
        download_response.status_code = 200
        download_response.content = b"fake_audio_data"
        
        mock_get.side_effect = [get_file_response, download_response]
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            file_path = adapter._download_voice_file("test_file_id_123")
            
            # Check file path format
            assert file_path.startswith("/tmp/telegram_")
            assert file_path.endswith(".oga")
            
            # Check that file was written
            mock_file.write.assert_called_once_with(b"fake_audio_data")
    
    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token-123"})
    @patch('tools.chat.telegram_adapter.requests.get')
    def test_download_voice_file_getfile_error(self, mock_get):
        """Test: Error handling bei getFile failure"""
        adapter = TelegramAdapter()
        
        # Mock getFile error
        get_file_response = Mock()
        get_file_response.status_code = 400
        get_file_response.text = "Bad Request"
        mock_get.return_value = get_file_response
        
        with pytest.raises(Exception, match="getFile failed"):
            adapter._download_voice_file("invalid_file_id")


class TestTelegramVoiceEdgeCases:
    """Edge cases for voice message handling"""
    
    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token-123"})
    def test_neither_text_nor_voice(self):
        """Test: Error wenn weder text noch voice"""
        webhook_data = {
            "message": {
                "from": {"id": 123456, "first_name": "Max"},
                "chat": {"id": 789}
                # Kein text, kein voice!
            }
        }
        
        adapter = TelegramAdapter()
        
        with pytest.raises(WebhookParseError, match="neither 'text' nor 'voice'"):
            adapter.parse_incoming(webhook_data)
    
    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token-123"})
    def test_voice_with_empty_transcript(self):
        """Test: Error wenn Transcript leer ist"""
        webhook_data = {
            "message": {
                "from": {"id": 123456, "first_name": "Max"},
                "chat": {"id": 789},
                "voice": {"file_id": "ABC123", "duration": 5}
            }
        }
        
        adapter = TelegramAdapter()
        
        with patch.object(adapter, '_download_voice_file', return_value="/tmp/test.ogg"):
            with patch('tools.transcription.get_transcriber') as mock_get_transcriber:
                mock_transcriber = Mock()
                mock_transcriber.is_enabled.return_value = True
                mock_result = Mock()
                mock_result.text = ""  # Empty!
                mock_transcriber.transcribe.return_value = mock_result
                mock_get_transcriber.return_value = mock_transcriber
                
                with patch('os.path.exists', return_value=True):
                    with patch('os.remove'):
                        with pytest.raises(WebhookParseError, match="Empty message text"):
                            adapter.parse_incoming(webhook_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

