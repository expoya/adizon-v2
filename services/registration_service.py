"""
Adizon - Registration Service
Handles User Registration & Admin Notifications
"""

import os
import requests
from repositories.user_repository import UserRepository
from models.user import User
from typing import Optional


class RegistrationService:
    """Service für User-Registrierung und Admin-Notifications"""
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        self.admin_telegram_id = os.getenv("ADMIN_TELEGRAM_ID")
        self.telegram_token = os.getenv("TELEGRAM_TOKEN")
    
    def register_pending_user(
        self,
        platform: str,
        platform_id: str,
        user_name: str
    ) -> tuple[Optional[User], str]:
        """
        Registriert neuen User mit Pending-Status.
        
        Args:
            platform: "telegram" oder "slack"
            platform_id: Platform-spezifische User-ID
            user_name: Display Name
            
        Returns:
            (User-Objekt, Response-Message)
        """
        # 1. Erstelle Pending User in DB
        user = self.user_repo.create_pending_user(platform, platform_id, user_name)
        
        if not user:
            return None, "❌ Fehler bei der Registrierung. Bitte kontaktiere den Admin."
        
        # 2. Sende Admin-Notification
        self._notify_admin_new_registration(user, platform, platform_id)
        
        # 3. Response für User
        response = (
            f"👋 Hallo {user_name}!\n\n"
            f"Deine Registrierung wurde erfasst und wartet auf Freischaltung durch den Admin.\n"
            f"Du wirst benachrichtigt, sobald dein Zugang freigeschaltet wurde.\n\n"
            f"📋 Deine ID: {platform}:{platform_id}"
        )
        
        return user, response
    
    def _notify_admin_new_registration(
        self,
        user: User,
        platform: str,
        platform_id: str
    ):
        """
        Sendet Notification an Admin (via Telegram).
        
        Args:
            user: User-Objekt
            platform: Platform
            platform_id: Platform-ID
        """
        if not self.admin_telegram_id or not self.telegram_token:
            print("⚠️ Admin-Notification disabled (ADMIN_TELEGRAM_ID or TELEGRAM_TOKEN not set)")
            return
        
        # Notification Text
        message = (
            f"🆕 *Neue Registrierungsanfrage*\n\n"
            f"👤 Name: {user.name}\n"
            f"📧 Email: {user.email}\n"
            f"🔗 Platform: {platform.upper()}\n"
            f"🆔 Platform-ID: {platform_id}\n"
            f"🗓️ Zeitpunkt: {user.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"User-ID: `{user.id}`\n\n"
            f"_Zum Freischalten: Admin-Panel öffnen und User approven._"
        )
        
        # Telegram API Call
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.admin_telegram_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                print(f"✅ Admin notification sent for user {user.id}")
            else:
                print(f"⚠️ Admin notification failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Admin notification error: {e}")
    
    def notify_user_approved(self, user: User, platform: str):
        """
        Benachrichtigt User, dass er approved wurde.
        
        Args:
            user: User-Objekt
            platform: Platform
        """
        if not self.telegram_token:
            return
        
        platform_id = user.telegram_id if platform == "telegram" else user.slack_id
        
        if not platform_id:
            return
        
        message = (
            f"✅ *Willkommen bei Adizon!*\n\n"
            f"Dein Zugang wurde freigeschaltet.\n"
            f"Du kannst jetzt alle Funktionen nutzen.\n\n"
            f"Schreib mir einfach eine Nachricht!"
        )
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": platform_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                print(f"✅ Approval notification sent to user {user.id}")
        except Exception as e:
            print(f"❌ Approval notification error: {e}")

