
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Callable

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.database import SessionLocal, User

load_dotenv()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)


def get_auth_secret() -> str:
    """Load the JWT signing secret without using an insecure default."""
    secret = os.getenv("AUTH_SECRET_KEY", "")

    if len(secret) < 32:
        raise RuntimeError(
            "AUTH_SECRET_KEY must be configured with at least 32 characters."
        )

    return secret


def get_db():
    """Provide a database session for one request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def authenticate_user(
    db: Session,
    username: str,
    password: str,
) -> User | None:
    user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if user is None or not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def create_access_token(
    user: User,
    expires_minutes: int | None = None,
) -> str:
    if not user.is_active:
        raise ValueError("Cannot issue a token to an inactive user.")

    duration = (
        expires_minutes
        if expires_minutes is not None
        else ACCESS_TOKEN_EXPIRE_MINUTES
    )

    if duration <= 0:
        raise ValueError("Token lifetime must be positive.")

    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user.id),
        "iat": now,
        "exp": now + timedelta(minutes=duration),
    }

    return jwt.encode(
        payload,
        get_auth_secret(),
        algorithm=ALGORITHM,
    )


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            get_auth_secret(),
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp"]},
        )

        subject = payload.get("sub")
        user_id = int(subject)

        if user_id <= 0:
            raise ValueError("Invalid user ID.")

    except (
        jwt.InvalidTokenError,
        RuntimeError,
        TypeError,
        ValueError,
    ):
        raise unauthorized

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        raise unauthorized

    return user


def require_roles(*allowed_roles: str) -> Callable:
    """Build a dependency that restricts access to specified roles."""
    valid_roles = {"user", "approver", "admin"}

    if not allowed_roles or not set(allowed_roles).issubset(valid_roles):
        raise ValueError("Invalid or missing role configuration.")

    def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return current_user

    return role_checker
