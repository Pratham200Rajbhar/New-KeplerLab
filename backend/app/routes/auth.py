import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, field_validator

from app.services.auth import (
    register_user,
    authenticate_user,
    get_current_user,
    create_access_token,
    create_refresh_token,
    store_refresh_token,
    validate_and_rotate_refresh_token,
    revoke_user_tokens,
)
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth")


class SignupRequest(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 2 or len(v) > 50:
            raise ValueError("Username must be between 2 and 50 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    role: str

    class Config:
        from_attributes = True


def _set_refresh_cookie(response: Response, token: str) -> None:
    """Set the refresh token as an HttpOnly Secure cookie."""
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/auth",  # Only sent to /auth endpoints
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Clear the refresh token cookie."""
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/auth",
    )


@router.post("/signup", response_model=UserResponse)
async def signup(request: SignupRequest):
    logger.info(f"Signup attempt for email: {request.email}")
    user = await register_user(request.email, request.username, request.password)
    logger.info(f"User registered successfully: {user.id}")
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        role=user.role
    )


@router.post("/login", response_model=AccessTokenResponse)
async def login(request: LoginRequest, response: Response):
    logger.info(f"Login attempt for email: {request.email}")
    user = await authenticate_user(request.email, request.password)

    if not user:
        logger.warning(f"Failed login attempt for email: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Create token family for rotation tracking
    family = str(uuid.uuid4())

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)}, family=family)

    # Store refresh token hash in DB
    await store_refresh_token(str(user.id), refresh_token, family)

    # Set refresh token as HttpOnly cookie
    _set_refresh_cookie(response, refresh_token)

    logger.info(f"User logged in successfully: {user.id}")
    return AccessTokenResponse(access_token=access_token)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token_endpoint(request: Request, response: Response):
    """Refresh access token using HttpOnly cookie. Implements token rotation."""
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token"
        )

    result = await validate_and_rotate_refresh_token(token)
    if result is None:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    user_id = result["user_id"]
    family = result["family"]

    # Create new rotated tokens
    access_token = create_access_token(data={"sub": user_id})
    new_refresh_token = create_refresh_token(data={"sub": user_id}, family=family)

    # Store new refresh token
    await store_refresh_token(user_id, new_refresh_token, family)

    # Set new refresh cookie
    _set_refresh_cookie(response, new_refresh_token)

    return AccessTokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        role=current_user.role
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user),
):
    """Logout: revoke all refresh tokens for user and clear cookie."""
    await revoke_user_tokens(str(current_user.id))
    _clear_refresh_cookie(response)
    logger.info(f"User logged out: {current_user.id}")
    return {"message": "Logged out successfully"}
