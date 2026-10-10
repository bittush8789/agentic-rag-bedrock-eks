import os
import sys
from pathlib import Path

# Add backend directory to path if run directly
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.db.session import AsyncSessionLocal
from app.services.ingestion import process_document_ingestion
from app.core.logging import logger


async def execute_ingestion_task(document_id: str, tenant_id: str) -> bool:
    """Executes asynchronous document parsing, chunking, and vector embedding."""
    logger.info(f"[WORKER] Starting ingestion job for document: {document_id} (tenant: {tenant_id})")
    async with AsyncSessionLocal() as session:
        try:
            await process_document_ingestion(document_id, session)
            logger.info(f"[WORKER] Ingestion completed successfully for {document_id}")
            return True
        except Exception as e:
            logger.error(f"[WORKER] Ingestion task failed for {document_id}: {e}")
            return False
