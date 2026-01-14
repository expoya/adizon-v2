"""
Chat-Adapter Interface
Abstract Base Class für alle Chat-Plattformen (Telegram, Slack, Teams, etc.)

Fully async interface for non-blocking HTTP operations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class StandardMessage:
    """
    Plattform-agnostisches Message-Format.
    Wird von allen Chat-Adaptern verwendet.
    """
    user_id: str          # Platform-prefixed: "telegram:123456", "slack:U123456"
    user_name: str        # Display Name: "Max Mustermann"
    text: str             # Message content
    platform: str         # Platform identifier: "telegram", "slack", "teams"
    chat_id: str          # Platform-specific chat/channel ID (for sending replies)
    raw_data: Dict[str, Any]  # Original webhook data (for debugging)
    
    def __repr__(self):
        return f"StandardMessage(platform={self.platform}, user={self.user_name}, text='{self.text[:50]}...')"


class ChatAdapter(ABC):
    """
    Abstract Base Class für Chat-Adapter (async).
    
    Jede Chat-Plattform (Telegram, Slack, Teams, etc.) implementiert diese Interface.
    All methods are async to prevent blocking the FastAPI event loop.
    
    Beispiel:
        class TelegramAdapter(ChatAdapter):
            async def parse_incoming(self, webhook_data: dict) -> StandardMessage:
                # Parse Telegram-specific webhook
                ...
            
            async def send_message(self, chat_id: str, text: str) -> bool:
                # Send via Telegram Bot API
                ...
    """
    
    @abstractmethod
    async def parse_incoming(self, webhook_data: dict) -> StandardMessage:
        """
        Parst eingehende Webhook-Daten zu StandardMessage (async).
        
        Args:
            webhook_data: Platform-spezifisches Webhook-Format
            
        Returns:
            StandardMessage mit normalisierten Daten
            
        Raises:
            ValueError: Wenn Webhook-Format ungültig ist
        """
        pass
    
    @abstractmethod
    async def send_message(self, chat_id: str, text: str) -> bool:
        """
        Sendet Nachricht über die Plattform (async).
        
        Args:
            chat_id: Platform-specific Chat/Channel ID
            text: Message text to send
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """
        Gibt den Namen der Plattform zurück.
        
        Returns:
            Platform name (lowercase): "telegram", "slack", "teams"
        """
        pass
    
    def format_response(self, text: str) -> str:
        """
        Optional: Formatiert Response für Plattform.
        Default: Gibt Text unverändert zurück.
        
        Kann überschrieben werden für plattform-spezifische Formatierung
        (z.B. Markdown für Slack, HTML für Telegram).
        
        Args:
            text: Raw response text
            
        Returns:
            Formatted text for platform
        """
        return text
    
    def validate_webhook(self, webhook_data: dict) -> bool:
        """
        Optional: Validiert Webhook-Signatur/Authenticity.
        Default: Returns True (keine Validation).
        
        Kann überschrieben werden für Security-Checks
        (z.B. Slack Signing Secret, Telegram Secret Token).
        
        Args:
            webhook_data: Webhook data to validate
            
        Returns:
            True if valid, False otherwise
        """
        return True


class ChatAdapterError(Exception):
    """Base Exception für Chat-Adapter Fehler"""
    pass


class WebhookParseError(ChatAdapterError):
    """Webhook konnte nicht geparst werden"""
    pass


class MessageSendError(ChatAdapterError):
    """Nachricht konnte nicht gesendet werden"""
    pass
