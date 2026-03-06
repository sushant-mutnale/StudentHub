"""
Verification Routes - Recruiter verification workflow.

Endpoints for:
- Requesting verification
- Checking verification status
- Admin approval/rejection
"""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..database import get_database
from ..models import audit as audit_model
from ..services import moderation_service
from ..utils.dependencies import get_current_user, get_current_recruiter

router = APIRouter(prefix="/verification", tags=["verification"])


class VerificationRequest(BaseModel):
    company_website: Optional[str] = None
    company_description: Optional[str] = None
    additional_info: Optional[str] = None


class VerificationStatusResponse(BaseModel):
    status: str
    email_verified: bool = False
    domain_verified: bool = False
    trust_score: int = 0
    verified_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


def users_collection():
    return get_database()["users"]


@router.get("/status", response_model=VerificationStatusResponse)
async def get_verification_status(recruiter=Depends(get_current_recruiter)):
    """Get the current verification status."""
    verification = recruiter.get("verification_data", {})
    db = get_database()
    
    trust_score = await moderation_service.get_recruiter_trust_score(
        str(recruiter["_id"]), db
    )
    
    return VerificationStatusResponse(
        status=recruiter.get("verification_status", moderation_service.VERIFICATION_UNVERIFIED),
        email_verified=verification.get("email_verified", False),
        domain_verified=verification.get("domain_verified", False),
        trust_score=trust_score,
        verified_at=verification.get("verified_at"),
        rejection_reason=verification.get("rejection_reason")
    )


@router.post("/request")
async def request_verification(
    payload: VerificationRequest,
    recruiter=Depends(get_current_recruiter)
):
    """Request account verification."""
    current_status = recruiter.get("verification_status", moderation_service.VERIFICATION_UNVERIFIED)
    
    if current_status == moderation_service.VERIFICATION_VERIFIED:
        return {"message": "Already verified", "status": current_status}
    
    if current_status == moderation_service.VERIFICATION_SUSPENDED:
        raise HTTPException(status_code=403, detail="Account is suspended")
    
    # Update profile with provided info
    updates = {"updated_at": datetime.utcnow()}
    if payload.company_website:
        updates["website"] = payload.company_website
    if payload.company_description:
        updates["company_description"] = payload.company_description
    
    # Check domain match for auto-verification
    email_domain = moderation_service.get_domain_from_email(recruiter.get("email", ""))
    website_domain = moderation_service.get_domain_from_url(
        payload.company_website or recruiter.get("website", "")
    )
    
    domain_verified = email_domain and website_domain and (
        email_domain == website_domain or email_domain.endswith(f".{website_domain}")
    )
    
    # Update verification data
    verification_data = recruiter.get("verification_data", {})
    verification_data.update({
        "email_verified": True,  # Assuming email is verified at signup
        "domain_verified": domain_verified,
        "verification_requested_at": datetime.utcnow(),
        "additional_info": payload.additional_info
    })
    updates["verification_data"] = verification_data
    
    # Determine new status
    if domain_verified:
        # Auto-verify if domain matches
        updates["verification_status"] = moderation_service.VERIFICATION_VERIFIED
        verification_data["verified_at"] = datetime.utcnow()
        verification_data["verified_by"] = "system_auto"
    else:
        updates["verification_status"] = moderation_service.VERIFICATION_REVIEW_REQUIRED
    
    await users_collection().update_one(
        {"_id": ObjectId(recruiter["_id"])},
        {"$set": updates}
    )
    
    # Audit log
    await audit_model.log_audit(
        action="verification_requested",
        entity_type="recruiter",
        entity_id=str(recruiter["_id"]),
        actor_id=str(recruiter["_id"]),
        metadata={"domain_verified": domain_verified}
    )
    
    return {
        "message": "Verification request submitted",
        "status": updates["verification_status"],
        "domain_verified": domain_verified
    }


@router.post("/check-domain")
async def check_domain_verification(recruiter=Depends(get_current_recruiter)):
    """Re-check domain verification status."""
    result = await moderation_service.check_domain_mismatch(recruiter)
    
    domain_verified = result.get("flag") is None
    
    if domain_verified:
        await users_collection().update_one(
            {"_id": ObjectId(recruiter["_id"])},
            {
                "$set": {
                    "verification_data.domain_verified": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )
    
    return {
        "domain_verified": domain_verified,
        "details": result.get("details")
    }
