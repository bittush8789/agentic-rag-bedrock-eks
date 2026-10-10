import re
from typing import List, Dict, Any, Tuple
from app.schemas.chat import Citation
from app.core.logging import logger


def extract_and_validate_citations(
    raw_answer: str,
    context_chunks: List[Dict[str, Any]]
) -> Tuple[str, List[Citation]]:
    """
    Validates that model citations strictly reference retrieved ground-truth chunks.
    Filters out any hallucinated references.
    """
    if not context_chunks:
        return raw_answer, []

    chunk_map = {chunk["id"]: chunk for chunk in context_chunks}
    valid_citations: List[Citation] = []
    seen_chunk_ids = set()

    # Pattern 1: [Chunk <uuid-or-id>]
    chunk_pattern = re.compile(r"\[Chunk\s+([a-zA-Z0-9_-]+)\]", re.IGNORECASE)
    matches = chunk_pattern.findall(raw_answer)

    for cid in matches:
        if cid in chunk_map and cid not in seen_chunk_ids:
            seen_chunk_ids.add(cid)
            chunk = chunk_map[cid]
            snippet = chunk.get("content", "")[:160].strip()
            valid_citations.append(
                Citation(
                    chunk_id=chunk["id"],
                    document_id=chunk["document_id"],
                    document_name=chunk.get("document_name", "Document"),
                    page_number=chunk.get("page_number"),
                    chunk_index=chunk.get("chunk_index"),
                    snippet=snippet
                )
            )

    # Pattern 2: [Doc: <name>, Page <num>] or numerical references [1], [2]
    num_pattern = re.compile(r"\[(\d+)\]")
    num_matches = num_pattern.findall(raw_answer)
    for n_str in num_matches:
        idx = int(n_str) - 1
        if 0 <= idx < len(context_chunks):
            chunk = context_chunks[idx]
            if chunk["id"] not in seen_chunk_ids:
                seen_chunk_ids.add(chunk["id"])
                snippet = chunk.get("content", "")[:160].strip()
                valid_citations.append(
                    Citation(
                        chunk_id=chunk["id"],
                        document_id=chunk["document_id"],
                        document_name=chunk.get("document_name", "Document"),
                        page_number=chunk.get("page_number"),
                        chunk_index=chunk.get("chunk_index"),
                        snippet=snippet
                    )
                )

    # If the model produced a grounded answer citing document names without explicit ID markers,
    # match against top retrieved chunks if relevance is high
    if not valid_citations and context_chunks:
        for chunk in context_chunks[:2]:
            doc_name = chunk.get("document_name", "")
            if doc_name and doc_name.lower() in raw_answer.lower():
                if chunk["id"] not in seen_chunk_ids:
                    seen_chunk_ids.add(chunk["id"])
                    valid_citations.append(
                        Citation(
                            chunk_id=chunk["id"],
                            document_id=chunk["document_id"],
                            document_name=doc_name,
                            page_number=chunk.get("page_number"),
                            chunk_index=chunk.get("chunk_index"),
                            snippet=chunk.get("content", "")[:160].strip()
                        )
                    )

    # Clean up raw chunk IDs in the answer for human presentation
    cleaned_answer = raw_answer
    for cid in matches:
        if cid in chunk_map:
            chunk = chunk_map[cid]
            p_str = f", p.{chunk['page_number']}" if chunk.get("page_number") else ""
            cleaned_answer = cleaned_answer.replace(f"[Chunk {cid}]", f"[{chunk['document_name']}{p_str}]")
        else:
            # Strip hallucinated chunk references
            cleaned_answer = cleaned_answer.replace(f"[Chunk {cid}]", "")

    return cleaned_answer.strip(), valid_citations
