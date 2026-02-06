from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from .user_schema import UserPublic


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserPublic


class LoginRequest(BaseModel):
    username: str
    password: str
    role: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    token: str = Field(min_length=16)
    new_password: str = Field(min_length=8)

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


# OTP Schemas
class SendOTPRequest(BaseModel):
    email: EmailStr
    purpose: str = "verification"  # verification, signup, password_reset

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)
    purpose: str = "verification"

class ResetPasswordWithOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8)

class OTPResponse(BaseModel):
    success: bool
    message: str
