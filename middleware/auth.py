"""
Adizon - Authentication Middleware
Prüft ob User autorisiert ist, basierend auf Platform-ID
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from utils.database import SessionLocal
from repositories.user_repository import UserRepository
from models.user import User
from typing import Optional
import json


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Auth Middleware für Adizon.
    
    Flow:
    1. Webhook kommt rein (Telegram/Slack)
    2. Extrahiere platform + platform_id aus Request
    3. Query DB: Existiert User? Ist approved?
    4. Wenn JA → Inject User in Request State
    5. Wenn NEIN → Trigger Registration Flow
    """
    
    def __init__(self, app):
        super().__init__(app)
        # Endpoints die NICHT authenticated werden müssen
        self.skip_paths = [
            "/",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/api/users",  # Admin API hat eigene Auth
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Main Middleware Logic"""
        
        # Skip Auth für bestimmte Pfade
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)
        
        # Nur Webhooks authenticaten
        if not request.url.path.startswith("/webhook/"):
            return await call_next(request)
        
        # Parse Webhook Data
        try:
            body = await request.body()
            webhook_data = json.loads(body) if body else {}
            
            # Request body wieder setzen (für nachfolgende Handler)
            async def receive():
                return {"type": "http.request", "body": body}
            request._receive = receive
            
        except Exception as e:
            print(f"⚠️ Auth Middleware: Body parse failed: {e}")
            return await call_next(request)
        
        # Extrahiere Platform & User-ID
        platform = request.path_params.get("platform")
        user_info = self._extract_user_info(platform, webhook_data)
        
        if not user_info:
            # Kein User-Info gefunden → Durchlassen (z.B. Slack Challenge)
            return await call_next(request)
        
        platform_id, user_name = user_info
        
        print(f"🔎 Auth Middleware: Looking for user...")
        print(f"   Platform: {platform}")
        print(f"   Platform ID: {platform_id}")
        print(f"   User Name: {user_name}")
        
        # Query DB: Existiert User?
        db = SessionLocal()
        try:
            repo = UserRepository(db)
            user = repo.get_user_by_platform_id(platform, platform_id)
            
            print(f"🔎 DB Query Result: {user}")
            
            if user and user.is_approved and user.is_active:
                # ✅ User ist authorized
                request.state.user = user
                request.state.is_authenticated = True
                print(f"✅ Auth OK: {user.name} ({platform}:{platform_id})")
                
            elif user and not user.is_approved:
                # ⏳ User wartet auf Approval
                request.state.user = None
                request.state.is_authenticated = False
                request.state.registration_pending = True
                print(f"⏳ User pending approval: {user.name}")
                
            else:
                # 🆕 Neuer User → Registration Flow
                request.state.user = None
                request.state.is_authenticated = False
                request.state.registration_needed = True
                request.state.registration_data = {
                    "platform": platform,
                    "platform_id": platform_id,
                    "user_name": user_name
                }
                print(f"🆕 New user detected: {user_name} ({platform}:{platform_id})")
        
        finally:
            db.close()
        
        return await call_next(request)
    
    def _extract_user_info(self, platform: str, webhook_data: dict) -> Optional[tuple[str, str]]:
        """
        Extrahiert User-Info aus Webhook Data.
        
        Returns:
            (platform_id, user_name) oder None
        """
        if platform == "telegram":
            msg = webhook_data.get("message", {})
            from_user = msg.get("from", {})
            user_id = from_user.get("id")
            username = from_user.get("username") or from_user.get("first_name", "Unknown")
            
            if user_id:
                return (str(user_id), username)
        
        elif platform == "slack":
            event = webhook_data.get("event", {})
            user_id = event.get("user")
            # Slack username müsste via API geholt werden, wir nehmen erstmal die ID
            username = f"Slack User {user_id}"
            
            if user_id:
                return (user_id, username)
        
        return None

