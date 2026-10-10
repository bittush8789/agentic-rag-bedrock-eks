from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class Citation(BaseModel):
    chunk_id: str = Field(..., description="Unique chunk ID referenced")
    document_id: str = Field(..., description="Document ID referenced")
    document_name: str = Field(..., description="Original filename")
    page_number: Optional[int] = Field(default=None, description="Page number in original document")
    chunk_index: Optional[int] = Field(default=None, description="Sequential chunk index")
    snippet: Optional[str] = Field(default=None, description="Excerpt of ground truth evidence")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="User prompt/question")
    conversation_id: Optional[str] = Field(default=None, description="Optional existing conversation ID")
    document_ids: Optional[List[str]] = Field(default=None, description="Optional filter to specific document IDs")


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    citations: Optional[List[Citation]] = None
    created_at: datetime


class ChatResponseMeta(BaseModel):
    latency_ms: int
    tokens_used: int
    model_id: str
    retrieval_count: int
    refined_query: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    citations: List[Citation]
    meta: ChatResponseMeta
