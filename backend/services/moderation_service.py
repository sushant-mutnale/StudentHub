"""
Moderation Service - Risk-based job and recruiter moderation.

Implements the "Flexible Model":
- Verified recruiters can auto-publish
- Suspicious activity triggers admin review
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re
from urllib.parse import urlparse

from bson import ObjectId

from ..database import get_database
from ..models import audit as audit_model


# Verification statuses
VERIFICATION_UNVERIFIED = "unverified"
VERIFICATION_VERIFIED = "verified"
VERIFICATION_REVIEW_REQUIRED = "review_required"
VERIFICATION_SUSPENDED = "suspended"

# Job statuses
JOB_STATUS_DRAFT = "draft"
JOB_STATUS_PUBLISHED = "published"
JOB_STATUS_PENDING_REVIEW = "pending_review"
JOB_STATUS_REJECTED = "rejected"
JOB_STATUS_CLOSED = "closed"

# Suspicious flag types
FLAG_DOMAIN_MISMATCH = "domain_mismatch"
FLAG_BURST_POSTING = "burst_posting"
FLAG_DUPLICATE_CONTENT = "duplicate_content"
FLAG_UNREALISTIC_SALARY = "unrealistic_salary"
FLAG_SUSPICIOUS_URL = "suspicious_url"
FLAG_EXCESSIVE_EDITS = "excessive_edits"
FLAG_NEW_ACCOUNT = "new_account"
FLAG_INCOMPLETE_PROFILE = "incomplete_profile"

# Risk thresholds
RISK_THRESHOLD_REVIEW = 5  # Score >= this triggers review
RISK_THRESHOLD_AUTO_REJECT = 15  # Score >= this auto-rejects


def get_domain_from_email(email: str) -> Optional[str]:
    """Extract domain from email address."""
    if not email or "@" not in email:
        return None
    return email.split("@")[1].lower()


def get_domain_from_url(url: str) -> Optional[str]:
    """Extract domain from URL."""
    if not url:
        return None
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return None


async def check_domain_mismatch(recruiter: dict) -> Dict[str, Any]:
    """Check if recruiter email domain matches company website."""
    email = recruiter.get("email", "")
    website = recruiter.get("website", "")
    
    email_domain = get_domain_from_email(email)
    website_domain = get_domain_from_url(website)
    
    if not email_domain or not website_domain:
        return {"flag": None, "score": 0}
    
    # Check if domains match (or email is subdomain of website)
    if email_domain == website_domain or email_domain.endswith(f".{website_domain}"):
        return {"flag": None, "score": 0}
    
    # Check for common public email domains
    public_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"}
    if email_domain in public_domains:
        return {
            "flag": FLAG_DOMAIN_MISMATCH,
            "score": 3,
            "details": f"Public email domain ({email_domain}) with company website ({website_domain})"
        }
    
    return {
        "flag": FLAG_DOMAIN_MISMATCH,
        "score": 2,
        "details": f"Email domain ({email_domain}) doesn't match website ({website_domain})"
    }


async def check_burst_posting(recruiter_id: str, db) -> Dict[str, Any]:
    """Check for suspicious burst of job postings."""
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    recent_jobs = await db["jobs"].count_documents({
        "recruiter_id": ObjectId(recruiter_id),
        "created_at": {"$gte": one_hour_ago}
    })
    
    if recent_jobs > 10:
        return {
            "flag": FLAG_BURST_POSTING,
            "score": 5,
            "details": f"{recent_jobs} jobs posted in last hour"
        }
    elif recent_jobs > 5:
        return {
            "flag": FLAG_BURST_POSTING,
            "score": 2,
            "details": f"{recent_jobs} jobs posted in last hour"
        }
    
    return {"flag": None, "score": 0}


async def check_excessive_edits(job_id: str, db) -> Dict[str, Any]:
    """Check for excessive job edits in short time."""
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    edit_count = await db["audit_logs"].count_documents({
        "entity_type": "job",
        "entity_id": job_id,
        "action": "job_edited",
        "timestamp": {"$gte": one_hour_ago}
    })
    
    if edit_count > 10:
        return {
            "flag": FLAG_EXCESSIVE_EDITS,
            "score": 4,
            "details": f"{edit_count} edits in last hour"
        }
    
    return {"flag": None, "score": 0}


async def check_duplicate_content(job: dict, recruiter_id: str, db) -> Dict[str, Any]:
    """Check for duplicate job postings."""
    title = job.get("title", "").lower().strip()
    
    # Find similar jobs by same recruiter
    similar_jobs = await db["jobs"].count_documents({
        "recruiter_id": ObjectId(recruiter_id),
        "title": {"$regex": re.escape(title), "$options": "i"},
        "_id": {"$ne": job.get("_id")}
    })
    
    if similar_jobs >= 3:
        return {
            "flag": FLAG_DUPLICATE_CONTENT,
            "score": 4,
            "details": f"{similar_jobs} similar jobs found"
        }
    
    return {"flag": None, "score": 0}


def check_unrealistic_salary(job: dict) -> Dict[str, Any]:
    """Check for unrealistic salary values."""
    salary = job.get("salary")
    if not salary:
        return {"flag": None, "score": 0}
    
    # Try to extract numeric value
    salary_str = str(salary).replace(",", "").replace("$", "").replace("₹", "")
    try:
        salary_num = float(re.search(r'\d+', salary_str).group())
    except (AttributeError, ValueError):
        return {"flag": None, "score": 0}
    
    # Flag unrealistic values (too high or too low for annual/monthly)
    if salary_num > 10000000 or (salary_num < 1000 and "hour" not in str(salary).lower()):
        return {
            "flag": FLAG_UNREALISTIC_SALARY,
            "score": 3,
            "details": f"Suspicious salary value: {salary}"
        }
    
    return {"flag": None, "score": 0}


def check_suspicious_urls(job: dict) -> Dict[str, Any]:
    """Check for suspicious external URLs in job description."""
    description = job.get("description", "")
    
    # Find URLs in description
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, description)
    
    suspicious_patterns = [
        r'bit\.ly', r'tinyurl', r'goo\.gl',  # URL shorteners
        r'\.xyz$', r'\.tk$', r'\.ml$',  # Free domains
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'  # IP addresses
    ]
    
    for url in urls:
        for pattern in suspicious_patterns:
            if re.search(pattern, url, re.I):
                return {
                    "flag": FLAG_SUSPICIOUS_URL,
                    "score": 4,
                    "details": f"Suspicious URL pattern: {url[:50]}"
                }
    
    return {"flag": None, "score": 0}


def check_new_account(recruiter: dict) -> Dict[str, Any]:
    """Flag if account is very new."""
    created_at = recruiter.get("created_at")
    if not created_at:
        return {"flag": None, "score": 0}
    
    account_age = datetime.utcnow() - created_at
    if account_age < timedelta(hours=24):
        return {
            "flag": FLAG_NEW_ACCOUNT,
            "score": 2,
            "details": "Account less than 24 hours old"
        }
    
    return {"flag": None, "score": 0}


def check_incomplete_profile(recruiter: dict) -> Dict[str, Any]:
    """Check if recruiter profile is incomplete."""
    required_fields = ["company_name", "website", "company_description"]
    missing = [f for f in required_fields if not recruiter.get(f)]
    
    if len(missing) >= 2:
        return {
            "flag": FLAG_INCOMPLETE_PROFILE,
            "score": 2,
            "details": f"Missing: {', '.join(missing)}"
        }
    
    return {"flag": None, "score": 0}


async def calculate_job_risk_score(job: dict, recruiter: dict, db) -> Dict[str, Any]:
    """Calculate overall risk score for a job posting."""
    flags = []
    total_score = 0
    
    # Run all checks
    checks = [
        await check_domain_mismatch(recruiter),
        await check_burst_posting(str(recruiter["_id"]), db),
        await check_duplicate_content(job, str(recruiter["_id"]), db),
        check_unrealistic_salary(job),
        check_suspicious_urls(job),
        check_new_account(recruiter),
        check_incomplete_profile(recruiter)
    ]
    
    for check in checks:
        if check.get("flag"):
            flags.append({
                "type": check["flag"],
                "score": check["score"],
                "details": check.get("details")
            })
            total_score += check["score"]
    
    # Determine status
    if total_score >= RISK_THRESHOLD_AUTO_REJECT:
        status = JOB_STATUS_REJECTED
        review_required = False
    elif total_score >= RISK_THRESHOLD_REVIEW:
        status = JOB_STATUS_PENDING_REVIEW
        review_required = True
    elif recruiter.get("verification_status") == VERIFICATION_VERIFIED:
        status = JOB_STATUS_PUBLISHED
        review_required = False
    else:
        status = JOB_STATUS_PENDING_REVIEW
        review_required = True
    
    return {
        "risk_score": total_score,
        "flags": flags,
        "suggested_status": status,
        "review_required": review_required
    }


async def get_recruiter_trust_score(recruiter_id: str, db) -> int:
    """Calculate trust score based on history."""
    score = 50  # Base score
    
    # Positive: Verified status
    recruiter = await db["users"].find_one({"_id": ObjectId(recruiter_id)})
    if recruiter and recruiter.get("verification_status") == VERIFICATION_VERIFIED:
        score += 30
    
    # Positive: Account age
    if recruiter:
        age = datetime.utcnow() - recruiter.get("created_at", datetime.utcnow())
        if age > timedelta(days=90):
            score += 10
        elif age > timedelta(days=30):
            score += 5
    
    # Positive: Successful hires
    hires = await db["applications"].count_documents({
        "company_id": ObjectId(recruiter_id),
        "status": "hired"
    })
    score += min(hires * 2, 20)
    
    # Negative: Flagged jobs
    flagged_jobs = await db["jobs"].count_documents({
        "recruiter_id": ObjectId(recruiter_id),
        "moderation.risk_score": {"$gte": RISK_THRESHOLD_REVIEW}
    })
    score -= flagged_jobs * 5
    
    return max(0, min(100, score))
