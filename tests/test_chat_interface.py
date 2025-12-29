"""
Tests für Chat-Adapter Interface & StandardMessage
"""

import pytest
from tools.chat.interface import (
    StandardMessage,
    ChatAdapter,
    ChatAdapterError,
    WebhookParseError,
    MessageSendError
)


# === StandardMessage Tests ===

def test_standard_message_creation():
    """Test: StandardMessage kann erstellt werden"""
    msg = StandardMessage(
        user_id="telegram:123456",
        user_name="Test User",
        text="Hello Adizon",
        platform="telegram",
        chat_id="123456",
        raw_data={"message": {"text": "Hello"}}
    )
    
    assert msg.user_id == "telegram:123456"
    assert msg.user_name == "Test User"
    assert msg.text == "Hello Adizon"
    assert msg.platform == "telegram"
    assert msg.chat_id == "123456"
    assert "message" in msg.raw_data
    
    print("✅ StandardMessage Creation")


def test_standard_message_repr():
    """Test: StandardMessage __repr__ ist lesbar"""
    msg = StandardMessage(
        user_id="slack:U123",
        user_name="Max Mustermann",
        text="This is a very long message that should be truncated in repr",
        platform="slack",
        chat_id="C123",
        raw_data={}
    )
    
    repr_str = repr(msg)
    assert "slack" in repr_str
    assert "Max Mustermann" in repr_str
    assert "..." in repr_str  # Truncated
    
    print("✅ StandardMessage Repr")


# === ChatAdapter Interface Tests ===

class MockChatAdapter(ChatAdapter):
    """Mock-Implementierung für Tests"""
    
    def parse_incoming(self, webhook_data: dict) -> StandardMessage:
        return StandardMessage(
            user_id="mock:1",
            user_name="Mock User",
            text=webhook_data.get("text", ""),
            platform="mock",
            chat_id="mock_chat",
            raw_data=webhook_data
        )
    
    def send_message(self, chat_id: str, text: str) -> bool:
        return True
    
    def get_platform_name(self) -> str:
        return "mock"


def test_chat_adapter_interface():
    """Test: ChatAdapter Interface kann implementiert werden"""
    adapter = MockChatAdapter()
    
    # parse_incoming
    msg = adapter.parse_incoming({"text": "Test"})
    assert isinstance(msg, StandardMessage)
    assert msg.text == "Test"
    
    # send_message
    success = adapter.send_message("123", "Hello")
    assert success is True
    
    # get_platform_name
    platform = adapter.get_platform_name()
    assert platform == "mock"
    
    print("✅ ChatAdapter Interface")


def test_chat_adapter_format_response():
    """Test: format_response Default-Implementierung"""
    adapter = MockChatAdapter()
    
    text = "Hello World"
    formatted = adapter.format_response(text)
    
    assert formatted == text  # Default gibt unverändert zurück
    
    print("✅ ChatAdapter format_response")


def test_chat_adapter_validate_webhook():
    """Test: validate_webhook Default-Implementierung"""
    adapter = MockChatAdapter()
    
    is_valid = adapter.validate_webhook({"data": "test"})
    
    assert is_valid is True  # Default gibt immer True zurück
    
    print("✅ ChatAdapter validate_webhook")


# === Exception Tests ===

def test_chat_adapter_error():
    """Test: ChatAdapterError kann geworfen werden"""
    with pytest.raises(ChatAdapterError):
        raise ChatAdapterError("Test error")
    
    print("✅ ChatAdapterError")


def test_webhook_parse_error():
    """Test: WebhookParseError ist ChatAdapterError"""
    with pytest.raises(ChatAdapterError):
        raise WebhookParseError("Parse failed")
    
    with pytest.raises(WebhookParseError):
        raise WebhookParseError("Parse failed")
    
    print("✅ WebhookParseError")


def test_message_send_error():
    """Test: MessageSendError ist ChatAdapterError"""
    with pytest.raises(ChatAdapterError):
        raise MessageSendError("Send failed")
    
    with pytest.raises(MessageSendError):
        raise MessageSendError("Send failed")
    
    print("✅ MessageSendError")


# === Run All Tests ===

if __name__ == "__main__":
    print("\n🧪 Running Chat Interface Tests...\n")
    
    test_standard_message_creation()
    test_standard_message_repr()
    test_chat_adapter_interface()
    test_chat_adapter_format_response()
    test_chat_adapter_validate_webhook()
    test_chat_adapter_error()
    test_webhook_parse_error()
    test_message_send_error()
    
    print("\n📊 Ergebnis: 8/8 Tests bestanden ✅")
    print("✅ Chat Interface validiert\n")

