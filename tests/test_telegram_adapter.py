"""
Tests für Telegram Chat Adapter
"""

import pytest
from unittest.mock import patch, MagicMock
from tools.chat.telegram_adapter import TelegramAdapter
from tools.chat.interface import StandardMessage, WebhookParseError


# === Parse Incoming Tests ===

def test_parse_telegram_webhook():
    """Test: Telegram Webhook wird korrekt geparst"""
    
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}):
        adapter = TelegramAdapter()
    
    webhook_data = {
        "message": {
            "chat": {"id": 123456},
            "from": {
                "id": 789012,
                "first_name": "Max",
                "last_name": "Mustermann"
            },
            "text": "Hallo Adizon"
        }
    }
    
    msg = adapter.parse_incoming(webhook_data)
    
    assert isinstance(msg, StandardMessage)
    assert msg.user_id == "telegram:789012"
    assert msg.user_name == "Max Mustermann"
    assert msg.text == "Hallo Adizon"
    assert msg.platform == "telegram"
    assert msg.chat_id == "123456"
    assert msg.raw_data == webhook_data
    
    print("✅ Parse Telegram Webhook")


def test_parse_telegram_webhook_without_last_name():
    """Test: Telegram Webhook ohne Last Name"""
    
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}):
        adapter = TelegramAdapter()
    
    webhook_data = {
        "message": {
            "chat": {"id": 123456},
            "from": {
                "id": 789012,
                "first_name": "Max"
            },
            "text": "Hallo"
        }
    }
    
    msg = adapter.parse_incoming(webhook_data)
    
    assert msg.user_name == "Max"  # Kein trailing space
    
    print("✅ Parse Telegram Webhook (no last name)")


def test_parse_telegram_webhook_missing_message():
    """Test: Telegram Webhook ohne 'message' wirft Fehler"""
    
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}):
        adapter = TelegramAdapter()
    
    webhook_data = {"update_id": 123}
    
    with pytest.raises(WebhookParseError, match="No 'message' field"):
        adapter.parse_incoming(webhook_data)
    
    print("✅ Parse Error (missing message)")


def test_parse_telegram_webhook_missing_user_id():
    """Test: Telegram Webhook ohne User-ID wirft Fehler"""
    
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}):
        adapter = TelegramAdapter()
    
    webhook_data = {
        "message": {
            "chat": {"id": 123456},
            "from": {"first_name": "Max"},
            "text": "Hello"
        }
    }
    
    with pytest.raises(WebhookParseError, match="Missing 'from.id'"):
        adapter.parse_incoming(webhook_data)
    
    print("✅ Parse Error (missing user ID)")


# === Send Message Tests ===

@patch('tools.chat.telegram_adapter.requests.post')
def test_send_telegram_message(mock_post):
    """Test: Telegram Message wird gesendet"""
    
    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response
    
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}):
        adapter = TelegramAdapter()
    
    success = adapter.send_message("123456", "Hello World")
    
    assert success is True
    mock_post.assert_called_once()
    
    # Check API URL
    call_args = mock_post.call_args
    assert "sendMessage" in call_args[1]['url'] or "sendMessage" in call_args[0][0]
    
    print("✅ Send Telegram Message")


@patch('tools.chat.telegram_adapter.requests.post')
def test_send_telegram_message_error(mock_post):
    """Test: Telegram API Error"""
    
    # Mock error response
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    mock_post.return_value = mock_response
    
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}):
        adapter = TelegramAdapter()
    
    success = adapter.send_message("123456", "Hello")
    
    assert success is False
    
    print("✅ Send Error (API Error)")


# === Platform Name Test ===

def test_get_platform_name():
    """Test: get_platform_name gibt 'telegram' zurück"""
    
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}):
        adapter = TelegramAdapter()
    
    assert adapter.get_platform_name() == "telegram"
    
    print("✅ Get Platform Name")


# === Initialization Tests ===

def test_telegram_adapter_init_without_token():
    """Test: TelegramAdapter ohne Token wirft Fehler"""
    
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN not set"):
            TelegramAdapter()
    
    print("✅ Init Error (no token)")


# === Update ID Tests (for Deduplication) ===

def test_parse_telegram_webhook_with_update_id():
    """Test: update_id wird aus Webhook extrahiert (für Deduplication)"""
    
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}):
        adapter = TelegramAdapter()
    
    webhook_data = {
        "update_id": 861843155,
        "message": {
            "chat": {"id": 123456},
            "from": {
                "id": 789012,
                "first_name": "Max"
            },
            "text": "Test"
        }
    }
    
    msg = adapter.parse_incoming(webhook_data)
    
    # update_id sollte im raw_data enthalten sein
    assert msg.raw_data["update_id"] == 861843155
    
    print("✅ Parse with update_id")


# === Run All Tests ===

if __name__ == "__main__":
    print("\n🧪 Running Telegram Adapter Tests...\n")
    
    test_parse_telegram_webhook()
    test_parse_telegram_webhook_without_last_name()
    test_parse_telegram_webhook_missing_message()
    test_parse_telegram_webhook_missing_user_id()
    test_send_telegram_message()
    test_send_telegram_message_error()
    test_get_platform_name()
    test_telegram_adapter_init_without_token()
    test_parse_telegram_webhook_with_update_id()
    
    print("\n📊 Ergebnis: 9/9 Tests bestanden ✅")
    print("✅ Telegram Adapter validiert\n")

