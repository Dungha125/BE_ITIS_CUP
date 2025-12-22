"""
Pydantic Schemas cho Authentication
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserRegisterRequest(BaseModel):
    """Request schema cho đăng ký tài khoản"""
    full_name: str = Field(..., min_length=1, max_length=255, description="Họ và tên")
    username: str = Field(..., min_length=3, max_length=100, description="Tên đăng nhập")
    email: EmailStr = Field(..., description="Email")
    password: str = Field(..., min_length=6, max_length=200, description="Mật khẩu (tối thiểu 6 ký tự)")


class UserLoginRequest(BaseModel):
    """Request schema cho đăng nhập"""
    username: str = Field(..., description="Tên đăng nhập hoặc email")
    password: str = Field(..., description="Mật khẩu")


class UserResponse(BaseModel):
    """Response schema cho thông tin user"""
    id: int
    full_name: str
    username: str
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Response schema cho token"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RegisterResponse(BaseModel):
    """Response schema cho đăng ký thành công"""
    success: bool
    message: str
    data: UserResponse


class LoginResponse(BaseModel):
    """Response schema cho đăng nhập thành công"""
    success: bool
    message: str
    data: TokenResponse

