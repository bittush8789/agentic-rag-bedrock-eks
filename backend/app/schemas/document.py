from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    filename: str
    content_type: str
    file_size: int
    status: str
    chunk_count: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    document_id: str = Field(..., description="Unique document ID")
    job_id: str = Field(..., description="Asynchronous ingestion job ID")
    status: str = Field(..., description="Ingestion processing status (QUEUED)")
    filename: str = Field(..., description="Sanitized uploaded filename")
    file_size: int = Field(..., description="File size in bytes")
    message: str = Field(default="Document accepted and queued for processing")


class DocumentListResponse(BaseModel):
    documents: List[DocumentRead]
    total: int
    limit: int
    offset: int
