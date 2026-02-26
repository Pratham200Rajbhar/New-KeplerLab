import logging
import uuid
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timedelta, timezone

from app.db.prisma_client import prisma
from app.services.auth.security import (
    hash_password,
    verify_password,
    decode_token,
    hash_token,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


async def register_user(email: str, username: str, password: str):
    existing_user = await prisma.user.find_unique(where={"email": email})

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user = await prisma.user.create(
        data={
            "email": email,
            "username": username,
            "hashedPassword": hash_password(password),
        }
    )
    return user


async def authenticate_user(email: str, password: str):
    user = await prisma.user.find_unique(where={"email": email})

    if not user:
        return None
    if not verify_password(password, user.hashedPassword):
        return None
    return user


async def get_user_by_id(user_id: str):
    return await prisma.user.find_unique(where={"id": user_id})


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """Extract and validate user from Bearer token in Authorization header."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = await get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.isActive:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )

    return user


async def validate_file_token(token: str) -> Optional[str]:
    """Validate a short-lived file access token. Returns user_id or None."""
    payload = decode_token(token)
    if payload is None or payload.get("type") != "file":
        return None
    return payload.get("sub")


# ── Refresh Token Rotation ─────────────────────────────────


async def store_refresh_token(user_id: str, token: str, family: str) -> None:
    """Store a hashed refresh token in the database."""
    token_hash = hash_token(token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    await prisma.refreshtoken.create(
        data={
            "userId": user_id,
            "tokenHash": token_hash,
            "family": family,
            "expiresAt": expires_at,
        }
    )


async def validate_and_rotate_refresh_token(token: str) -> Optional[dict]:
    """
    Validate a refresh token and perform rotation.

    Returns {"user_id": ..., "family": ...} on success, or None on failure.
    If a used token is detected (replay attack), all tokens in the family are revoked.
    """
    payload = decode_token(token)
    if payload is None or payload.get("type") != "refresh":
        return None

    user_id = payload.get("sub")
    family = payload.get("family", user_id)
    token_hash = hash_token(token)

    # Find the token in DB
    stored = await prisma.refreshtoken.find_unique(where={"tokenHash": token_hash})

    if not stored:
        # Token not found — might be stolen or never stored
        logger.warning(f"Refresh token not found in DB for user {user_id}")
        return None

    if stored.used:
        # Token reuse detected — potential theft. Revoke entire family.
        logger.warning(f"Refresh token reuse detected for user {user_id}, family {family}. Revoking all.")
        await revoke_token_family(family)
        return None

    if stored.expiresAt < datetime.now(timezone.utc):
        logger.info(f"Refresh token expired for user {user_id}")
        return None

    # Mark old token as used - using find_first with used=False to avoid race conditions
    updated = await prisma.refreshtoken.update_many(
        where={
            "id": stored.id,
            "used": False
        },
        data={"used": True},
    )
    
    if updated == 0:
        # If updated is 0, it means someone else marked it as used in the meantime
        logger.warning(f"Refresh token was already rotated for user {user_id}")
        return None

    return {"user_id": user_id, "family": family}


async def revoke_token_family(family: str) -> None:
    """Revoke all tokens in a family (used when reuse is detected)."""
    await prisma.refreshtoken.delete_many(where={"family": family})


async def revoke_user_tokens(user_id: str) -> None:
    """Revoke all refresh tokens for a user (used on logout)."""
    await prisma.refreshtoken.delete_many(where={"userId": user_id})


async def cleanup_expired_tokens() -> int:
    """Remove expired tokens from DB. Returns count deleted."""
    result = await prisma.refreshtoken.delete_many(
        where={"expiresAt": {"lt": datetime.now(timezone.utc)}}
    )
    return result
