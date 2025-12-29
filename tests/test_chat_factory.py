"""
Tests für Chat-Adapter Factory
"""

import pytest
from unittest.mock import patch
from tools.chat import (
    get_chat_adapter,
    get_default_adapter,
    list_supported_platforms,
    TelegramAdapter,
    SlackAdapter,
    ChatAdapter
)


# === Factory Tests ===

def test_get_chat_adapter_telegram():
    """Test: Factory gibt Telegram Adapter zurück"""
    
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}):
        adapter = get_chat_adapter("telegram")
    
    assert isinstance(adapter, TelegramAdapter)
    assert isinstance(adapter, ChatAdapter)
    assert adapter.get_platform_name() == "telegram"
    
    print("✅ Get Telegram Adapter")


def test_get_chat_adapter_slack():
    """Test: Factory gibt Slack Adapter zurück"""
    
    with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'xoxb-test'}):
        adapter = get_chat_adapter("slack")
    
    assert isinstance(adapter, SlackAdapter)
    assert isinstance(adapter, ChatAdapter)
    assert adapter.get_platform_name() == "slack"
    
    print("✅ Get Slack Adapter")


def test_get_chat_adapter_case_insensitive():
    """Test: Platform Name ist case-insensitive"""
    
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}):
        adapter1 = get_chat_adapter("TELEGRAM")
        adapter2 = get_chat_adapter("Telegram")
        adapter3 = get_chat_adapter("telegram")
    
    assert all(isinstance(a, TelegramAdapter) for a in [adapter1, adapter2, adapter3])
    
    print("✅ Case Insensitive")


def test_get_chat_adapter_unknown_platform():
    """Test: Unbekannte Plattform wirft ValueError"""
    
    with pytest.raises(ValueError, match="Unknown chat platform"):
        get_chat_adapter("whatsapp")
    
    print("✅ Unknown Platform Error")


# === Default Adapter Tests ===

def test_get_default_adapter_telegram():
    """Test: Default Adapter (CHAT_PLATFORM=telegram)"""
    
    with patch.dict('os.environ', {
        'CHAT_PLATFORM': 'telegram',
        'TELEGRAM_BOT_TOKEN': 'test_token'
    }):
        adapter = get_default_adapter()
    
    assert isinstance(adapter, TelegramAdapter)
    
    print("✅ Default Adapter (Telegram)")


def test_get_default_adapter_slack():
    """Test: Default Adapter (CHAT_PLATFORM=slack)"""
    
    with patch.dict('os.environ', {
        'CHAT_PLATFORM': 'slack',
        'SLACK_BOT_TOKEN': 'xoxb-test'
    }):
        adapter = get_default_adapter()
    
    assert isinstance(adapter, SlackAdapter)
    
    print("✅ Default Adapter (Slack)")


def test_get_default_adapter_fallback():
    """Test: Default Adapter ohne CHAT_PLATFORM (Fallback: telegram)"""
    
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}, clear=True):
        adapter = get_default_adapter()
    
    assert isinstance(adapter, TelegramAdapter)
    
    print("✅ Default Adapter Fallback")


# === List Platforms Tests ===

def test_list_supported_platforms():
    """Test: list_supported_platforms gibt korrekte Liste zurück"""
    
    platforms = list_supported_platforms()
    
    assert isinstance(platforms, list)
    assert "telegram" in platforms
    assert "slack" in platforms
    assert len(platforms) >= 2
    
    print("✅ List Supported Platforms")


# === Interface Compliance Tests ===

def test_adapter_interface_compliance_telegram():
    """Test: Telegram Adapter erfüllt ChatAdapter Interface"""
    
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}):
        adapter = get_chat_adapter("telegram")
    
    # Check required methods
    assert hasattr(adapter, 'parse_incoming')
    assert hasattr(adapter, 'send_message')
    assert hasattr(adapter, 'get_platform_name')
    assert hasattr(adapter, 'format_response')
    assert hasattr(adapter, 'validate_webhook')
    
    # Check they are callable
    assert callable(adapter.parse_incoming)
    assert callable(adapter.send_message)
    assert callable(adapter.get_platform_name)
    
    print("✅ Interface Compliance (Telegram)")


def test_adapter_interface_compliance_slack():
    """Test: Slack Adapter erfüllt ChatAdapter Interface"""
    
    with patch.dict('os.environ', {'SLACK_BOT_TOKEN': 'xoxb-test'}):
        adapter = get_chat_adapter("slack")
    
    # Check required methods
    assert hasattr(adapter, 'parse_incoming')
    assert hasattr(adapter, 'send_message')
    assert hasattr(adapter, 'get_platform_name')
    assert hasattr(adapter, 'format_response')
    assert hasattr(adapter, 'validate_webhook')
    
    print("✅ Interface Compliance (Slack)")


# === Run All Tests ===

if __name__ == "__main__":
    print("\n🧪 Running Chat Factory Tests...\n")
    
    test_get_chat_adapter_telegram()
    test_get_chat_adapter_slack()
    test_get_chat_adapter_case_insensitive()
    test_get_chat_adapter_unknown_platform()
    test_get_default_adapter_telegram()
    test_get_default_adapter_slack()
    test_get_default_adapter_fallback()
    test_list_supported_platforms()
    test_adapter_interface_compliance_telegram()
    test_adapter_interface_compliance_slack()
    
    print("\n📊 Ergebnis: 10/10 Tests bestanden ✅")
    print("✅ Chat Factory validiert\n")

