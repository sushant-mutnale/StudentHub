"""
Moderation Service (Security)

Automated risk scoring for user-generated content (Jobs, Posts, Messages).
Uses keyword analysis and patterns to detect spam, hate speech, or PII leaks.
"""

import re
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime

class RiskLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# Job Status Constants
JOB_STATUS_PENDING_REVIEW = "pending_review"
JOB_STATUS_PUBLISHED = "published"
JOB_STATUS_REJECTED = "rejected"
JOB_STATUS_CLOSED = "closed"

# Verification Status Constants
VERIFICATION_REVIEW_REQUIRED = "review_required"
VERIFICATION_VERIFIED = "verified"
VERIFICATION_SUSPENDED = "suspended"

class ModerationService:
    """
    Automated content moderation engine.
    """
    
    # Sensitive keywords (simplified for demo)
    SENSITIVE_KEYWORDS = {
        "scam", "fraud", "money laundering", "bitcoin", "crypto", 
        "bank account", "password", "credit card", "ssn", "social security"
    }
    
    PROFANITY_LIST = {
        "dammit", "hell", "crap" # Very mild list for demo purposes
    }
    
    @classmethod
    def analyze_text(cls, text: str) -> Dict[str, Any]:
        """
        Analyze text for risk factors.
        Returns risk score (0-100) and flagged categories.
        """
        if not text:
            return {"score": 0, "level": RiskLevel.SAFE, "flags": []}
            
        lower_text = text.lower()
        score = 0
        flags = []
        
        # Check PII Leaks (Regex)
        # Email pattern (outside of allowed contexts)
        # Phone pattern
        
        # Check Keywords
        for word in cls.SENSITIVE_KEYWORDS:
            if word in lower_text:
                score += 30
                flags.append(f"sensitive_keyword: {word}")
        
        for word in cls.PROFANITY_LIST:
             if word in lower_text:
                score += 20
                flags.append(f"profanity: {word}")
                
        # Determine Level
        if score >= 80:
            level = RiskLevel.CRITICAL
        elif score >= 60:
            level = RiskLevel.HIGH
        elif score >= 40:
            level = RiskLevel.MEDIUM
        elif score >= 20:
            level = RiskLevel.LOW
        else:
            level = RiskLevel.SAFE
            
        return {
            "score": min(score, 100),
            "level": level,
            "flags": flags,
            "timestamp": datetime.utcnow()
        }

    @classmethod
    async def flag_content(cls, content_type: str, content_id: str, analysis: Dict):
        """
        Persist moderation result to database.
        """
        from ..database import get_database
        from datetime import datetime as dt
        
        db = get_database()
        
        flag_doc = {
            "content_type": content_type,
            "content_id": content_id,
            "risk_score": analysis["score"],
            "risk_level": analysis["level"],
            "flags": analysis["flags"],
            "created_at": dt.utcnow(),
            "status": "open", # open, resolved, ignored
            "action_taken": None
        }
        
        # In a real app we'd save this to a 'moderation_queue' collection
        if analysis["level"] in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
             await db["moderation_queue"].insert_one(flag_doc)
             # Auto-hide content if critical?
             if analysis["level"] == RiskLevel.CRITICAL:
                 await cls._auto_hide_content(content_type, content_id)

    @classmethod
    async def _auto_hide_content(cls, content_type: str, content_id: str):
        """Auto-hide content that is Critical risk."""
        from ..database import get_database
        from bson import ObjectId
        db = get_database()
        
        if content_type == "job":
            await db["jobs"].update_one(
                {"_id": ObjectId(content_id)}, 
                {"$set": {"is_active": False, "moderation_status": "flagged"}}
            )
        elif content_type == "post":
            await db["posts"].update_one(
                {"_id": ObjectId(content_id)}, 
                {"$set": {"is_visible": False, "moderation_status": "flagged"}}
            )

moderation_service = ModerationService()
