"""
Telegram Chat Adapter
Implementierung für Telegram Bot API
"""

import os
import requests
from typing import Optional
from .interface import ChatAdapter, StandardMessage, WebhookParseError, MessageSendError


class TelegramAdapter(ChatAdapter):
    """
    Chat-Adapter für Telegram.
    
    Features:
    - Parse Telegram Webhook zu StandardMessage
    - Send Messages via Telegram Bot API
    - Error-Handling
    
    Env Variables:
    - TELEGRAM_BOT_TOKEN: Bot Token von @BotFather
    """
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not self.bot_token:
            raise ValueError("❌ TELEGRAM_BOT_TOKEN not set in .env")
        
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"
        print(f"✅ Telegram Adapter initialized")
    
    def parse_incoming(self, webhook_data: dict) -> StandardMessage:
        """
        Parst Telegram Webhook zu StandardMessage.
        
        Telegram Webhook Format:
        {
            "message": {
                "chat": {"id": 123456},
                "from": {"id": 123456, "first_name": "Max", "last_name": "Mustermann"},
                "text": "Hallo Adizon"
            }
        }
        """
        try:
            # Extract Message Object
            message_data = webhook_data.get("message", {})
            
            if not message_data:
                raise WebhookParseError("No 'message' field in Telegram webhook")
            
            # Extract User Info
            from_user = message_data.get("from", {})
            user_id = from_user.get("id")
            first_name = from_user.get("first_name", "Unknown")
            last_name = from_user.get("last_name", "")
            user_name = f"{first_name} {last_name}".strip()
            
            # Extract Chat Info
            chat = message_data.get("chat", {})
            chat_id = chat.get("id")
            
            # Extract Message Text
            text = message_data.get("text", "")
            
            # Validation
            if not user_id:
                raise WebhookParseError("Missing 'from.id' in Telegram webhook")
            if not chat_id:
                raise WebhookParseError("Missing 'chat.id' in Telegram webhook")
            if not text:
                raise WebhookParseError("Missing 'text' in Telegram webhook")
            
            # Create StandardMessage
            return StandardMessage(
                user_id=f"telegram:{user_id}",
                user_name=user_name,
                text=text,
                platform="telegram",
                chat_id=str(chat_id),
                raw_data=webhook_data
            )
            
        except WebhookParseError:
            raise
        except Exception as e:
            raise WebhookParseError(f"Failed to parse Telegram webhook: {e}")
    
    def send_message(self, chat_id: str, text: str) -> bool:
        """
        Sendet Nachricht via Telegram Bot API.
        
        Args:
            chat_id: Telegram Chat ID (as string)
            text: Message text to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.api_base}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"  # Optional: Support für Markdown-Formatierung
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Telegram message sent to chat {chat_id}")
                return True
            else:
                print(f"❌ Telegram API Error {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to send Telegram message: {e}")
            return False
    
    def get_platform_name(self) -> str:
        """Returns 'telegram'"""
        return "telegram"
    
    def format_response(self, text: str) -> str:
        """
        Formatiert Response für Telegram.
        Telegram unterstützt Markdown (optional).
        """
        # Für jetzt: Keine spezielle Formatierung
        # In Zukunft: Bold/Italic via Markdown
        return text
    
    def validate_webhook(self, webhook_data: dict) -> bool:
        """
        Optional: Validiert Telegram Webhook via Secret Token.
        
        Telegram unterstützt Secret Token für Webhook-Validation.
        Siehe: https://core.telegram.org/bots/api#setwebhook
        
        For now: Keine Validation (returns True).
        """
        # TODO: Implementiere Secret Token Validation wenn gewünscht
        return True


# === HELPER FUNCTIONS ===

def send_telegram_message(chat_id: str, text: str) -> bool:
    """
    Standalone Helper für direktes Senden (ohne Adapter-Instanz).
    Nützlich für Quick-Tests.
    """
    adapter = TelegramAdapter()
    return adapter.send_message(chat_id, text)

