"""
Adizon - User Model
PostgreSQL User-Management für Multi-Platform Chat
"""

import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from utils.database import Base


class UserRole(enum.Enum):
    """User Role Enum"""
    USER = "user"
    ADMIN = "admin"


class User(Base):
    """
    User Model für Adizon User-Management.
    
    Ein User kann über mehrere Chat-Plattformen (Telegram, Slack) mit Adizon interagieren.
    Die primäre Identity ist die Email-Adresse.
    
    Attributes:
        id: Unique User ID (UUID)
        email: Email-Adresse (unique, required)
        name: Display Name des Users
        telegram_id: Telegram User ID (optional, unique)
        slack_id: Slack User ID (optional, unique)
        is_active: User ist aktiv (kann einloggen)
        is_approved: User wurde von Admin freigegeben
        role: User-Role (user oder admin)
        crm_display_name: Name für CRM-Attribution ("via Michael")
        created_at: Account-Erstellungsdatum
        updated_at: Letztes Update
    """
    
    __tablename__ = "users"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identity Fields
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    
    # Platform IDs (nullable, unique)
    telegram_id = Column(String(100), unique=True, nullable=True, index=True)
    slack_id = Column(String(100), unique=True, nullable=True, index=True)
    
    # Status Fields
    is_active = Column(Boolean, default=True, nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)
    
    # Role
    role = Column(SQLEnum(UserRole, values_callable=lambda obj: [e.value for e in obj]), default=UserRole.USER, nullable=False)
    
    # CRM Integration
    crm_display_name = Column(String(255), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, name={self.name}, approved={self.is_approved})>"
    
    def to_dict(self):
        """Konvertiert User zu Dictionary (für API-Responses)"""
        return {
            "id": str(self.id),
            "email": self.email,
            "name": self.name,
            "telegram_id": self.telegram_id,
            "slack_id": self.slack_id,
            "is_active": self.is_active,
            "is_approved": self.is_approved,
            "role": self.role.value,
            "crm_display_name": self.crm_display_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def platform_ids(self):
        """Gibt alle verknüpften Platform-IDs zurück"""
        platforms = {}
        if self.telegram_id:
            platforms["telegram"] = self.telegram_id
        if self.slack_id:
            platforms["slack"] = self.slack_id
        return platforms
    
    @property
    def is_multi_platform(self):
        """Prüft ob User mehrere Plattformen verknüpft hat"""
        return len(self.platform_ids) > 1

