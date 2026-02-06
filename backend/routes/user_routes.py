from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId

from ..models import post as post_model
from ..models import user as user_model
from ..schemas.post_schema import CommentSchema, PostResponse
from ..schemas.user_schema import UserPublic, UserUpdate
from ..utils.dependencies import get_current_user
from ..utils.ai_scorer import update_student_ai_profile

router = APIRouter()


def db_user_to_public(db_user: dict) -> UserPublic:
    """Convert MongoDB user document to UserPublic response model."""
    user_id = str(db_user.get("_id") or db_user.get("id"))
    return UserPublic(
        id=user_id,
        role=db_user["role"],
        username=db_user["username"],
        email=db_user["email"],
        full_name=db_user.get("full_name"),
        prn=db_user.get("prn"),
        college=db_user.get("college"),
        branch=db_user.get("branch"),
        year=db_user.get("year"),
        company_name=db_user.get("company_name"),
        contact_number=db_user.get("contact_number"),
        website=db_user.get("website"),
        company_description=db_user.get("company_description"),
        avatar_url=db_user.get("avatar_url"),
        bio=db_user.get("bio"),
        skills=db_user.get("skills") or [],
        ai_profile=db_user.get("ai_profile"),
        created_at=db_user.get("created_at"),
        updated_at=db_user.get("updated_at"),
    )


@router.get("/me", response_model=UserPublic)
async def get_me(current_user=Depends(get_current_user)):
    return db_user_to_public(current_user)


@router.put("/me", response_model=UserPublic)
async def update_me(payload: UserUpdate, current_user=Depends(get_current_user)):
    updates = {k: v for k, v in payload.dict(exclude_unset=True).items()}
    user_id = str(current_user["_id"])
    updated = await user_model.update_user(user_id, updates)
    
    # Recalculate AI profile if student
    if current_user.get("role") == "student":
        await update_student_ai_profile(user_id)
        # Fetch again to get updated scores
        updated = await user_model.get_user_by_id(user_id)
        
    return db_user_to_public(updated)


    return db_user_to_public(updated)


@router.get("/search", response_model=list[dict])
async def search_users(
    skill: str | None = None,
    location: str | None = None,
    current_user=Depends(get_current_user)
):
    """Search for users (candidates) by skill or location."""
    query = {"role": "student"}
    
    if skill:
        # Simple regex match for now
        query["skills"] = {"$regex": skill, "$options": "i"}
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    
    cursor = user_model.users_collection().find(query).limit(50)
    users = await cursor.to_list(length=None)
    
    # Return simplified list
    return [
        {
            "id": str(u["_id"]),
            "username": u.get("username"),
            "full_name": u.get("full_name"),
            "skills": u.get("skills", []),
            "location": u.get("location"),
            "avatar_url": u.get("avatar_url")
        }
        for u in users
    ]


@router.get("/{user_id}", response_model=UserPublic)
async def get_public_profile(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    user = await user_model.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user_to_public(user)


def serialize_post(doc: dict) -> PostResponse:
    """Convert MongoDB post document to PostResponse with string IDs."""
    # Convert main post ID
    post_id = str(doc.get("_id") or doc.get("id"))
    
    # Convert author_id
    author_id = str(doc.get("author_id"))
    
    # Convert likes list
    likes = [str(like) if isinstance(like, ObjectId) else like for like in doc.get("likes", [])]
    
    # Convert comments
    comments = []
    for comment in doc.get("comments", []):
        comments.append(CommentSchema(
            id=str(comment.get("_id") or comment.get("id")),
            user_id=str(comment.get("user_id")),
            text=comment.get("text"),
            created_at=comment.get("created_at"),
        ))
    
    return PostResponse(
        id=post_id,
        author_id=author_id,
        author_name=doc.get("author_name"),
        author_username=doc.get("author_username"),
        author_role=doc.get("author_role"),
        author_avatar_url=doc.get("author_avatar_url"),
        content=doc.get("content"),
        tags=doc.get("tags", []),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
        likes=likes,
        comments=comments,
    )


@router.get("/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    posts = await post_model.list_posts_by_user(user_id)
    return [serialize_post(post) for post in posts]

