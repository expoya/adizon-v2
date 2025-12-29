"""
Adizon - User Management REST API
CRUD Endpoints für Admin-Frontend
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from utils.database import get_db
from repositories.user_repository import UserRepository
from models.user import User, UserRole
from services.registration_service import RegistrationService
import os

router = APIRouter(prefix="/api/users", tags=["users"])

# === AUTHENTICATION ===

def verify_admin_token(authorization: str = Header(None)):
    """Verify Admin API Token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    token = authorization.replace("Bearer ", "")
    admin_token = os.getenv("ADMIN_API_TOKEN")
    
    if not admin_token:
        raise HTTPException(status_code=500, detail="Admin token not configured")
    
    if token != admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    
    return True

# === PYDANTIC MODELS ===

class UserCreate(BaseModel):
    """User Creation Schema"""
    email: EmailStr
    name: str
    crm_display_name: Optional[str] = None
    telegram_id: Optional[str] = None
    slack_id: Optional[str] = None
    is_approved: bool = False
    role: str = "user"  # "user" oder "admin"

class UserUpdate(BaseModel):
    """User Update Schema"""
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    crm_display_name: Optional[str] = None
    telegram_id: Optional[str] = None
    slack_id: Optional[str] = None
    is_active: Optional[bool] = None
    is_approved: Optional[bool] = None
    role: Optional[str] = None

class UserResponse(BaseModel):
    """User Response Schema"""
    id: str
    email: str
    name: str
    telegram_id: Optional[str]
    slack_id: Optional[str]
    is_active: bool
    is_approved: bool
    role: str
    crm_display_name: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True

class StatsResponse(BaseModel):
    """Statistics Response"""
    total_users: int
    active_users: int
    pending_users: int

# === ENDPOINTS ===

@router.get("", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_token)
):
    """Get all users (with pagination)"""
    repo = UserRepository(db)
    users = repo.get_all_users(skip=skip, limit=limit)
    return [UserResponse(**user.to_dict()) for user in users]

@router.get("/pending", response_model=List[UserResponse])
def list_pending_users(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_token)
):
    """Get all users waiting for approval"""
    repo = UserRepository(db)
    users = repo.get_pending_users()
    return [UserResponse(**user.to_dict()) for user in users]

@router.get("/stats", response_model=StatsResponse)
def get_stats(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_token)
):
    """Get user statistics"""
    repo = UserRepository(db)
    return StatsResponse(
        total_users=repo.count_users(),
        active_users=repo.count_active_users(),
        pending_users=repo.count_pending_users()
    )

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_token)
):
    """Get user by ID"""
    repo = UserRepository(db)
    user = repo.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(**user.to_dict())

@router.post("/", response_model=UserResponse, status_code=201)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_token)
):
    """Create new user (manual by admin)"""
    repo = UserRepository(db)
    
    # Check if email already exists
    existing = repo.get_user_by_email(user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Parse role (case-insensitive)
    try:
        role_str = (user_data.role or "user").lower()
        role = UserRole.ADMIN if role_str == "admin" else UserRole.USER
    except:
        role = UserRole.USER
    
    user = repo.create_user(
        email=user_data.email,
        name=user_data.name,
        crm_display_name=user_data.crm_display_name,
        telegram_id=user_data.telegram_id,
        slack_id=user_data.slack_id,
        is_approved=user_data.is_approved,
        role=role
    )
    
    if not user:
        raise HTTPException(status_code=500, detail="User creation failed")
    
    return UserResponse(**user.to_dict())

@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: uuid.UUID,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_token)
):
    """Update user"""
    repo = UserRepository(db)
    
    # Filter out None values
    update_data = {k: v for k, v in user_data.dict().items() if v is not None}
    
    # Parse role if provided (case-insensitive)
    if "role" in update_data:
        try:
            role_str = str(update_data["role"]).lower()
            update_data["role"] = UserRole.ADMIN if role_str == "admin" else UserRole.USER
        except:
            del update_data["role"]
    
    user = repo.update_user(user_id, **update_data)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found or update failed")
    
    return UserResponse(**user.to_dict())

@router.post("/{user_id}/approve", response_model=UserResponse)
def approve_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_token)
):
    """Approve pending user"""
    repo = UserRepository(db)
    user = repo.approve_user(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Send notification to user
    reg_service = RegistrationService(repo)
    
    # Determine platform (telegram or slack)
    platform = None
    if user.telegram_id:
        platform = "telegram"
    elif user.slack_id:
        platform = "slack"
    
    if platform:
        reg_service.notify_user_approved(user, platform)
    
    return UserResponse(**user.to_dict())

@router.post("/{user_id}/link")
def link_platform(
    user_id: uuid.UUID,
    platform: str,
    platform_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_token)
):
    """Link additional platform to user"""
    repo = UserRepository(db)
    user = repo.link_platform(user_id, platform, platform_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found or link failed")
    
    return UserResponse(**user.to_dict())

@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_token)
):
    """Delete user (hard delete)"""
    repo = UserRepository(db)
    success = repo.delete_user(user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return None

