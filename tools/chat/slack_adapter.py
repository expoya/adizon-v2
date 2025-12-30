"""
Slack Chat Adapter
Implementierung für Slack Bot API
"""

import os
import uuid
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
        print(f"🔵 Slack Adapter: Parsing webhook data...")
        print(f"🔵 Webhook type: {webhook_data.get('type', 'unknown')}")
        
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
            # Slack kann bot_id, bot_profile, oder subtype="bot_message" senden
            if event.get("bot_id") or event.get("bot_profile") or event.get("subtype") == "bot_message":
                raise WebhookParseError("Ignoring bot message (loop prevention)")
            
            # Skip Message Subtypes (edits, deletes, etc.)
            # Diese Events haben oft kein 'user' Feld oder sind nicht relevant
            subtype = event.get("subtype")
            if subtype in ["message_changed", "message_deleted", "channel_join", "channel_leave"]:
                raise WebhookParseError(f"Ignoring Slack subtype: {subtype}")
            
            # Extract User Info
            user_id = event.get("user")
            
            # Extract Channel Info (for replies)
            channel = event.get("channel")
            
            # === TEXT OR AUDIO? ===
            text = None
            
            # Check for Audio Files
            files = event.get("files", [])
            if files and len(files) > 0:
                # Check if any file is audio
                first_file = files[0]
                mimetype = first_file.get("mimetype", "")
                
                if mimetype.startswith("audio/"):
                    print("🎤 Audio file detected (Slack)")
                    text = self._handle_audio_file(first_file)
            
            # Fallback to Text Message
            if not text:
                text = event.get("text", "")
            
            # Validation
            if not user_id:
                # Wenn kein user_id vorhanden ist, ist es wahrscheinlich ein System-Event
                raise WebhookParseError(f"Missing 'event.user' in Slack webhook (event_type: {event.get('type')}, subtype: {event.get('subtype', 'none')})")
            if not channel:
                raise WebhookParseError("Missing 'event.channel' in Slack webhook")
            if not text:
                raise WebhookParseError("Missing 'event.text' or audio file in Slack webhook")
            
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
    
    # === AUDIO FILE HANDLING ===
    
    def _handle_audio_file(self, file_data: dict) -> str:
        """
        Handles Slack audio file: Download → Transcribe → Cleanup
        
        Args:
            file_data: Slack file object with url_private, mimetype, size, etc.
            
        Returns:
            Transcribed text
            
        Raises:
            WebhookParseError: If transcription fails
        """
        file_id = file_data.get("id")
        file_url = file_data.get("url_private")
        mimetype = file_data.get("mimetype", "audio/*")
        size = file_data.get("size", 0)
        
        if not file_url:
            raise WebhookParseError("Missing 'url_private' in Slack audio file")
        
        print(f"🎤 Processing audio file: {mimetype}, {size} bytes, id={file_id}")
        
        # Download audio file
        audio_path = None
        try:
            audio_path = self._download_audio_file(file_url, mimetype)
            print(f"✅ Audio downloaded: {audio_path}")
            
            # Transcribe
            from tools.transcription import get_transcriber
            transcriber = get_transcriber()
            
            if not transcriber.is_enabled():
                raise WebhookParseError(
                    "🚫 Audio-Nachrichten sind aktuell nicht verfügbar. "
                    "Bitte schreibe eine Textnachricht."
                )
            
            result = transcriber.transcribe(audio_path)
            print(f"✅ Transcription: '{result.text[:50]}...'")
            
            return result.text
            
        except Exception as e:
            print(f"❌ Audio transcription failed: {e}")
            raise WebhookParseError(
                "❌ Audio-Nachricht konnte nicht verarbeitet werden. "
                "Bitte versuche es nochmal oder schreibe eine Textnachricht."
            )
        
        finally:
            # Cleanup: Delete temp file
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                    print(f"🗑️  Temp file deleted: {audio_path}")
                except Exception as e:
                    print(f"⚠️  Failed to delete temp file: {e}")
    
    def _download_audio_file(self, file_url: str, mimetype: str) -> str:
        """
        Download Slack audio file to /tmp
        
        Slack requires OAuth Bearer Token for url_private downloads.
        
        Args:
            file_url: Slack url_private (requires authentication)
            mimetype: File MIME type (e.g., "audio/mp3", "audio/wav")
            
        Returns:
            Path to downloaded file in /tmp
            
        Raises:
            Exception: If download fails
        """
        # Extract file extension from mimetype
        # audio/mp3 → mp3, audio/wav → wav, audio/mpeg → mp3
        ext = "mp3"  # default
        if "/" in mimetype:
            ext_map = {
                "audio/mp3": "mp3",
                "audio/mpeg": "mp3",
                "audio/wav": "wav",
                "audio/ogg": "ogg",
                "audio/m4a": "m4a",
                "audio/x-m4a": "m4a"
            }
            ext = ext_map.get(mimetype, mimetype.split("/")[1])
        
        # Download with OAuth Bearer Token
        headers = {"Authorization": f"Bearer {self.bot_token}"}
        response = requests.get(file_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"Slack file download failed: {response.status_code} {response.text}")
        
        # Save to /tmp with unique name
        unique_id = uuid.uuid4().hex[:8]
        temp_path = f"/tmp/slack_audio_{unique_id}.{ext}"
        
        with open(temp_path, "wb") as f:
            f.write(response.content)
        
        return temp_path


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

