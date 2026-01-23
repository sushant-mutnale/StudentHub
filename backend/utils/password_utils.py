import secrets
import hashlib
import hmac
import datetime
from typing import Tuple

def generate_reset_token() -> str:
    # cryptographically secure token
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def compare_token_hash(token: str, token_hash: str) -> bool:
    # use constant-time comparison
    return hmac.compare_digest(hash_token(token), token_hash)

def token_expiry_dt(minutes: int) -> datetime.datetime:
    return datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)