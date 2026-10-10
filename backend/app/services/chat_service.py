import uuid
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message
from app.models.audit import AuditEvent
from app.schemas.chat import ChatResponse, ChatResponseMeta, Citation
from app.rag.agent import run_agentic_rag
from app.core.config import settings
from app.core.logging import logger


class ChatService:
    async def process_chat(
        self,
        tenant_id: str,
        message: str,
        conversation_id: Optional[str],
        document_ids: Optional[List[str]],
        db: AsyncSession
    ) -> ChatResponse:
        """Manages conversation state and executes LangGraph agent workflow."""
        convo = None
        if conversation_id:
            convo_res = await db.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.tenant_id == tenant_id
                )
            )
            convo = convo_res.scalar_one_or_none()
            if not convo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found or unauthorized."
                )
        else:
            # Create new conversation
            title = message[:40] + ("..." if len(message) > 40 else "")
            convo = Conversation(
                tenant_id=tenant_id,
                title=title
            )
            db.add(convo)
            await db.flush()

        # Save user message
        user_msg = Message(
            conversation_id=convo.id,
            role="user",
            content=message
        )
        db.add(user_msg)

        # Retrieve recent history for context
        hist_query = (
            select(Message)
            .where(Message.conversation_id == convo.id)
            .order_by(desc(Message.created_at))
            .limit(6)
        )
        hist_rows = (await db.execute(hist_query)).scalars().all()
        history = [{"role": m.role, "content": m.content} for m in reversed(list(hist_rows))]

        # Run agentic RAG workflow
        agent_output = await run_agentic_rag(
            db=db,
            tenant_id=tenant_id,
            user_message=message,
            document_ids=document_ids,
            conversation_history=history
        )

        # Persist assistant response
        citations_data = [
            c.model_dump() if hasattr(c, "model_dump") else c
            for c in agent_output.get("citations", [])
        ]
        assistant_msg = Message(
            conversation_id=convo.id,
            role="assistant",
            content=agent_output["answer"],
            citations=citations_data
        )
        db.add(assistant_msg)

        # Audit event
        audit = AuditEvent(
            tenant_id=tenant_id,
            actor="chat-user",
            action="CHAT_QUERY_EXECUTED",
            resource_type="conversation",
            resource_id=convo.id,
            details={
                "latency_ms": agent_output.get("latency_ms", 0),
                "tokens_used": agent_output.get("tokens_used", 0),
                "citation_count": len(citations_data)
            }
        )
        db.add(audit)
        await db.commit()

        # Build schema response
        citations_list = [
            Citation(**c) if isinstance(c, dict) else c
            for c in citations_data
        ]

        meta = ChatResponseMeta(
            latency_ms=agent_output.get("latency_ms", 0),
            tokens_used=agent_output.get("tokens_used", 0),
            model_id=settings.BEDROCK_GENERATION_MODEL_ID,
            retrieval_count=len(agent_output.get("retrieved_chunks", [])),
            refined_query=agent_output.get("refined_query")
        )

        return ChatResponse(
            conversation_id=convo.id,
            answer=agent_output["answer"],
            citations=citations_list,
            meta=meta
        )

    async def list_conversations(
        self,
        tenant_id: str,
        limit: int,
        offset: int,
        db: AsyncSession
    ) -> Tuple[List[Conversation], int]:
        """Lists conversations for the tenant."""
        from sqlalchemy import func
        count_q = select(func.count(Conversation.id)).where(Conversation.tenant_id == tenant_id)
        total = (await db.execute(count_q)).scalar() or 0

        query = (
            select(Conversation)
            .where(Conversation.tenant_id == tenant_id)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        return list(result.scalars().all()), total

    async def get_conversation(
        self,
        tenant_id: str,
        conversation_id: str,
        db: AsyncSession
    ) -> Conversation:
        """Retrieves a conversation with messages."""
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id
            )
        )
        result = await db.execute(query)
        convo = result.scalar_one_or_none()
        if not convo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        return convo


chat_service = ChatService()
