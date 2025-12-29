"""
Adizon - User Repository
CRUD Operations für User-Management
"""

import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.user import User, UserRole


class UserRepository:
    """Repository für User-CRUD-Operationen"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # === READ OPERATIONS ===
    
    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Holt User anhand der ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Holt User anhand der Email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_platform_id(self, platform: str, platform_id: str) -> Optional[User]:
        """
        Holt User anhand der Platform-ID (Telegram/Slack).
        
        Args:
            platform: "telegram" oder "slack"
            platform_id: Platform-spezifische User-ID
            
        Returns:
            User-Objekt oder None
        """
        if platform == "telegram":
            return self.db.query(User).filter(User.telegram_id == platform_id).first()
        elif platform == "slack":
            return self.db.query(User).filter(User.slack_id == platform_id).first()
        else:
            return None
    
    def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Holt alle User (mit Pagination)"""
        return self.db.query(User).offset(skip).limit(limit).all()
    
    def get_pending_users(self) -> List[User]:
        """Holt alle User, die auf Approval warten"""
        return self.db.query(User).filter(User.is_approved == False).all()
    
    def get_active_users(self) -> List[User]:
        """Holt alle aktiven und approved User"""
        return self.db.query(User).filter(
            User.is_active == True,
            User.is_approved == True
        ).all()
    
    # === CREATE OPERATIONS ===
    
    def create_user(
        self,
        email: str,
        name: str,
        crm_display_name: Optional[str] = None,
        telegram_id: Optional[str] = None,
        slack_id: Optional[str] = None,
        is_approved: bool = False,
        role: UserRole = UserRole.USER
    ) -> Optional[User]:
        """
        Erstellt neuen User.
        
        Args:
            email: Email-Adresse (unique)
            name: Display Name
            crm_display_name: Name für CRM-Attribution (default: name)
            telegram_id: Telegram User-ID (optional)
            slack_id: Slack User-ID (optional)
            is_approved: Sofort approved? (default: False)
            role: User-Role (default: USER)
            
        Returns:
            User-Objekt oder None bei Fehler
        """
        try:
            user = User(
                id=uuid.uuid4(),
                email=email,
                name=name,
                crm_display_name=crm_display_name or name,
                telegram_id=telegram_id,
                slack_id=slack_id,
                is_active=True,
                is_approved=is_approved,
                role=role
            )
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            return user
            
        except IntegrityError as e:
            self.db.rollback()
            print(f"❌ User creation failed: {e}")
            return None
    
    def create_pending_user(
        self,
        platform: str,
        platform_id: str,
        name: str
    ) -> Optional[User]:
        """
        Erstellt neuen User mit Pending-Status (wartet auf Admin-Approval).
        
        Args:
            platform: "telegram" oder "slack"
            platform_id: Platform-spezifische User-ID
            name: Display Name vom Chat-Provider
            
        Returns:
            User-Objekt oder None bei Fehler
        """
        # Generate temporary email (wird später vom Admin geändert)
        temp_email = f"{platform}_{platform_id}@temp.adizon.local"
        
        kwargs = {
            "email": temp_email,
            "name": name,
            "crm_display_name": name,
            "is_approved": False,
            "role": UserRole.USER
        }
        
        if platform == "telegram":
            kwargs["telegram_id"] = platform_id
        elif platform == "slack":
            kwargs["slack_id"] = platform_id
        
        return self.create_user(**kwargs)
    
    # === UPDATE OPERATIONS ===
    
    def update_user(
        self,
        user_id: uuid.UUID,
        **kwargs
    ) -> Optional[User]:
        """
        Updated User-Felder.
        
        Args:
            user_id: User-ID
            **kwargs: Felder zum Updaten (email, name, is_active, etc.)
            
        Returns:
            Updated User oder None
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        # Nur erlaubte Felder updaten
        allowed_fields = [
            'email', 'name', 'telegram_id', 'slack_id',
            'is_active', 'is_approved', 'role', 'crm_display_name'
        ]
        
        for key, value in kwargs.items():
            if key in allowed_fields and hasattr(user, key):
                setattr(user, key, value)
        
        try:
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as e:
            self.db.rollback()
            print(f"❌ User update failed: {e}")
            return None
    
    def approve_user(self, user_id: uuid.UUID) -> Optional[User]:
        """Approved einen pending User"""
        return self.update_user(user_id, is_approved=True)
    
    def deactivate_user(self, user_id: uuid.UUID) -> Optional[User]:
        """Deaktiviert einen User (Soft-Delete)"""
        return self.update_user(user_id, is_active=False)
    
    def link_platform(
        self,
        user_id: uuid.UUID,
        platform: str,
        platform_id: str
    ) -> Optional[User]:
        """
        Verknüpft eine zusätzliche Platform mit bestehendem User.
        
        Args:
            user_id: User-ID
            platform: "telegram" oder "slack"
            platform_id: Platform-spezifische User-ID
            
        Returns:
            Updated User oder None
        """
        kwargs = {}
        if platform == "telegram":
            kwargs["telegram_id"] = platform_id
        elif platform == "slack":
            kwargs["slack_id"] = platform_id
        else:
            return None
        
        return self.update_user(user_id, **kwargs)
    
    # === DELETE OPERATIONS ===
    
    def delete_user(self, user_id: uuid.UUID) -> bool:
        """
        Löscht User permanent (Hard-Delete).
        
        Args:
            user_id: User-ID
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        try:
            self.db.delete(user)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            print(f"❌ User deletion failed: {e}")
            return False
    
    # === STATISTICS ===
    
    def count_users(self) -> int:
        """Zählt alle User"""
        return self.db.query(User).count()
    
    def count_pending_users(self) -> int:
        """Zählt pending User"""
        return self.db.query(User).filter(User.is_approved == False).count()
    
    def count_active_users(self) -> int:
        """Zählt aktive User"""
        return self.db.query(User).filter(
            User.is_active == True,
            User.is_approved == True
        ).count()

