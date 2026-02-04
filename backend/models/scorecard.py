"""
Scorecard Models - Structured evaluation templates and instances.

Collections:
- scorecard_templates: Reusable templates per stage type
- scorecard_instances: Filled-out evaluations linked to applications
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId

from ..database import get_database


def scorecard_templates_collection():
    return get_database()["scorecard_templates"]


def scorecard_instances_collection():
    return get_database()["scorecard_instances"]


# Default scoring scale
DEFAULT_SCALE_MIN = 1
DEFAULT_SCALE_MAX = 5

# Decision types
DECISION_PASS = "pass"
DECISION_HOLD = "hold"
DECISION_REJECT = "reject"

# Common rejection reasons
REJECTION_REASONS = [
    "communication_issues",
    "skills_mismatch",
    "culture_fit",
    "no_show",
    "insufficient_experience",
    "salary_expectations",
    "other"
]


def get_default_scorecard_templates() -> List[Dict[str, Any]]:
    """Get default scorecard templates for each stage type."""
    return [
        {
            "name": "Technical Interview - DSA",
            "stage_type": "interview",
            "interview_type": "technical_dsa",
            "criteria": [
                {
                    "name": "Problem Solving",
                    "description": "Ability to understand and break down problems",
                    "weight": 25,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                },
                {
                    "name": "Data Structures",
                    "description": "Knowledge of appropriate data structures",
                    "weight": 20,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                },
                {
                    "name": "Algorithms",
                    "description": "Algorithm design and complexity analysis",
                    "weight": 20,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                },
                {
                    "name": "Code Quality",
                    "description": "Clean, readable, maintainable code",
                    "weight": 15,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                },
                {
                    "name": "Debugging",
                    "description": "Ability to find and fix bugs",
                    "weight": 10,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": False
                },
                {
                    "name": "Communication",
                    "description": "Clear explanation of thought process",
                    "weight": 10,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                }
            ],
            "pass_threshold": 3.5,
            "is_default": True
        },
        {
            "name": "System Design Interview",
            "stage_type": "interview",
            "interview_type": "system_design",
            "criteria": [
                {
                    "name": "Architecture",
                    "description": "Overall system design and component organization",
                    "weight": 25,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                },
                {
                    "name": "Scalability",
                    "description": "Handling growth in users/data/traffic",
                    "weight": 25,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                },
                {
                    "name": "Trade-offs",
                    "description": "Understanding and articulating design trade-offs",
                    "weight": 20,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                },
                {
                    "name": "Technical Depth",
                    "description": "Deep knowledge of specific components",
                    "weight": 15,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                },
                {
                    "name": "Clarity",
                    "description": "Clear communication and diagrams",
                    "weight": 15,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                }
            ],
            "pass_threshold": 3.5,
            "is_default": True
        },
        {
            "name": "Behavioral Interview",
            "stage_type": "interview",
            "interview_type": "behavioral",
            "criteria": [
                {
                    "name": "STAR Structure",
                    "description": "Uses Situation-Task-Action-Result format",
                    "weight": 20,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                },
                {
                    "name": "Clarity",
                    "description": "Clear and concise responses",
                    "weight": 20,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                },
                {
                    "name": "Culture Fit",
                    "description": "Alignment with company values",
                    "weight": 25,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                },
                {
                    "name": "Motivation",
                    "description": "Genuine interest and enthusiasm",
                    "weight": 15,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                },
                {
                    "name": "Self-Awareness",
                    "description": "Honest reflection and growth mindset",
                    "weight": 20,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                }
            ],
            "pass_threshold": 3.5,
            "is_default": True
        },
        {
            "name": "Resume Screening",
            "stage_type": "screening",
            "criteria": [
                {
                    "name": "Skills Match",
                    "description": "Required skills present in resume",
                    "weight": 35,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                },
                {
                    "name": "Experience Level",
                    "description": "Appropriate experience for the role",
                    "weight": 30,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                },
                {
                    "name": "Education",
                    "description": "Educational background",
                    "weight": 15,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": False
                },
                {
                    "name": "Projects",
                    "description": "Relevant projects and achievements",
                    "weight": 20,
                    "scale_min": DEFAULT_SCALE_MIN,
                    "scale_max": DEFAULT_SCALE_MAX,
                    "required": True
                }
            ],
            "pass_threshold": 3.0,
            "is_default": True
        }
    ]


async def create_default_templates_for_company(company_id: str) -> List[dict]:
    """Create default scorecard templates for a company."""
    templates = get_default_scorecard_templates()
    now = datetime.utcnow()
    
    created = []
    for template in templates:
        doc = {
            **template,
            "company_id": ObjectId(company_id),
            "created_at": now,
            "updated_at": now
        }
        result = await scorecard_templates_collection().insert_one(doc)
        doc["_id"] = result.inserted_id
        created.append(doc)
    
    return created


async def get_scorecard_template(template_id: str) -> Optional[dict]:
    """Get a scorecard template by ID."""
    return await scorecard_templates_collection().find_one({"_id": ObjectId(template_id)})


async def list_scorecard_templates(
    company_id: str,
    stage_type: Optional[str] = None,
    interview_type: Optional[str] = None
) -> List[dict]:
    """List scorecard templates for a company."""
    query: Dict[str, Any] = {"company_id": ObjectId(company_id)}
    if stage_type:
        query["stage_type"] = stage_type
    if interview_type:
        query["interview_type"] = interview_type
    
    cursor = scorecard_templates_collection().find(query).sort("name", 1)
    return await cursor.to_list(length=100)


async def create_scorecard_template(
    company_id: str,
    name: str,
    stage_type: str,
    criteria: List[Dict],
    interview_type: Optional[str] = None,
    pass_threshold: float = 3.5
) -> dict:
    """Create a custom scorecard template."""
    now = datetime.utcnow()
    doc = {
        "company_id": ObjectId(company_id),
        "name": name,
        "stage_type": stage_type,
        "interview_type": interview_type,
        "criteria": criteria,
        "pass_threshold": pass_threshold,
        "is_default": False,
        "created_at": now,
        "updated_at": now
    }
    result = await scorecard_templates_collection().insert_one(doc)
    return await scorecard_templates_collection().find_one({"_id": result.inserted_id})


async def submit_scorecard(
    application_id: str,
    stage_id: str,
    template_id: str,
    evaluator_id: str,
    scores: List[Dict],
    decision: str,
    overall_notes: Optional[str] = None,
    rejection_reason: Optional[str] = None,
    interview_id: Optional[str] = None
) -> dict:
    """Submit a completed scorecard evaluation."""
    # Calculate overall score
    template = await get_scorecard_template(template_id)
    if not template:
        raise ValueError("Scorecard template not found")
    
    # Weight-based calculation
    total_weight = 0
    weighted_sum = 0
    
    criteria_map = {c["name"]: c for c in template.get("criteria", [])}
    for score_entry in scores:
        criterion_name = score_entry.get("criterion")
        score_value = score_entry.get("score", 0)
        
        if criterion_name in criteria_map:
            weight = criteria_map[criterion_name].get("weight", 1)
            weighted_sum += score_value * weight
            total_weight += weight
    
    overall_score = weighted_sum / total_weight if total_weight > 0 else 0
    
    now = datetime.utcnow()
    doc = {
        "application_id": ObjectId(application_id),
        "stage_id": stage_id,
        "interview_id": ObjectId(interview_id) if interview_id else None,
        "template_id": ObjectId(template_id),
        "evaluator_id": ObjectId(evaluator_id),
        "scores": scores,
        "overall_score": overall_score,
        "decision": decision,
        "overall_notes": overall_notes,
        "rejection_reason": rejection_reason,
        "submitted_at": now
    }
    
    result = await scorecard_instances_collection().insert_one(doc)
    return await scorecard_instances_collection().find_one({"_id": result.inserted_id})


async def get_scorecards_for_application(application_id: str) -> List[dict]:
    """Get all scorecards for an application."""
    cursor = scorecard_instances_collection().find({
        "application_id": ObjectId(application_id)
    }).sort("submitted_at", -1)
    return await cursor.to_list(length=100)


async def get_scorecard_aggregation(application_id: str) -> Dict[str, Any]:
    """Get aggregated scorecard stats for an application."""
    scorecards = await get_scorecards_for_application(application_id)
    
    if not scorecards:
        return {
            "count": 0,
            "average_score": None,
            "decisions": {},
            "pass_rate": None
        }
    
    total_score = sum(s.get("overall_score", 0) for s in scorecards)
    avg_score = total_score / len(scorecards)
    
    decisions = {}
    for s in scorecards:
        d = s.get("decision", "unknown")
        decisions[d] = decisions.get(d, 0) + 1
    
    pass_count = decisions.get(DECISION_PASS, 0)
    pass_rate = pass_count / len(scorecards) if scorecards else 0
    
    return {
        "count": len(scorecards),
        "average_score": round(avg_score, 2),
        "decisions": decisions,
        "pass_rate": round(pass_rate * 100, 1)
    }


async def ensure_scorecard_indexes():
    """Create indexes for scorecard collections."""
    templates_col = scorecard_templates_collection()
    await templates_col.create_index("company_id")
    await templates_col.create_index([("company_id", 1), ("stage_type", 1)])
    
    instances_col = scorecard_instances_collection()
    await instances_col.create_index("application_id")
    await instances_col.create_index([("application_id", 1), ("stage_id", 1)])
    await instances_col.create_index("evaluator_id")
    await instances_col.create_index("submitted_at")
