"""
Telegram Chat Adapter
Implementierung für Telegram Bot API
"""

import os
import uuid
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
        
        Telegram Webhook Format (Text):
        {
            "message": {
                "chat": {"id": 123456},
                "from": {"id": 123456, "first_name": "Max", "last_name": "Mustermann"},
                "text": "Hallo Adizon"
            }
        }
        
        Telegram Webhook Format (Voice):
        {
            "message": {
                "chat": {"id": 123456},
                "from": {...},
                "voice": {
                    "file_id": "AwACAgQAAxkBAAI...",
                    "duration": 5,
                    "mime_type": "audio/ogg"
                }
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
            
            # Validation
            if not user_id:
                raise WebhookParseError("Missing 'from.id' in Telegram webhook")
            if not chat_id:
                raise WebhookParseError("Missing 'chat.id' in Telegram webhook")
            
            # === TEXT OR VOICE? ===
            text = None
            
            # Check for Voice Message
            if "voice" in message_data:
                print("🎤 Voice message detected (Telegram)")
                text = self._handle_voice_message(message_data["voice"])
            
            # Fallback to Text Message
            elif "text" in message_data:
                text = message_data.get("text", "")
            
            # Neither text nor voice
            else:
                raise WebhookParseError("Message has neither 'text' nor 'voice'")
            
            if not text:
                raise WebhookParseError("Empty message text (after transcription)")
            
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
    
    # === VOICE MESSAGE HANDLING ===
    
    def _handle_voice_message(self, voice_data: dict) -> str:
        """
        Handles Telegram voice message: Download → Transcribe → Cleanup
        
        Args:
            voice_data: Telegram voice object with file_id, duration, mime_type
            
        Returns:
            Transcribed text
            
        Raises:
            WebhookParseError: If transcription fails
        """
        file_id = voice_data.get("file_id")
        duration = voice_data.get("duration", 0)
        
        if not file_id:
            raise WebhookParseError("Missing 'file_id' in voice message")
        
        print(f"🎤 Processing voice message: {duration}s, file_id={file_id[:20]}...")
        
        # Download audio file
        audio_path = None
        try:
            audio_path = self._download_voice_file(file_id)
            print(f"✅ Audio downloaded: {audio_path}")
            
            # Transcribe
            from tools.transcription import get_transcriber
            transcriber = get_transcriber()
            
            if not transcriber.is_enabled():
                raise WebhookParseError(
                    "🚫 Sprachnachrichten sind aktuell nicht verfügbar. "
                    "Bitte schreibe eine Textnachricht."
                )
            
            result = transcriber.transcribe(audio_path)
            print(f"✅ Transcription: '{result.text[:50]}...'")
            
            return result.text
            
        except Exception as e:
            print(f"❌ Voice transcription failed: {e}")
            raise WebhookParseError(
                "❌ Sprachnachricht konnte nicht verarbeitet werden. "
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
    
    def _download_voice_file(self, file_id: str) -> str:
        """
        Download Telegram voice file to /tmp
        
        Telegram Bot API:
        1. getFile → returns file_path
        2. Download from: https://api.telegram.org/file/bot{token}/{file_path}
        
        Args:
            file_id: Telegram file_id
            
        Returns:
            Path to downloaded file in /tmp
            
        Raises:
            Exception: If download fails
        """
        # Step 1: Get file path
        get_file_url = f"{self.api_base}/getFile"
        response = requests.get(get_file_url, params={"file_id": file_id}, timeout=10)
        
        if response.status_code != 200:
            raise Exception(f"getFile failed: {response.status_code} {response.text}")
        
        file_data = response.json()
        if not file_data.get("ok"):
            raise Exception(f"getFile error: {file_data}")
        
        file_path = file_data["result"]["file_path"]
        
        # Step 2: Download file
        download_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
        audio_response = requests.get(download_url, timeout=30)
        
        if audio_response.status_code != 200:
            raise Exception(f"Download failed: {audio_response.status_code}")
        
        # Step 3: Save to /tmp with unique name
        # Extract extension from file_path (usually .oga or .ogg)
        ext = file_path.split(".")[-1] if "." in file_path else "ogg"
        unique_id = uuid.uuid4().hex[:8]
        temp_path = f"/tmp/telegram_{file_id[:10]}_{unique_id}.{ext}"
        
        with open(temp_path, "wb") as f:
            f.write(audio_response.content)
        
        return temp_path


# === HELPER FUNCTIONS ===

def send_telegram_message(chat_id: str, text: str) -> bool:
    """
    Standalone Helper für direktes Senden (ohne Adapter-Instanz).
    Nützlich für Quick-Tests.
    """
    adapter = TelegramAdapter()
    return adapter.send_message(chat_id, text)

