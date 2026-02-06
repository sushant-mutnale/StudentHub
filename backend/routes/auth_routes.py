from datetime import timedelta

from fastapi import APIRouter, HTTPException, status

from ..models import user as user_model
from ..schemas.auth_schema import LoginRequest, TokenResponse
from ..schemas.user_schema import RecruiterCreate, StudentCreate, UserPublic
from ..utils.auth import create_access_token, hash_password, verify_password

router = APIRouter()


def db_user_to_public(db_user: dict) -> UserPublic:
    """Convert MongoDB user document to UserPublic response model."""
    user_id = str(db_user.get("_id") or db_user.get("id"))
    return UserPublic(
        id=user_id,
        role=db_user["role"],
        username=db_user["username"],
        email=db_user["email"],
        full_name=db_user.get("full_name"),
        prn=db_user.get("prn"),
        college=db_user.get("college"),
        branch=db_user.get("branch"),
        year=db_user.get("year"),
        company_name=db_user.get("company_name"),
        contact_number=db_user.get("contact_number"),
        website=db_user.get("website"),
        company_description=db_user.get("company_description"),
        avatar_url=db_user.get("avatar_url"),
        bio=db_user.get("bio"),
        skills=db_user.get("skills") or [],
        created_at=db_user.get("created_at"),
        updated_at=db_user.get("updated_at"),
    )


@router.post("/signup/student", response_model=UserPublic)
async def signup_student(payload: StudentCreate):
    if await user_model.get_user_by_username(payload.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    if await user_model.get_user_by_email(payload.email):
        raise HTTPException(status_code=400, detail="Email already exists")

    student_data = payload.dict()
    student_data["password_hash"] = hash_password(student_data.pop("password"))
    created = await user_model.create_user(student_data)
    return db_user_to_public(created)


@router.post("/signup/recruiter", response_model=UserPublic)
async def signup_recruiter(payload: RecruiterCreate):
    if await user_model.get_user_by_username(payload.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    if await user_model.get_user_by_email(payload.email):
        raise HTTPException(status_code=400, detail="Email already exists")

    recruiter_data = payload.dict()
    recruiter_data["password_hash"] = hash_password(recruiter_data.pop("password"))
    created = await user_model.create_user(recruiter_data)
    return db_user_to_public(created)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    user = await user_model.get_user_by_username(payload.username)
    if not user or user.get("role") != payload.role:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token, expires_at = create_access_token(
        data={"sub": str(user["_id"]), "role": user["role"]},
        expires_delta=timedelta(minutes=60 * 24),
    )
    user_public = db_user_to_public(user)
    return TokenResponse(access_token=token, expires_at=expires_at, user=user_public)


# ============ Real-time Validation Endpoints ============

@router.get("/check-username/{username}")
async def check_username_available(username: str):
    """
    Check if a username is available.
    Used for real-time validation during signup.
    """
    if len(username) < 3:
        return {"available": False, "username": username, "message": "Username too short"}
    
    user = await user_model.get_user_by_username(username)
    return {
        "available": user is None,
        "username": username,
        "message": "Username is available" if user is None else "Username already taken"
    }


@router.get("/check-email/{email}")
async def check_email_available(email: str):
    """
    Check if an email is available.
    Used for real-time validation during signup.
    """
    user = await user_model.get_user_by_email(email)
    return {
        "available": user is None,
        "email": email,
        "message": "Email is available" if user is None else "Email already registered"
    }


# ============ OTP Endpoints ============

from ..schemas.auth_schema import (
    SendOTPRequest, VerifyOTPRequest, ResetPasswordWithOTPRequest, OTPResponse
)
from ..services.otp_service import otp_service
from ..services.email_service import email_service


@router.post("/send-otp", response_model=OTPResponse)
async def send_otp(payload: SendOTPRequest):
    """
    Send OTP to email for verification/signup/password reset.
    """
    # For password_reset, verify email exists
    if payload.purpose == "password_reset":
        user = await user_model.get_user_by_email(payload.email)
        if not user:
            # Don't reveal if email exists for security
            return OTPResponse(success=True, message="If email exists, OTP has been sent")
    
    # For signup, verify email doesn't exist
    if payload.purpose == "signup":
        user = await user_model.get_user_by_email(payload.email)
        if user:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate and send OTP
    otp = await otp_service.generate_otp(payload.email, payload.purpose)
    sent = await email_service.send_otp_email(payload.email, otp, payload.purpose)
    
    if sent:
        return OTPResponse(success=True, message="OTP sent to your email")
    else:
        raise HTTPException(status_code=500, detail="Failed to send OTP email")


@router.post("/verify-otp", response_model=OTPResponse)
async def verify_otp(payload: VerifyOTPRequest):
    """
    Verify OTP code.
    """
    success, message = await otp_service.verify_otp(
        payload.email, payload.otp, payload.purpose
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return OTPResponse(success=True, message=message)


@router.post("/forgot-password", response_model=OTPResponse)
async def forgot_password(payload: SendOTPRequest):
    """
    Request password reset OTP.
    """
    payload.purpose = "password_reset"
    return await send_otp(payload)


@router.post("/reset-password", response_model=OTPResponse)
async def reset_password(payload: ResetPasswordWithOTPRequest):
    """
    Reset password using OTP.
    """
    # Verify OTP first
    success, message = await otp_service.verify_otp(
        payload.email, payload.otp, "password_reset"
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    # Find user and update password
    user = await user_model.get_user_by_email(payload.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update password
    new_hash = hash_password(payload.new_password)
    await user_model.update_user_password(str(user["_id"]), new_hash)
    
    return OTPResponse(success=True, message="Password reset successfully")
