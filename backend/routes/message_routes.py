from fastapi import APIRouter, Depends, HTTPException

from ..models import message as message_model
from ..models import user as user_model
from ..schemas.message_schema import MessageCreate, MessageResponse
from ..utils.dependencies import get_current_user

router = APIRouter()


def db_message_to_public(db_message: dict) -> MessageResponse:
    """Convert MongoDB message document to MessageResponse with string IDs."""
    return MessageResponse(
        id=str(db_message.get("_id") or db_message.get("id")),
        sender_id=str(db_message.get("sender_id")),
        receiver_id=str(db_message.get("receiver_id")),
        content=db_message.get("content"),
        created_at=db_message.get("created_at"),
        read=db_message.get("read", False),
    )


@router.post("/", response_model=MessageResponse)
async def send_message(
    payload: MessageCreate, current_user=Depends(get_current_user)
):
    receiver = await user_model.get_user_by_id(payload.receiver_id)
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")
    doc = await message_model.send_message(
        str(current_user["_id"]), payload.receiver_id, payload.content
    )
    return db_message_to_public(doc)


@router.get("/conversation/{other_user_id}", response_model=list[MessageResponse])
async def conversation(other_user_id: str, current_user=Depends(get_current_user)):
    other = await user_model.get_user_by_id(other_user_id)
    if not other:
        raise HTTPException(status_code=404, detail="User not found")
    messages = await message_model.conversation(str(current_user["_id"]), other_user_id)
    return [db_message_to_public(msg) for msg in messages]


