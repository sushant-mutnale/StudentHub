from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from ..models import post as post_model
from ..schemas.post_schema import (
    CommentCreate,
    CommentSchema,
    PostCreate,
    PostResponse,
    PostUpdate,
)
from ..utils.dependencies import get_current_student, get_current_user

router = APIRouter()


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


@router.get("/", response_model=list[PostResponse])
async def list_posts():
    posts = await post_model.list_posts()
    return [serialize_post(p) for p in posts]


@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(payload: PostCreate, current_student=Depends(get_current_student)):
    doc = await post_model.create_post(current_student, payload.dict())
    return serialize_post(doc)


@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: str, payload: PostUpdate, current_student=Depends(get_current_student)
):
    post = await post_model.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if str(post["author_id"]) != str(current_student["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized to edit this post")
    doc = await post_model.update_post(post_id, payload.dict(exclude_unset=True))
    return serialize_post(doc)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: str, current_student=Depends(get_current_student)):
    post = await post_model.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if str(post["author_id"]) != str(current_student["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    await post_model.delete_post(post_id)
    return {"status": "deleted"}


@router.post("/{post_id}/like", response_model=PostResponse)
async def like_post(post_id: str, current_user=Depends(get_current_user)):
    post = await post_model.toggle_like(post_id, str(current_user["_id"]))
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return serialize_post(post)


@router.post("/{post_id}/comments", response_model=PostResponse)
async def comment_on_post(
    post_id: str, payload: CommentCreate, current_user=Depends(get_current_user)
):
    post = await post_model.add_comment(
        post_id, str(current_user["_id"]), payload.text
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return serialize_post(post)

