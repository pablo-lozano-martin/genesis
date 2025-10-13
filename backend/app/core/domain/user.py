# ABOUTME: User domain model representing a user entity in the system
# ABOUTME: Contains user authentication fields and metadata, database-agnostic

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    """
    User domain model.

    Represents a user in the system with authentication credentials
    and metadata. This is a pure domain model without database concerns.
    """

    id: Optional[str] = Field(default=None, description="User unique identifier")
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    hashed_password: str = Field(..., description="Bcrypt hashed password")
    full_name: Optional[str] = Field(default=None, max_length=100, description="User's full name")
    is_active: bool = Field(default=True, description="Whether the user account is active")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Account creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "is_active": True,
                "created_at": "2025-01-15T10:30:00",
                "updated_at": "2025-01-15T10:30:00"
            }
        }


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=100)


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    email: Optional[EmailStr] = None
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(default=None, max_length=100)
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Public user response schema (excludes sensitive data)."""

    id: str
    email: EmailStr
    username: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "is_active": True,
                "created_at": "2025-01-15T10:30:00"
            }
        }
