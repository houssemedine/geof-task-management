from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Modélise la structure "RegisterRequest"."""

    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    """Modélise la structure "LoginRequest"."""

    email: EmailStr
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    """Modélise la structure "TokenResponse"."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """Modélise la structure "UserResponse"."""

    id: int
    email: EmailStr
    is_active: bool
    roles: list[str]
    created_at: datetime
    updated_at: datetime
