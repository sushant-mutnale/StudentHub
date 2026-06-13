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
    # Verification Status Constants
    VERIFICATION_UNVERIFIED = "unverified"
    VERIFICATION_REVIEW_REQUIRED = "review_required"
    VERIFICATION_VERIFIED = "verified"
    VERIFICATION_SUSPENDED = "suspended"

    # Job Status Constants
    JOB_STATUS_PENDING_REVIEW = "pending_review"
    JOB_STATUS_PUBLISHED = "published"
    JOB_STATUS_REJECTED = "rejected"
    JOB_STATUS_CLOSED = "closed"
    
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

    async def get_recruiter_trust_score(self, recruiter_id: str, db) -> int:
        """Calculate trust score (0-100) for a recruiter."""
        from bson import ObjectId
        try:
            recruiter = await db["users"].find_one({"_id": ObjectId(recruiter_id)})
            if not recruiter:
                return 0
        except Exception:
            return 0
            
        score = 40  # base score
        
        # Email verified (always True for seeded, check verification_data)
        ver_data = recruiter.get("verification_data", {})
        if ver_data.get("email_verified"):
            score += 15
            
        # Domain verified
        if ver_data.get("domain_verified"):
            score += 25
            
        # Profile completeness
        if recruiter.get("company_name"):
            score += 5
        if recruiter.get("website"):
            score += 5
        if recruiter.get("company_description"):
            score += 5
        if recruiter.get("contact_number"):
            score += 5
            
        # Check connection count
        connections = recruiter.get("connections", [])
        if connections:
            score += min(len(connections) * 2, 10)
            
        return min(score, 100)

    def get_domain_from_email(self, email: str) -> Optional[str]:
        """Extract domain from an email address."""
        if not email or "@" not in email:
            return None
        parts = email.split("@")
        return parts[-1].strip().lower()

    def get_domain_from_url(self, url: str) -> Optional[str]:
        """Extract domain from a website URL."""
        if not url:
            return None
        cleaned = url.strip().lower()
        cleaned = re.sub(r'^https?://', '', cleaned)
        cleaned = re.sub(r'^www\.', '', cleaned)
        parts = cleaned.split('/')
        domain = parts[0].split(':')[0]
        return domain if domain else None

    async def check_domain_mismatch(self, recruiter: dict) -> dict:
        """
        Check if recruiter's email domain matches their website domain.
        Returns a dict with verification details and warning flags.
        """
        email = recruiter.get("email", "")
        website = recruiter.get("website", "")
        
        email_domain = self.get_domain_from_email(email)
        website_domain = self.get_domain_from_url(website)
        
        if not email_domain:
            return {"flag": "missing_email", "details": "Recruiter email is missing."}
        if not website_domain:
            return {"flag": "missing_website", "details": "Recruiter website URL is missing."}
            
        public_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "zoho.com", "protonmail.com"}
        if email_domain in public_domains:
            return {
                "flag": "public_email_domain",
                "details": f"Public email domains ({email_domain}) cannot be used for auto-verification."
            }
            
        matched = (email_domain == website_domain) or email_domain.endswith(f".{website_domain}") or website_domain.endswith(f".{email_domain}")
        
        if matched:
            return {"flag": None, "details": "Email domain matches website domain successfully."}
        else:
            return {
                "flag": "domain_mismatch",
                "details": f"Email domain '{email_domain}' does not match website domain '{website_domain}'."
            }

moderation_service = ModerationService()
