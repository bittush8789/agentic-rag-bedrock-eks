import hashlib
import uuid
import json
import boto3
from typing import List, Tuple, Optional
from fastapi import HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.document import Document, DocumentStatus
from app.models.job import IngestionJob
from app.models.audit import AuditEvent
from app.services.storage import storage_service
from app.services.ingestion import process_document_ingestion
from app.db.session import AsyncSessionLocal
from app.core.config import settings
from app.core.logging import logger


async def run_inline_ingestion(document_id: str):
    """Background task runner for inline local execution."""
    async with AsyncSessionLocal() as session:
        await process_document_ingestion(document_id, session)


def publish_to_sqs(document_id: str, tenant_id: str):
    """Publishes ingestion task to SQS for worker pods."""
    if not settings.SQS_QUEUE_URL:
        logger.warning("SQS_QUEUE_URL not configured. Cannot enqueue to SQS.")
        return
    try:
        sqs = boto3.client("sqs", region_name=settings.AWS_REGION)
        message_body = json.dumps({
            "document_id": document_id,
            "tenant_id": tenant_id,
            "action": "INGEST_DOCUMENT"
        })
        sqs.send_message(
            QueueUrl=settings.SQS_QUEUE_URL,
            MessageBody=message_body
        )
        logger.info(f"Published ingestion job for {document_id} to SQS.")
    except Exception as e:
        logger.error(f"Failed to publish to SQS: {e}")
        raise


class DocumentService:
    async def create_document(
        self,
        tenant_id: str,
        filename: str,
        content: bytes,
        content_type: str,
        background_tasks: Optional[BackgroundTasks],
        db: AsyncSession
    ) -> Tuple[Document, IngestionJob]:
        """Orchestrates document acceptance, validation, storage, and asynchronous job queuing."""
        # 1. Validate file extension
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Allowed extensions: {settings.ALLOWED_EXTENSIONS}"
            )

        # 2. Validate file size
        if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum permitted size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB."
            )

        # 3. Compute SHA256 checksum
        checksum = hashlib.sha256(content).hexdigest()

        # 4. Check for duplicate upload within tenant
        dup_query = select(Document).where(
            Document.tenant_id == tenant_id,
            Document.sha256_checksum == checksum,
            Document.status == DocumentStatus.READY.value
        )
        dup_result = await db.execute(dup_query)
        existing_doc = dup_result.scalar_one_or_none()
        if existing_doc:
            logger.info(f"Duplicate document detected for tenant {tenant_id} with checksum {checksum}. Returning existing document.")
            # Fetch existing job
            job_query = select(IngestionJob).where(IngestionJob.document_id == existing_doc.id)
            job_res = await db.execute(job_query)
            existing_job = job_res.scalar_one_or_none()
            if not existing_job:
                existing_job = IngestionJob(
                    document_id=existing_doc.id,
                    tenant_id=tenant_id,
                    status=DocumentStatus.READY.value
                )
                db.add(existing_job)
                await db.commit()
            return existing_doc, existing_job

        # 5. Persist raw file to storage
        doc_id = str(uuid.uuid4())
        safe_filename = filename.replace(" ", "_")
        storage_key = f"{tenant_id}/{doc_id}/{safe_filename}"
        await storage_service.save_file(storage_key, content, content_type)

        # 6. Create Document record
        doc = Document(
            id=doc_id,
            tenant_id=tenant_id,
            filename=filename,
            content_type=content_type,
            file_size=len(content),
            s3_key=storage_key,
            sha256_checksum=checksum,
            status=DocumentStatus.QUEUED.value,
            chunk_count=0
        )
        db.add(doc)

        # 7. Create IngestionJob record
        job = IngestionJob(
            document_id=doc_id,
            tenant_id=tenant_id,
            status=DocumentStatus.QUEUED.value,
            attempts=0
        )
        db.add(job)

        # 8. Audit event
        audit = AuditEvent(
            tenant_id=tenant_id,
            actor="api-user",
            action="DOCUMENT_UPLOADED",
            resource_type="document",
            resource_id=doc_id,
            details={"filename": filename, "file_size": len(content)}
        )
        db.add(audit)
        await db.commit()
        await db.refresh(doc)
        await db.refresh(job)

        # 9. Trigger async processing
        if settings.ASYNC_PROCESSING_MODE == "sqs" and settings.SQS_QUEUE_URL:
            publish_to_sqs(doc_id, tenant_id)
        elif background_tasks:
            background_tasks.add_task(run_inline_ingestion, doc_id)
        else:
            # Fallback inline processing
            await process_document_ingestion(doc_id, db)

        return doc, job

    async def list_documents(
        self,
        tenant_id: str,
        limit: int,
        offset: int,
        db: AsyncSession
    ) -> Tuple[List[Document], int]:
        """Lists tenant documents with pagination."""
        count_query = select(func.count(Document.id)).where(Document.tenant_id == tenant_id)
        total = (await db.execute(count_query)).scalar() or 0

        query = (
            select(Document)
            .where(Document.tenant_id == tenant_id)
            .order_by(desc(Document.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        docs = list(result.scalars().all())
        return docs, total

    async def get_document(self, tenant_id: str, document_id: str, db: AsyncSession) -> Document:
        """Retrieves single document with tenant authorization."""
        query = select(Document).where(Document.id == document_id, Document.tenant_id == tenant_id)
        result = await db.execute(query)
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found."
            )
        return doc

    async def delete_document(self, tenant_id: str, document_id: str, db: AsyncSession) -> None:
        """Deletes document, chunks, and storage object safely."""
        doc = await self.get_document(tenant_id, document_id, db)

        # Remove from storage
        try:
            await storage_service.delete_file(doc.s3_key)
        except Exception as e:
            logger.warning(f"Error deleting storage file: {e}")

        # Delete from DB
        await db.delete(doc)

        audit = AuditEvent(
            tenant_id=tenant_id,
            actor="api-user",
            action="DOCUMENT_DELETED",
            resource_type="document",
            resource_id=document_id,
            details={"filename": doc.filename}
        )
        db.add(audit)
        await db.commit()


document_service = DocumentService()
