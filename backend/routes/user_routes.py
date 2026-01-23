from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId

from ..models import post as post_model
from ..models import user as user_model
from ..schemas.post_schema import CommentSchema, PostResponse
from ..schemas.user_schema import UserPublic, UserUpdate
from ..utils.dependencies import get_current_user

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
        created_at=db_user.get("created_at"),
        updated_at=db_user.get("updated_at"),
    )


@router.get("/me", response_model=UserPublic)
async def get_me(current_user=Depends(get_current_user)):
    return db_user_to_public(current_user)


@router.put("/me", response_model=UserPublic)
async def update_me(payload: UserUpdate, current_user=Depends(get_current_user)):
    updates = {k: v for k, v in payload.dict(exclude_unset=True).items()}
    updated = await user_model.update_user(str(current_user["_id"]), updates)
    return db_user_to_public(updated)


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

