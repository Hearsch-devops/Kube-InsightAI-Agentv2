

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_db, hash_password, require_roles
from app.database import AuditEvent, InvestigationHistory, User


router = APIRouter(prefix="/admin", tags=["Admin"])

RoleName = Literal["admin", "approver", "user"]


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=128)
    role: RoleName = "user"

class ChangeRoleRequest(BaseModel):
    role: RoleName

class ChangeStatusRequest(BaseModel):
    is_active: bool

class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=12, max_length=128)

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool

def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
    )

def record_audit(
    db: Session,
    actor: str,
    event_type: str,
    details: dict,
) -> None:
    db.add(
        AuditEvent(
            actor=actor,
            event_type=event_type,
            details=details,
        )
    )

@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    username = payload.username.strip()

    existing = db.scalar(
        select(User).where(User.username == username)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    user = User(
        username=username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )

    try:
        db.add(user)
        db.flush()

        record_audit(
            db,
            current_user.username,
            "user_created",
            {"user_id": user.id, "username": user.username, "role": user.role},
        )
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    return user_response(user)

@router.get("/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    users = db.scalars(select(User).order_by(User.id)).all()
    return [user_response(user) for user in users]

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot delete your own account",
        )

    # Protect the last active administrator.
    if user.role == "admin" and user.is_active:
        active_admin_count = db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.role == "admin",
                User.is_active.is_(True),
            )
        )

        if active_admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete the last active administrator",
            )

    # Preserve investigation history rather than deleting it implicitly.
    history_count = db.scalar(
        select(func.count())
        .select_from(InvestigationHistory)
        .where(InvestigationHistory.user_id == user.id)
    )

    if history_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This user has investigation history. "
                "Deactivate the account instead to preserve its records."
            ),
        )

    deleted_user = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
    }

    try:
        record_audit(
            db,
            current_user.username,
            "user_deleted",
            deleted_user,
        )
        db.delete(user)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "message": "User deleted successfully",
        **deleted_user,
    }

@router.put("/users/{user_id}/password")
def reset_user_password(
    user_id: int,
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    try:
        user.password_hash = hash_password(payload.new_password)

        record_audit(
            db,
            current_user.username,
            "user_password_reset",
            {
                "user_id": user.id,
                "username": user.username,
            },
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "message": f"Password updated successfully for {user.username}",
    }

@router.patch("/users/{user_id}/role", response_model=UserResponse)
def change_user_role(
    user_id: int,
    payload: ChangeRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "admin" and payload.role != "admin" and user.is_active:
        active_admins = db.scalars(
            select(User).where(User.role == "admin", User.is_active.is_(True))
        ).all()
        if len(active_admins) <= 1:
            raise HTTPException(
                status_code=409,
                detail="Cannot demote the last active administrator",
            )

    old_role = user.role
    user.role = payload.role

    record_audit(
        db,
        current_user.username,
        "user_role_changed",
        {"user_id": user.id, "old_role": old_role, "new_role": user.role},
    )
    db.commit()
    db.refresh(user)
    return user_response(user)

@router.patch("/users/{user_id}/status", response_model=UserResponse)
def change_user_status(
    user_id: int,
    payload: ChangeStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id and not payload.is_active:
        raise HTTPException(
            status_code=409,
            detail="You cannot deactivate your own account",
        )

    if user.role == "admin" and user.is_active and not payload.is_active:
        active_admins = db.scalars(
            select(User).where(User.role == "admin", User.is_active.is_(True))
        ).all()
        if len(active_admins) <= 1:
            raise HTTPException(
                status_code=409,
                detail="Cannot deactivate the last active administrator",
            )

    old_status = user.is_active
    user.is_active = payload.is_active

    record_audit(
        db,
        current_user.username,
        "user_status_changed",
        {
            "user_id": user.id,
            "old_is_active": old_status,
            "new_is_active": user.is_active,
        },
    )
    db.commit()
    db.refresh(user)
    return user_response(user)

@router.get("/audit")
def list_audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "approver")),
):
    events = db.scalars(
        select(AuditEvent)
        .order_by(
            AuditEvent.created_at.desc(),
            AuditEvent.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    ).all()

    return {
        "items": [
            {
                "id": event.id,
                "proposal_id": event.proposal_id,
                "actor": event.actor,
                "event_type": event.event_type,
                "details": event.details,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
        "limit": limit,
        "offset": offset,
    }
