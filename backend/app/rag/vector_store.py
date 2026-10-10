import math
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.chunk import Chunk
from app.models.document import Document
from app.core.config import settings
from app.core.logging import logger


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def search_similar_chunks(
    db: AsyncSession,
    tenant_id: str,
    query_embedding: List[float],
    top_k: Optional[int] = None,
    threshold: Optional[float] = None,
    document_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Performs tenant-isolated vector similarity search.
    On PostgreSQL: executes pgvector cosine distance query.
    On SQLite: retrieves candidate tenant chunks and calculates cosine similarity.
    """
    k = top_k or settings.TOP_K_RETRIEVAL
    min_score = threshold if threshold is not None else settings.SIMILARITY_THRESHOLD

    bind = db.bind
    dialect_name = bind.dialect.name if bind else "sqlite"

    query = (
        select(Chunk, Document.filename)
        .join(Document, Chunk.document_id == Document.id)
        .where(
            Chunk.tenant_id == tenant_id,
            Document.status == "READY"
        )
    )

    if document_ids:
        query = query.where(Chunk.document_id.in_(document_ids))

    if dialect_name == "postgresql":
        # Native pgvector cosine distance
        distance_col = Chunk.embedding.cosine_distance(query_embedding)
        query = query.order_by(distance_col).limit(k)

        result = await db.execute(query)
        rows = result.all()

        results = []
        for chunk, filename in rows:
            score = cosine_similarity(query_embedding, chunk.embedding)
            if score >= min_score:
                results.append({
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "document_name": filename,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "score": round(score, 4)
                })
        return results
    else:
        # SQLite / Local fallback mode
        result = await db.execute(query)
        rows = result.all()

        scored_chunks = []
        for chunk, filename in rows:
            if not chunk.embedding:
                continue
            sim = cosine_similarity(query_embedding, chunk.embedding)
            if sim >= min_score:
                scored_chunks.append({
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "document_name": filename,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "score": round(sim, 4)
                })

        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:k]
