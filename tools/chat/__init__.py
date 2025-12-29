"""
Chat-Adapter Factory
Stellt Chat-Adapter für verschiedene Plattformen bereit (Telegram, Slack, Teams, etc.)
"""

import os
from typing import Optional
from .interface import ChatAdapter, StandardMessage
from .telegram_adapter import TelegramAdapter
from .slack_adapter import SlackAdapter


# === STARTUP INFO ===
# Print Chat-Platform Config beim Import (wie CRM)
_telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
_slack_token = os.getenv("SLACK_BOT_TOKEN", "").strip()
_default_platform = os.getenv("CHAT_PLATFORM", "telegram").strip().lower()

_configured_platforms = []
if _telegram_token:
    _configured_platforms.append("Telegram")
if _slack_token:
    _configured_platforms.append("Slack")

if _configured_platforms:
    platforms_str = ", ".join(_configured_platforms)
    print(f"💬 Chat-Adapter configured: {platforms_str}")
    print(f"📱 Default Platform: {_default_platform.upper()}")
else:
    print("⚠️ No Chat-Platform tokens configured (set TELEGRAM_BOT_TOKEN or SLACK_BOT_TOKEN)")


# === FACTORY ===

def get_chat_adapter(platform: str) -> ChatAdapter:
    """
    Returns Chat-Adapter für spezifische Plattform.
    
    Args:
        platform: Platform identifier (lowercase): "telegram", "slack", "teams"
        
    Returns:
        ChatAdapter Instanz für die Plattform
        
    Raises:
        ValueError: Wenn Platform unbekannt ist
        
    Example:
        adapter = get_chat_adapter("telegram")
        msg = adapter.parse_incoming(webhook_data)
        adapter.send_message(msg.chat_id, "Hello!")
    """
    platform = platform.lower().strip()
    
    if platform == "telegram":
        return TelegramAdapter()
    elif platform == "slack":
        return SlackAdapter()
    # Future Adapters:
    # elif platform == "teams":
    #     return TeamsAdapter()
    # elif platform == "whatsapp":
    #     return WhatsAppAdapter()
    else:
        raise ValueError(
            f"Unknown chat platform: '{platform}'. "
            f"Supported: telegram, slack"
        )


def get_default_adapter() -> ChatAdapter:
    """
    Returns Chat-Adapter basierend auf Environment Variable.
    
    Env Variable:
        CHAT_PLATFORM: "telegram", "slack", "teams" (default: "telegram")
        
    Returns:
        ChatAdapter für die konfigurierte Plattform
    """
    platform = os.getenv("CHAT_PLATFORM", "telegram").strip()
    return get_chat_adapter(platform)


def list_supported_platforms() -> list[str]:
    """
    Gibt Liste aller unterstützten Plattformen zurück.
    
    Returns:
        List of platform names (lowercase)
    """
    return ["telegram", "slack"]


# === EXPORTS ===

__all__ = [
    # Interface
    "ChatAdapter",
    "StandardMessage",
    
    # Adapters
    "TelegramAdapter",
    "SlackAdapter",
    
    # Factory
    "get_chat_adapter",
    "get_default_adapter",
    "list_supported_platforms",
]

