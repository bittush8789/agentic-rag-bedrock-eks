from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_tenant_id, verify_auth
from app.services.document_service import document_service
from app.schemas.document import DocumentRead, DocumentListResponse, DocumentUploadResponse

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload document for asynchronous ingestion"
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF or TXT document file"),
    tenant_id: str = Depends(get_tenant_id),
    _: Optional[str] = Depends(verify_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Accepts a PDF or TXT file, computes checksum, persists raw content,
    and queues an ingestion job for chunking and embedding generation.
    """
    content = await file.read()
    doc, job = await document_service.create_document(
        tenant_id=tenant_id,
        filename=file.filename or "uploaded_file.txt",
        content=content,
        content_type=file.content_type or "application/octet-stream",
        background_tasks=background_tasks,
        db=db
    )
    return DocumentUploadResponse(
        document_id=doc.id,
        job_id=job.id,
        status=doc.status,
        filename=doc.filename,
        file_size=doc.file_size
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all tenant documents"
)
async def list_documents(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant_id: str = Depends(get_tenant_id),
    _: Optional[str] = Depends(verify_auth),
    db: AsyncSession = Depends(get_db)
):
    """Returns paginated documents belonging to the authenticated tenant."""
    docs, total = await document_service.list_documents(
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
        db=db
    )
    return DocumentListResponse(
        documents=[DocumentRead.model_validate(d) for d in docs],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get(
    "/{document_id}",
    response_model=DocumentRead,
    summary="Get document details and processing status"
)
async def get_document(
    document_id: str,
    tenant_id: str = Depends(get_tenant_id),
    _: Optional[str] = Depends(verify_auth),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves document details and status (QUEUED, PROCESSING, READY, FAILED)."""
    doc = await document_service.get_document(tenant_id, document_id, db)
    return DocumentRead.model_validate(doc)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document and its chunk vectors"
)
async def delete_document(
    document_id: str,
    tenant_id: str = Depends(get_tenant_id),
    _: Optional[str] = Depends(verify_auth),
    db: AsyncSession = Depends(get_db)
):
    """Deletes the document, all related pgvector chunks, and raw storage objects."""
    await document_service.delete_document(tenant_id, document_id, db)
    return None
