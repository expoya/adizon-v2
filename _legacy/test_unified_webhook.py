"""
Tests für Unified Webhook und Deduplication
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestUnifiedWebhookDeduplication:
    """Tests für Webhook Deduplication (Telegram und Slack)"""
    
    @patch('main.redis_client')
    @patch('main.get_chat_adapter')
    @patch('main.handle_message')
    def test_telegram_deduplication_first_message(self, mock_handle, mock_get_adapter, mock_redis):
        """Test: Erste Telegram Message wird verarbeitet"""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        
        # Setup Mocks
        mock_redis.exists.return_value = False  # Nicht im Cache
        mock_redis.setex = Mock()
        
        adapter_mock = Mock()
        adapter_mock.parse_incoming = Mock(return_value=Mock(
            chat_id="123",
            spec=['chat_id', 'user_id', 'user_name', 'text', 'platform', 'raw_data']
        ))
        adapter_mock.send_message = Mock(return_value=True)
        mock_get_adapter.return_value = adapter_mock
        
        mock_handle.return_value = "Response text"
        
        # Send Webhook
        response = client.post("/webhook/telegram", json={
            "update_id": 123456,
            "message": {
                "chat": {"id": 123},
                "from": {"id": 789, "first_name": "Test"},
                "text": "Hello"
            }
        })
        
        # Assertions
        assert response.status_code == 200
        mock_redis.exists.assert_called_once_with("telegram:update:123456")
        mock_redis.setex.assert_called_once_with("telegram:update:123456", 600, "1")
        mock_handle.assert_called_once()
        
        print("✅ Telegram First Message (not cached)")
    
    @patch('main.redis_client')
    @patch('main.get_chat_adapter')
    def test_telegram_deduplication_duplicate_message(self, mock_get_adapter, mock_redis):
        """Test: Doppelte Telegram Message wird ignoriert"""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        
        # Setup Mocks
        mock_redis.exists.return_value = True  # Bereits im Cache!
        
        # Send Webhook
        response = client.post("/webhook/telegram", json={
            "update_id": 123456,
            "message": {
                "chat": {"id": 123},
                "from": {"id": 789, "first_name": "Test"},
                "text": "Hello"
            }
        })
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "duplicate_update"
        
        # get_chat_adapter sollte NICHT aufgerufen worden sein
        mock_get_adapter.assert_not_called()
        
        print("✅ Telegram Duplicate Message (cached)")
    
    @patch('main.redis_client')
    @patch('main.get_chat_adapter')
    @patch('main.handle_message')
    def test_slack_deduplication_first_event(self, mock_handle, mock_get_adapter, mock_redis):
        """Test: Erstes Slack Event wird verarbeitet"""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        
        # Setup Mocks
        mock_redis.exists.return_value = False
        mock_redis.setex = Mock()
        
        adapter_mock = Mock()
        adapter_mock.parse_incoming = Mock(return_value=Mock(
            chat_id="C123",
            spec=['chat_id', 'user_id', 'user_name', 'text', 'platform', 'raw_data']
        ))
        adapter_mock.send_message = Mock(return_value=True)
        mock_get_adapter.return_value = adapter_mock
        
        mock_handle.return_value = "Response text"
        
        # Send Webhook
        response = client.post("/webhook/slack", json={
            "type": "event_callback",
            "event_id": "Ev123ABC",
            "event": {
                "type": "message",
                "user": "U123",
                "text": "Hello",
                "channel": "C123"
            }
        })
        
        # Assertions
        assert response.status_code == 200
        mock_redis.exists.assert_called_once_with("slack:event:Ev123ABC")
        mock_redis.setex.assert_called_once_with("slack:event:Ev123ABC", 600, "1")
        mock_handle.assert_called_once()
        
        print("✅ Slack First Event (not cached)")
    
    @patch('main.redis_client')
    @patch('main.get_chat_adapter')
    def test_slack_deduplication_duplicate_event(self, mock_get_adapter, mock_redis):
        """Test: Doppeltes Slack Event wird ignoriert"""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        
        # Setup Mocks
        mock_redis.exists.return_value = True  # Bereits im Cache!
        
        # Send Webhook
        response = client.post("/webhook/slack", json={
            "type": "event_callback",
            "event_id": "Ev123ABC",
            "event": {
                "type": "message",
                "user": "U123",
                "text": "Hello",
                "channel": "C123"
            }
        })
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "duplicate_event"
        
        # get_chat_adapter sollte NICHT aufgerufen worden sein
        mock_get_adapter.assert_not_called()
        
        print("✅ Slack Duplicate Event (cached)")


class TestUnifiedWebhookRouting:
    """Tests für Platform Routing"""
    
    @patch('main.get_chat_adapter')
    def test_unknown_platform(self, mock_get_adapter):
        """Test: Unbekannte Plattform gibt 400 zurück"""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        
        mock_get_adapter.side_effect = ValueError("Unknown platform")
        
        response = client.post("/webhook/whatsapp", json={"test": "data"})
        
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
        
        print("✅ Unknown Platform Error")
    
    @patch('main.redis_client')
    @patch('main.get_chat_adapter')
    def test_webhook_parse_error_returns_200(self, mock_get_adapter, mock_redis):
        """Test: WebhookParseError gibt 200 zurück (nicht 400)"""
        from fastapi.testclient import TestClient
        from main import app
        from tools.chat.interface import WebhookParseError
        
        client = TestClient(app)
        
        # Setup Mocks
        mock_redis.exists.return_value = False
        mock_redis.setex = Mock()
        
        adapter_mock = Mock()
        adapter_mock.parse_incoming = Mock(side_effect=WebhookParseError("Bot message"))
        mock_get_adapter.return_value = adapter_mock
        
        response = client.post("/webhook/slack", json={
            "type": "event_callback",
            "event_id": "Ev123",
            "event": {"type": "message", "bot_id": "B123"}
        })
        
        # Sollte 200 zurückgeben (nicht 400!)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        
        print("✅ WebhookParseError returns 200 OK")


class TestSlackChallengeHandling:
    """Tests für Slack Challenge"""
    
    @patch('main.handle_slack_challenge')
    def test_slack_challenge_response(self, mock_challenge):
        """Test: Slack Challenge wird korrekt beantwortet"""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        
        mock_challenge.return_value = "3eZbrw1aBm2rZgRNFdxV2595E9CY3gmdALWMmHkvFXO7tYXAYM8P"
        
        response = client.post("/webhook/slack", json={
            "type": "url_verification",
            "challenge": "3eZbrw1aBm2rZgRNFdxV2595E9CY3gmdALWMmHkvFXO7tYXAYM8P"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["challenge"] == "3eZbrw1aBm2rZgRNFdxV2595E9CY3gmdALWMmHkvFXO7tYXAYM8P"
        
        print("✅ Slack Challenge Response")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

