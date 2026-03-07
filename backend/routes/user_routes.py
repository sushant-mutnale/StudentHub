from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId

from ..models import post as post_model
from ..models import user as user_model
from ..schemas.post_schema import CommentSchema, PostResponse
from ..schemas.user_schema import UserPublic, UserUpdate
from ..utils.dependencies import get_current_user
from ..utils.ai_scorer import update_student_ai_profile
from ..models import connection as conn_model
from ..models import notification as notify_model

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
        connections=db_user.get("connections") or [],
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


@router.get("/suggested", response_model=list[dict])
async def get_suggested_users(current_user=Depends(get_current_user)):
    """Suggest users based on shared skills, college, or year."""
    user_id = str(current_user["_id"])
    existing_connections = current_user.get("connections", [])
    
    # Base query: Students only, not current user, not already connected
    query = {
        "role": "student",
        "_id": {"$ne": ObjectId(user_id), "$nin": [ObjectId(cid) for cid in existing_connections if ObjectId.is_valid(cid)]}
    }
    
    # Try to find users with shared skills or from same college
    user_skills = []
    if current_user.get("skills"):
        if isinstance(current_user["skills"][0], dict):
            user_skills = [s["name"] for s in current_user["skills"]]
        else:
            user_skills = current_user["skills"]
            
    college = current_user.get("college")
    
    # OR query for relevance
    relevance_criteria = []
    if user_skills:
        relevance_criteria.append({"skills.name": {"$in": user_skills}})
    if college:
        relevance_criteria.append({"college": college})
        
    if relevance_criteria:
        query["$or"] = relevance_criteria
        
    cursor = user_model.users_collection().find(query).limit(10)
    users = await cursor.to_list(length=None)
    
    # If not enough relevant users, fill with others
    if len(users) < 3:
        exclude_ids = [ObjectId(user_id)] + [ObjectId(cid) for cid in existing_connections if ObjectId.is_valid(cid)] + [u["_id"] for u in users]
        fallback_query = {
            "role": "student",
            "_id": {"$nin": exclude_ids}
        }
        fallback_cursor = user_model.users_collection().find(fallback_query).limit(5 - len(users))
        fallback_users = await fallback_cursor.to_list(length=None)
        users.extend(fallback_users)
    
    results = []
    for u in users:
        reason = "New discovery"
        u_skills = []
        if u.get("skills"):
            if isinstance(u["skills"][0], dict):
                u_skills = [s["name"] for s in u["skills"]]
            else:
                u_skills = u["skills"]
                
        shared = set(user_skills).intersection(set(u_skills))
        if shared:
            reason = f"Shared skill: {list(shared)[0]}"
        elif u.get("college") == college and college:
            reason = f"From {college}"
        elif u.get("year") == current_user.get("year") and u.get("year"):
            reason = f"Same year student"
            
        results.append({
            "id": str(u["_id"]),
            "username": u.get("username"),
            "full_name": u.get("full_name"),
            "location": u.get("location") or u.get("college") or "Student",
            "avatar_url": u.get("avatar_url"),
            "reason": reason
        })
        
    return results


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


@router.post("/connections/{target_id}")
async def add_connection(target_id: str, current_user=Depends(get_current_user)):
    user_id = str(current_user["_id"])
    if user_id == target_id:
        raise HTTPException(status_code=400, detail="Cannot connect to yourself")
    
    # Check if a request already exists
    existing = await conn_model.find_existing_request(user_id, target_id)
    if existing:
        if existing["status"] == "accepted":
            return {"message": "Already connected", "status": "accepted"}
        if str(existing["sender_id"]) == user_id:
            return {"message": "Request already sent", "status": "pending"}
        else:
            return {"message": "They already sent you a horizontal request. Check your pending requests.", "status": "incoming_pending"}

    # Create new pending request
    await conn_model.create_connection_request(user_id, target_id)
    
    # Notify target user
    await notify_model.create_notification(
        user_id=target_id,
        kind="connection_request",
        payload={
            "sender_id": user_id,
            "sender_name": current_user.get("full_name") or current_user.get("username"),
            "message": "sent you a connection request"
        },
        category="general"
    )
        
    return {"message": "Connection request sent", "status": "pending"}


@router.get("/connections/requests/pending")
async def list_pending_requests(current_user=Depends(get_current_user)):
    user_id = str(current_user["_id"])
    requests = await conn_model.get_pending_requests(user_id)
    
    results = []
    for req in requests:
        sender = await user_model.get_user_by_id(str(req["sender_id"]))
        if sender:
            results.append({
                "request_id": str(req["_id"]),
                "sender": {
                    "id": str(sender["_id"]),
                    "username": sender.get("username"),
                    "full_name": sender.get("full_name"),
                    "avatar_url": sender.get("avatar_url")
                },
                "created_at": req["created_at"]
            })
    return results


@router.post("/connections/requests/{request_id}/accept")
async def accept_connection(request_id: str, current_user=Depends(get_current_user)):
    user_id = str(current_user["_id"])
    request = await conn_model.get_request_by_id(request_id)
    
    if not request or str(request["receiver_id"]) != user_id:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request["status"] != "pending":
        return {"message": "Request already processed"}

    # 1. Update request status
    await conn_model.update_request_status(request_id, "accepted")
    
    # 2. Add to both users' connection lists
    sender_id = str(request["sender_id"])
    
    # Update current user (receiver)
    receiver_conns = current_user.get("connections", [])
    if sender_id not in receiver_conns:
        receiver_conns.append(sender_id)
        await user_model.update_user(user_id, {"connections": receiver_conns})
        
    # Update sender
    sender_user = await user_model.get_user_by_id(sender_id)
    if sender_user:
        sender_conns = sender_user.get("connections", [])
        if user_id not in sender_conns:
            sender_conns.append(user_id)
            await user_model.update_user(sender_id, {"connections": sender_conns})

    # 3. Notify sender that request was accepted
    await notify_model.create_notification(
        user_id=sender_id,
        kind="connection_accepted",
        payload={
            "receiver_id": user_id,
            "receiver_name": current_user.get("full_name") or current_user.get("username"),
            "message": "accepted your connection request"
        },
        category="general"
    )

    return {"message": "Connection accepted"}

@router.post("/connections/requests/{request_id}/decline")
async def decline_connection(request_id: str, current_user=Depends(get_current_user)):
    user_id = str(current_user["_id"])
    request = await conn_model.get_request_by_id(request_id)
    
    if not request or str(request["receiver_id"]) != user_id:
        raise HTTPException(status_code=404, detail="Request not found")

    await conn_model.update_request_status(request_id, "declined")
    return {"message": "Connection declined"}


@router.delete("/connections/{target_id}")
async def remove_connection(target_id: str, current_user=Depends(get_current_user)):
    user_id = str(current_user["_id"])
    
    connections = current_user.get("connections", [])
    if target_id in connections:
        connections.remove(target_id)
        await user_model.update_user(user_id, {"connections": connections})
        
    return {"message": "Connection removed successfully", "connections": connections}
