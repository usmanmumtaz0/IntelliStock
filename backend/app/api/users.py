"""Single-store administrator account management (never exposes password hashes)."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import require_roles, hash_password, normalize_email
from app.models.user import User, UserRole
from app.services.operations import audit

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    email: str = Field(max_length=255, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    username: str = Field(min_length=1, max_length=255)
    password: SecretStr = Field(min_length=12, max_length=128)
    role: UserRole = UserRole.STAFF


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: UserRole
    is_active: bool


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime
    signup_pending: bool


@router.get("", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    return db.query(User).order_by(User.signup_pending.desc(), User.username).all()


@router.post("", response_model=UserResponse, status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    account = User(email=normalize_email(str(data.email)), username=data.username,
                   hashed_password=hash_password(data.password.get_secret_value()), role=data.role)
    db.add(account)
    try:
        db.flush()
        audit(db, user, "create", "user", account.id,
              new={"email": account.email, "username": account.username, "role": account.role.value})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email or username already exists")
    return account


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, data: UserUpdate, db: Session = Depends(get_db),
                user=Depends(require_roles("admin"))):
    # Serialize administrative changes, including concurrent admin demotions.
    accounts = db.query(User).order_by(User.id).populate_existing().with_for_update().all()
    if user.role != UserRole.ADMIN or not user.is_active:
        raise HTTPException(403, "Administrator access required")
    account = next((item for item in accounts if item.id == user_id), None)
    if account is None:
        raise HTTPException(404, "User not found")
    if account.signup_pending:
        raise HTTPException(409, "Use Approve signup first; new signups must receive Staff access")
    if user_id == user.id and (data.role != UserRole.ADMIN or not data.is_active):
        raise HTTPException(409, "You cannot disable or demote your own administrator account")
    remaining = [item for item in accounts if item.id != user_id and item.is_active and item.role == UserRole.ADMIN]
    if not remaining and (not data.is_active or data.role != UserRole.ADMIN):
        raise HTTPException(409, "At least one active administrator is required")
    old = {"role": account.role.value, "is_active": account.is_active}
    account.role, account.is_active = data.role, data.is_active
    audit(db, user, "update", "user", account.id, old, data.model_dump(mode="json"))
    db.commit()
    return account


@router.post("/{user_id}/approve", response_model=UserResponse)
def approve_signup(user_id: str, db: Session = Depends(get_db),
                   user=Depends(require_roles("admin"))):
    # Same lock ordering as other administrator account changes.
    accounts = db.query(User).order_by(User.id).populate_existing().with_for_update().all()
    if user.role != UserRole.ADMIN or not user.is_active or user.signup_pending:
        raise HTTPException(403, "Administrator access required")
    account = next((item for item in accounts if item.id == user_id), None)
    if account is None:
        raise HTTPException(404, "User not found")
    if not account.signup_pending:
        raise HTTPException(409, "Account is not awaiting signup approval")
    account.role = UserRole.STAFF
    account.is_active = True
    account.signup_pending = False
    audit(db, user, "approve_signup", "user", account.id,
          old={"signup_pending": True, "is_active": False},
          new={"signup_pending": False, "is_active": True, "role": "staff"})
    db.commit()
    return account
