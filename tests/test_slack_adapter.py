"""
Tests für Slack Chat Adapter
"""

import pytest
from unittest.mock import patch, MagicMock
from tools.chat.slack_adapter import SlackAdapter, handle_slack_challenge
from tools.chat.interface import StandardMessage, WebhookParseError


# === Parse Incoming Tests ===

@patch('tools.chat.slack_adapter.SlackAdapter._get_user_name')
def test_parse_slack_webhook(mock_get_user_name):
    """Test: Slack Webhook wird korrekt geparst"""
    
    mock_get_user_name.return_value = "Max Mustermann"
    
    with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'xoxb-test'}):
        adapter = SlackAdapter()
    
    webhook_data = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "user": "U123456",
            "text": "Hallo Adizon",
            "channel": "C123456"
        }
    }
    
    msg = adapter.parse_incoming(webhook_data)
    
    assert isinstance(msg, StandardMessage)
    assert msg.user_id == "slack:U123456"
    assert msg.user_name == "Max Mustermann"
    assert msg.text == "Hallo Adizon"
    assert msg.platform == "slack"
    assert msg.chat_id == "C123456"
    assert msg.raw_data == webhook_data
    
    print("✅ Parse Slack Webhook")


def test_parse_slack_challenge():
    """Test: Slack Challenge (Webhook Verification) wird erkannt"""
    
    with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'xoxb-test'}):
        adapter = SlackAdapter()
    
    webhook_data = {
        "type": "url_verification",
        "challenge": "3eZbrw1aBm2rZgRNFdxV2595E9CY3gmdALWMmHkvFXO7tYXAYM8P"
    }
    
    with pytest.raises(WebhookParseError, match="CHALLENGE:"):
        adapter.parse_incoming(webhook_data)
    
    print("✅ Parse Slack Challenge")


def test_parse_slack_webhook_bot_message():
    """Test: Bot Messages werden ignoriert (Loop Prevention)"""
    
    with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'xoxb-test'}):
        adapter = SlackAdapter()
    
    webhook_data = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "bot_id": "B123456",
            "text": "Hello",
            "channel": "C123456"
        }
    }
    
    with pytest.raises(WebhookParseError, match="Ignoring bot message"):
        adapter.parse_incoming(webhook_data)
    
    print("✅ Ignore Bot Messages")


def test_parse_slack_webhook_missing_user():
    """Test: Slack Webhook ohne User wirft Fehler"""
    
    with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'xoxb-test'}):
        adapter = SlackAdapter()
    
    webhook_data = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "text": "Hello",
            "channel": "C123456"
        }
    }
    
    with pytest.raises(WebhookParseError, match="Missing 'event.user'"):
        adapter.parse_incoming(webhook_data)
    
    print("✅ Parse Error (missing user)")


def test_parse_slack_webhook_message_changed():
    """Test: message_changed Subtype wird ignoriert"""
    
    with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'xoxb-test'}):
        adapter = SlackAdapter()
    
    webhook_data = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "subtype": "message_changed",
            "message": {
                "text": "Edited message",
                "user": "U123456"
            },
            "channel": "C123456"
        }
    }
    
    with pytest.raises(WebhookParseError, match="Ignoring Slack subtype: message_changed"):
        adapter.parse_incoming(webhook_data)
    
    print("✅ Ignore message_changed Subtype")


def test_parse_slack_webhook_bot_profile():
    """Test: Bot Messages mit bot_profile werden ignoriert"""
    
    with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'xoxb-test'}):
        adapter = SlackAdapter()
    
    webhook_data = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "bot_profile": {
                "id": "B123456",
                "name": "Test Bot"
            },
            "text": "Bot message",
            "channel": "C123456"
        }
    }
    
    with pytest.raises(WebhookParseError, match="Ignoring bot message"):
        adapter.parse_incoming(webhook_data)
    
    print("✅ Ignore bot_profile Messages")


# === Send Message Tests ===

@patch('tools.chat.slack_adapter.requests.post')
def test_send_slack_message(mock_post):
    """Test: Slack Message wird gesendet"""
    
    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": True}
    mock_post.return_value = mock_response
    
    with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'xoxb-test'}):
        adapter = SlackAdapter()
    
    success = adapter.send_message("C123456", "Hello World")
    
    assert success is True
    mock_post.assert_called_once()
    
    print("✅ Send Slack Message")


@patch('tools.chat.slack_adapter.requests.post')
def test_send_slack_message_api_error(mock_post):
    """Test: Slack API Error (ok: false)"""
    
    # Mock error response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": False, "error": "channel_not_found"}
    mock_post.return_value = mock_response
    
    with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'xoxb-test'}):
        adapter = SlackAdapter()
    
    success = adapter.send_message("C123456", "Hello")
    
    assert success is False
    
    print("✅ Send Error (API Error)")


# === Helper Tests ===

def test_handle_slack_challenge():
    """Test: handle_slack_challenge extrahiert Challenge"""
    
    webhook_data = {
        "type": "url_verification",
        "challenge": "test_challenge_123"
    }
    
    challenge = handle_slack_challenge(webhook_data)
    
    assert challenge == "test_challenge_123"
    
    print("✅ Handle Slack Challenge")


def test_handle_slack_challenge_no_challenge():
    """Test: handle_slack_challenge gibt None bei normalem Event"""
    
    webhook_data = {
        "type": "event_callback",
        "event": {"type": "message"}
    }
    
    challenge = handle_slack_challenge(webhook_data)
    
    assert challenge is None
    
    print("✅ Handle Non-Challenge Event")


# === Platform Name Test ===

def test_get_platform_name():
    """Test: get_platform_name gibt 'slack' zurück"""
    
    with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'xoxb-test'}):
        adapter = SlackAdapter()
    
    assert adapter.get_platform_name() == "slack"
    
    print("✅ Get Platform Name")


# === Initialization Tests ===

def test_slack_adapter_init_without_token():
    """Test: SlackAdapter ohne Token wirft Fehler"""
    
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError, match="SLACK_BOT_TOKEN not set"):
            SlackAdapter()
    
    print("✅ Init Error (no token)")


# === Run All Tests ===

if __name__ == "__main__":
    print("\n🧪 Running Slack Adapter Tests...\n")
    
    test_parse_slack_webhook()
    test_parse_slack_challenge()
    test_parse_slack_webhook_bot_message()
    test_parse_slack_webhook_missing_user()
    test_parse_slack_webhook_message_changed()
    test_parse_slack_webhook_bot_profile()
    test_send_slack_message()
    test_send_slack_message_api_error()
    test_handle_slack_challenge()
    test_handle_slack_challenge_no_challenge()
    test_get_platform_name()
    test_slack_adapter_init_without_token()
    
    print("\n📊 Ergebnis: 12/12 Tests bestanden ✅")
    print("✅ Slack Adapter validiert\n")

