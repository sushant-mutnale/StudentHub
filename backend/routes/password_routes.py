from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
from backend.schemas.auth_schema import ForgotPasswordRequest, ResetPasswordRequest
from backend.database import get_db
from backend.utils.password_utils import generate_reset_token, hash_token, token_expiry_dt, compare_token_hash
from backend.utils.email_send import send_password_reset_email
from backend.utils.auth import hash_password  # existing function to hash pw
import urllib.parse
import os

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/forgot-password", status_code=200)
async def forgot_password(payload: ForgotPasswordRequest, db=Depends(get_db)):
    email = payload.email.lower()
    user = await db["users"].find_one({"email": email})
    # Always return same message to avoid user enumeration
    msg = {"message": "If an account with that email exists, a password reset link has been sent."}
    if not user:
        return msg

    token = generate_reset_token()
    token_hash = hash_token(token)
    expires_at = token_expiry_dt(int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRES_MINUTES", "60")))

    await db["users"].update_one({"_id": user["_id"]}, {"$set": {
        "password_reset_token_hash": token_hash,
        "password_reset_expires_at": expires_at,
        "password_reset_used": False
    }})

    frontend = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")
    reset_url = f"{frontend.rstrip('/')}/reset-password?token={urllib.parse.quote(token)}&email={urllib.parse.quote(email)}"
    # send email (async not required for this helper)
    send_password_reset_email(email, reset_url)
    return msg

@router.post("/reset-password", status_code=200)
async def reset_password(payload: ResetPasswordRequest, db=Depends(get_db)):
    email = payload.email.lower()
    user = await db["users"].find_one({"email": email})
    # generic error message
    bad = HTTPException(status_code=400, detail="Invalid or expired token.")
    if not user:
        raise bad
    token_hash = user.get("password_reset_token_hash")
    expires_at = user.get("password_reset_expires_at")
    used = user.get("password_reset_used", False)
    if not token_hash or used or not expires_at:
        raise bad
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at < datetime.utcnow():
        raise bad
    if not compare_token_hash(payload.token, token_hash):
        raise bad

    # all good — update password
    new_hash = hash_password(payload.new_password)
    await db["users"].update_one({"_id": user["_id"]}, {"$set": {
        "password_hash": new_hash,
        "password_reset_used": True,
    }, "$unset": {"password_reset_token_hash": "", "password_reset_expires_at": ""}})

    # optional: send confirmation email
    try:
        from backend.utils.email_send import send_password_reset_email as send_confirm
        send_confirm(email, f"Your password was changed on StudentHub.")
    except Exception:
        pass

    return {"message": "Password updated successfully. Please login using your new password."}
