from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from ..models.user import get_user_by_id
from .auth import get_user_from_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    return await get_user_from_token(token)


def require_role(role: str):
    async def dependency(current_user=Depends(get_current_user)):
        if current_user.get("role") != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return dependency


async def get_current_student(current_user=Depends(get_current_user)):
    if current_user.get("role") != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    return current_user


async def get_current_recruiter(current_user=Depends(get_current_user)):
    if current_user.get("role") != "recruiter":
        raise HTTPException(status_code=403, detail="Recruiter access required")
    return current_user



