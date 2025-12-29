"""
Slack Chat Adapter
Implementierung für Slack Bot API
"""

import os
import requests
from typing import Optional, Dict, Any
from .interface import ChatAdapter, StandardMessage, WebhookParseError, MessageSendError


class SlackAdapter(ChatAdapter):
    """
    Chat-Adapter für Slack.
    
    Features:
    - Parse Slack Event zu StandardMessage
    - Send Messages via Slack Web API
    - Challenge-Handling (Webhook Verification)
    - Error-Handling
    
    Env Variables:
    - SLACK_BOT_TOKEN: Bot Token (xoxb-...)
    - SLACK_SIGNING_SECRET: Signing Secret (für Webhook-Validation)
    
    Setup:
    1. Erstelle Slack App: https://api.slack.com/apps
    2. Bot Token Scopes: chat:write, channels:history, im:history
    3. Event Subscriptions: message.im, message.channels
    4. Install to Workspace
    """
    
    def __init__(self):
        self.bot_token = os.getenv("SLACK_BOT_TOKEN", "").strip()
        if not self.bot_token:
            raise ValueError("❌ SLACK_BOT_TOKEN not set in .env")
        
        self.signing_secret = os.getenv("SLACK_SIGNING_SECRET", "").strip()
        # Signing Secret ist optional für Basic Setup
        
        self.api_base = "https://slack.com/api"
        print(f"✅ Slack Adapter initialized")
    
    def parse_incoming(self, webhook_data: dict) -> StandardMessage:
        """
        Parst Slack Event zu StandardMessage.
        
        Slack Webhook Format:
        {
            "type": "event_callback",
            "event": {
                "type": "message",
                "user": "U123456",
                "text": "Hallo Adizon",
                "channel": "C123456"
            }
        }
        
        Oder Challenge (Webhook Verification):
        {
            "type": "url_verification",
            "challenge": "3eZbrw1aBm2rZgRNFdxV2595E9CY3gmdALWMmHkvFXO7tYXAYM8P"
        }
        """
        try:
            # Check for Challenge (Webhook Verification)
            if webhook_data.get("type") == "url_verification":
                challenge = webhook_data.get("challenge", "")
                raise WebhookParseError(f"CHALLENGE:{challenge}")  # Special handling in main.py
            
            # Check for Event Callback
            if webhook_data.get("type") != "event_callback":
                raise WebhookParseError(f"Unknown Slack webhook type: {webhook_data.get('type')}")
            
            # Extract Event
            event = webhook_data.get("event", {})
            
            if not event:
                raise WebhookParseError("No 'event' field in Slack webhook")
            
            # Skip Bot Messages (avoid loops)
            if event.get("bot_id"):
                raise WebhookParseError("Ignoring bot message (loop prevention)")
            
            # Extract User Info
            user_id = event.get("user")
            
            # Extract Message Text
            text = event.get("text", "")
            
            # Extract Channel Info (for replies)
            channel = event.get("channel")
            
            # Validation
            if not user_id:
                raise WebhookParseError("Missing 'event.user' in Slack webhook")
            if not channel:
                raise WebhookParseError("Missing 'event.channel' in Slack webhook")
            if not text:
                raise WebhookParseError("Missing 'event.text' in Slack webhook")
            
            # Get User Name via Slack API (optional, can be cached)
            user_name = self._get_user_name(user_id)
            
            # Create StandardMessage
            return StandardMessage(
                user_id=f"slack:{user_id}",
                user_name=user_name,
                text=text,
                platform="slack",
                chat_id=channel,
                raw_data=webhook_data
            )
            
        except WebhookParseError:
            raise
        except Exception as e:
            raise WebhookParseError(f"Failed to parse Slack webhook: {e}")
    
    def send_message(self, chat_id: str, text: str) -> bool:
        """
        Sendet Nachricht via Slack Web API.
        
        Args:
            chat_id: Slack Channel ID (z.B. "C123456")
            text: Message text to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.api_base}/chat.postMessage"
            headers = {
                "Authorization": f"Bearer {self.bot_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "channel": chat_id,
                "text": text
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    print(f"✅ Slack message sent to channel {chat_id}")
                    return True
                else:
                    error = data.get("error", "unknown")
                    print(f"❌ Slack API Error: {error}")
                    return False
            else:
                print(f"❌ Slack API HTTP Error {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to send Slack message: {e}")
            return False
    
    def get_platform_name(self) -> str:
        """Returns 'slack'"""
        return "slack"
    
    def format_response(self, text: str) -> str:
        """
        Formatiert Response für Slack.
        Slack unterstützt mrkdwn (ähnlich Markdown).
        
        For now: Keine spezielle Formatierung.
        """
        return text
    
    def validate_webhook(self, webhook_data: dict) -> bool:
        """
        Optional: Validiert Slack Webhook via Signing Secret.
        
        Slack sendet X-Slack-Signature Header für Verification.
        Siehe: https://api.slack.com/authentication/verifying-requests-from-slack
        
        For now: Keine Validation (returns True).
        TODO: Implementiere Signature-Verification
        """
        return True
    
    def _get_user_name(self, user_id: str) -> str:
        """
        Holt User-Name via Slack users.info API.
        
        Args:
            user_id: Slack User ID (z.B. "U123456")
            
        Returns:
            User Display Name oder "Unknown"
        """
        try:
            url = f"{self.api_base}/users.info"
            headers = {"Authorization": f"Bearer {self.bot_token}"}
            params = {"user": user_id}
            
            response = requests.get(url, headers=headers, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    user = data.get("user", {})
                    profile = user.get("profile", {})
                    
                    # Versuche verschiedene Name-Felder
                    display_name = profile.get("display_name")
                    real_name = profile.get("real_name")
                    name = user.get("name")
                    
                    return display_name or real_name or name or "Unknown"
            
            return "Unknown"
            
        except Exception as e:
            print(f"⚠️ Failed to get Slack user name: {e}")
            return "Unknown"


# === HELPER FUNCTIONS ===

def send_slack_message(channel_id: str, text: str) -> bool:
    """
    Standalone Helper für direktes Senden (ohne Adapter-Instanz).
    Nützlich für Quick-Tests.
    """
    adapter = SlackAdapter()
    return adapter.send_message(channel_id, text)


def handle_slack_challenge(webhook_data: dict) -> Optional[str]:
    """
    Handled Slack Challenge (Webhook Verification).
    
    Slack sendet beim Setup einen Challenge, der zurückgesendet werden muss.
    
    Args:
        webhook_data: Slack Webhook Data
        
    Returns:
        Challenge String wenn vorhanden, sonst None
    """
    if webhook_data.get("type") == "url_verification":
        return webhook_data.get("challenge")
    return None

