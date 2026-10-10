from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_tenant_id, verify_auth
from app.services.chat_service import chat_service
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question grounded in authorized documents"
)
async def chat_endpoint(
    request: ChatRequest,
    tenant_id: str = Depends(get_tenant_id),
    _: Optional[str] = Depends(verify_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Executes the 7-step LangGraph Agent workflow:
    1. Validation & prompt injection check
    2. Tenant-authorized pgvector similarity retrieval
    3. Retrieval quality evaluation
    4. Optional bounded query refinement
    5. Grounded Bedrock answer generation
    6. Citation verification
    7. Formatted response with latency and token metrics
    """
    response = await chat_service.process_chat(
        tenant_id=tenant_id,
        message=request.message,
        conversation_id=request.conversation_id,
        document_ids=request.document_ids,
        db=db
    )
    return response
