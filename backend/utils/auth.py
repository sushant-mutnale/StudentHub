import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import settings
from ..models.user import get_user_by_id

logger = logging.getLogger(__name__)

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
    pbkdf2_sha256__default_rounds=390000,
)

_USER_CACHE_TTL = 60  # seconds


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt, expire


async def blacklist_token(jti: str, expires_at: datetime):
    """Add token JTI to blacklist (e.g., on logout or password change)."""
    try:
        from ..redis_client import get_redis
        redis = get_redis()
        remaining = int((expires_at - datetime.utcnow()).total_seconds())
        if remaining > 0:
            await redis.set(f"blacklist:jti:{jti}", "1", ex=remaining)
    except Exception as e:
        logger.warning(f"Failed to blacklist token JTI: {e}")


async def is_token_blacklisted(jti: str) -> bool:
    try:
        from ..redis_client import get_redis
        redis = get_redis()
        return await redis.exists(f"blacklist:jti:{jti}") > 0
    except Exception:
        return False  # Fail open on Redis error — can tighten later


def _user_to_serializable(user: dict) -> dict:
    """Convert a MongoDB user dict to a JSON-serializable form."""
    result = {}
    for k, v in user.items():
        if hasattr(v, "__str__") and type(v).__name__ == "ObjectId":
            result[k] = str(v)
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, list):
            result[k] = [
                _user_to_serializable(i) if isinstance(i, dict) else
                str(i) if type(i).__name__ == "ObjectId" else
                i.isoformat() if isinstance(i, datetime) else i
                for i in v
            ]
        elif isinstance(v, dict):
            result[k] = _user_to_serializable(v)
        else:
            result[k] = v
    return result


async def get_user_from_token(token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        # Check JTI blacklist
        jti = payload.get("jti")
        if jti and await is_token_blacklisted(jti):
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Try Redis cache first
    cache_key = f"auth:user:{user_id}"
    try:
        from ..redis_client import get_redis
        redis = get_redis()
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis cache read failed, falling back to DB: {e}")

    # Fallback: query DB
    user = await get_user_by_id(user_id)
    if user is None:
        raise credentials_exception

    # Store in Redis cache
    try:
        from ..redis_client import get_redis
        redis = get_redis()
        serializable_user = _user_to_serializable(user)
        await redis.set(cache_key, json.dumps(serializable_user), ex=_USER_CACHE_TTL)
    except Exception as e:
        logger.warning(f"Redis cache write failed: {e}")

    return user


async def invalidate_user_cache(user_id: str):
    """Invalidate the Redis user cache on logout or password change."""
    try:
        from ..redis_client import get_redis
        redis = get_redis()
        await redis.delete(f"auth:user:{user_id}")
    except Exception as e:
        logger.warning(f"Failed to invalidate user cache for {user_id}: {e}")
