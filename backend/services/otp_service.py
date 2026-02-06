"""
OTP Service

Handles OTP generation, storage (Redis or Memory), and verification.
"""

import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

from ..config import settings

logger = logging.getLogger(__name__)


class OTPService:
    """Service for OTP management."""
    
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 10
    MAX_ATTEMPTS = 3
    
    def __init__(self):
        # In-memory store for fallback (format: {email: (otp, expiry, attempts)})
        self._memory_store: Dict[str, Tuple[str, datetime, int]] = {}
        self._redis = None
        self._try_connect_redis()
    
    def _try_connect_redis(self):
        """Try to connect to Redis for OTP storage."""
        try:
            from ..redis_client import get_redis
            self._redis = get_redis()
            logger.info("OTP Service using Redis storage")
        except Exception as e:
            logger.warning(f"Redis not available for OTP, using memory: {e}")
            self._redis = None
    
    def _generate_otp(self) -> str:
        """Generate a random 6-digit OTP."""
        return ''.join(secrets.choice('0123456789') for _ in range(self.OTP_LENGTH))
    
    def _get_key(self, email: str, purpose: str) -> str:
        """Generate storage key."""
        return f"otp:{purpose}:{email.lower()}"
    
    async def generate_otp(self, email: str, purpose: str = "verification") -> str:
        """
        Generate and store an OTP for the given email.
        Returns the OTP code.
        """
        otp = self._generate_otp()
        key = self._get_key(email, purpose)
        expiry = datetime.utcnow() + timedelta(minutes=self.OTP_EXPIRY_MINUTES)
        
        if self._redis:
            try:
                # Store in Redis with expiry
                await self._redis.setex(
                    key,
                    self.OTP_EXPIRY_MINUTES * 60,
                    f"{otp}:0"  # otp:attempts
                )
            except Exception as e:
                logger.error(f"Redis OTP store failed: {e}")
                # Fallback to memory
                self._memory_store[key] = (otp, expiry, 0)
        else:
            # Use memory store
            self._memory_store[key] = (otp, expiry, 0)
        
        logger.info(f"Generated OTP for {email} ({purpose})")
        return otp
    
    async def verify_otp(self, email: str, otp: str, purpose: str = "verification") -> Tuple[bool, str]:
        """
        Verify an OTP.
        Returns (success, message).
        """
        key = self._get_key(email, purpose)
        
        if self._redis:
            try:
                data = await self._redis.get(key)
                if not data:
                    return False, "OTP expired or not found"
                
                stored_otp, attempts = data.split(":")
                attempts = int(attempts)
                
                if attempts >= self.MAX_ATTEMPTS:
                    await self._redis.delete(key)
                    return False, "Too many failed attempts. Please request a new OTP."
                
                if otp == stored_otp:
                    await self._redis.delete(key)
                    return True, "OTP verified successfully"
                else:
                    # Increment attempts
                    await self._redis.setex(
                        key,
                        self.OTP_EXPIRY_MINUTES * 60,
                        f"{stored_otp}:{attempts + 1}"
                    )
                    remaining = self.MAX_ATTEMPTS - attempts - 1
                    return False, f"Invalid OTP. {remaining} attempts remaining."
                    
            except Exception as e:
                logger.error(f"Redis OTP verify failed: {e}")
                # Try memory fallback
        
        # Memory store verification
        if key not in self._memory_store:
            return False, "OTP expired or not found"
        
        stored_otp, expiry, attempts = self._memory_store[key]
        
        if datetime.utcnow() > expiry:
            del self._memory_store[key]
            return False, "OTP has expired"
        
        if attempts >= self.MAX_ATTEMPTS:
            del self._memory_store[key]
            return False, "Too many failed attempts. Please request a new OTP."
        
        if otp == stored_otp:
            del self._memory_store[key]
            return True, "OTP verified successfully"
        else:
            # Increment attempts
            self._memory_store[key] = (stored_otp, expiry, attempts + 1)
            remaining = self.MAX_ATTEMPTS - attempts - 1
            return False, f"Invalid OTP. {remaining} attempts remaining."
    
    async def invalidate_otp(self, email: str, purpose: str = "verification"):
        """Invalidate any existing OTP for the email."""
        key = self._get_key(email, purpose)
        
        if self._redis:
            try:
                await self._redis.delete(key)
            except Exception:
                pass
        
        if key in self._memory_store:
            del self._memory_store[key]
    
    def cleanup_expired(self):
        """Clean up expired OTPs from memory store."""
        now = datetime.utcnow()
        expired = [k for k, (_, expiry, _) in self._memory_store.items() if now > expiry]
        for k in expired:
            del self._memory_store[k]


# Singleton instance
otp_service = OTPService()
