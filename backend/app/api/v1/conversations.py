from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_tenant_id, verify_auth
from app.services.chat_service import chat_service
from app.schemas.conversation import ConversationRead, ConversationListResponse, ConversationDetailResponse
from app.schemas.chat import MessageRead

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="List conversations for authenticated tenant"
)
async def list_conversations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant_id: str = Depends(get_tenant_id),
    _: Optional[str] = Depends(verify_auth),
    db: AsyncSession = Depends(get_db)
):
    """Lists conversations associated with the current tenant."""
    convos, total = await chat_service.list_conversations(
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
        db=db
    )
    return ConversationListResponse(
        conversations=[ConversationRead.model_validate(c) for c in convos],
        total=total
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation history and messages"
)
async def get_conversation(
    conversation_id: str,
    tenant_id: str = Depends(get_tenant_id),
    _: Optional[str] = Depends(verify_auth),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves conversation thread with all user and assistant messages."""
    convo = await chat_service.get_conversation(tenant_id, conversation_id, db)
    return ConversationDetailResponse(
        id=convo.id,
        tenant_id=convo.tenant_id,
        title=convo.title,
        messages=[MessageRead.model_validate(m) for m in convo.messages],
        created_at=convo.created_at,
        updated_at=convo.updated_at
    )
