import traceback
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.document import Document, DocumentStatus
from app.models.chunk import Chunk
from app.models.job import IngestionJob
from app.models.audit import AuditEvent
from app.rag.parser import parse_document
from app.rag.chunker import chunk_parsed_pages
from app.rag.bedrock import bedrock_client
from app.services.storage import storage_service
from app.core.logging import logger


async def process_document_ingestion(document_id: str, db: AsyncSession):
    """
    Executes idempotent end-to-end document parsing, chunking, embedding,
    and storage in pgvector.
    """
    logger.info(f"Starting ingestion workflow for document: {document_id}")

    # Fetch document
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        logger.error(f"Ingestion failed: Document {document_id} not found.")
        return

    # Update status to PROCESSING
    doc.status = DocumentStatus.PROCESSING.value
    await db.execute(
        update(IngestionJob)
        .where(IngestionJob.document_id == document_id)
        .values(status=DocumentStatus.PROCESSING.value, attempts=IngestionJob.attempts + 1)
    )
    await db.commit()

    try:
        # 1. Fetch raw bytes from storage
        file_bytes = await storage_service.get_file(doc.s3_key)

        # 2. Parse text and page numbers
        parsed_pages = parse_document(doc.filename, file_bytes)
        if not parsed_pages:
            raise ValueError("No extractable text found in uploaded document.")

        # 3. Chunk text recursively with overlap
        chunks = chunk_parsed_pages(parsed_pages)
        if not chunks:
            raise ValueError("Document yielded 0 valid text chunks.")

        # 4. Generate embeddings and create Chunk entities
        chunk_entities = []
        for c in chunks:
            embedding = await bedrock_client.get_embedding(c.content)
            chunk_obj = Chunk(
                document_id=doc.id,
                tenant_id=doc.tenant_id,
                chunk_index=c.chunk_index,
                content=c.content,
                embedding=embedding,
                page_number=c.page_number,
                token_count=c.token_count
            )
            chunk_entities.append(chunk_obj)

        # 5. Persist chunks in DB
        db.add_all(chunk_entities)

        # 6. Update document and job status
        doc.status = DocumentStatus.READY.value
        doc.chunk_count = len(chunk_entities)
        doc.error_message = None

        await db.execute(
            update(IngestionJob)
            .where(IngestionJob.document_id == document_id)
            .values(status=DocumentStatus.READY.value, error_message=None)
        )

        # 7. Audit log
        audit = AuditEvent(
            tenant_id=doc.tenant_id,
            actor="ingestion-worker",
            action="DOCUMENT_INGESTION_COMPLETED",
            resource_type="document",
            resource_id=doc.id,
            details={"chunk_count": len(chunk_entities), "filename": doc.filename}
        )
        db.add(audit)
        await db.commit()

        logger.info(f"Document {document_id} ingestion succeeded with {len(chunk_entities)} chunks.")

    except Exception as e:
        await db.rollback()
        err_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Ingestion error on document {document_id}: {err_msg}\n{traceback.format_exc()}")

        # Update failure status
        doc.status = DocumentStatus.FAILED.value
        doc.error_message = err_msg[:1000]

        await db.execute(
            update(IngestionJob)
            .where(IngestionJob.document_id == document_id)
            .values(status=DocumentStatus.FAILED.value, error_message=err_msg[:1000])
        )
        await db.commit()
