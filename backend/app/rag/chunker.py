from typing import List, NamedTuple, Optional
from app.rag.parser import ParsedPage
from app.core.config import settings


class ChunkPayload(NamedTuple):
    chunk_index: int
    content: str
    page_number: Optional[int]
    token_count: int


def recursive_split_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: Optional[List[str]] = None
) -> List[str]:
    """
    Recursively splits text using prioritized separators (\n\n, \n, . , space, '').
    Enforces overlap between consecutive chunks.
    """
    if separators is None:
        separators = ["\n\n", "\n", ". ", "; ", ", ", " ", ""]

    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    # Find the first separator present in the text
    sep = separators[-1]
    for s in separators:
        if s == "" or s in text:
            sep = s
            break

    splits = text.split(sep) if sep else list(text)
    chunks = []
    current_chunk = []
    current_len = 0

    for piece in splits:
        piece_len = len(piece) + (len(sep) if current_chunk else 0)
        if current_len + piece_len <= chunk_size:
            current_chunk.append(piece)
            current_len += piece_len
        else:
            if current_chunk:
                merged = sep.join(current_chunk).strip()
                if merged:
                    chunks.append(merged)
                # Form overlap from end of current_chunk
                overlap_pieces = []
                overlap_len = 0
                for rev_p in reversed(current_chunk):
                    if overlap_len + len(rev_p) <= chunk_overlap:
                        overlap_pieces.insert(0, rev_p)
                        overlap_len += len(rev_p) + len(sep)
                    else:
                        break
                current_chunk = overlap_pieces
                current_len = overlap_len
            
            # If a single piece is longer than chunk_size, recurse with next separators
            if len(piece) > chunk_size:
                next_seps = separators[separators.index(sep) + 1 :] if sep in separators else [""]
                sub_chunks = recursive_split_text(piece, chunk_size, chunk_overlap, next_seps)
                chunks.extend(sub_chunks)
                current_chunk = []
                current_len = 0
            else:
                current_chunk.append(piece)
                current_len += len(piece) + (len(sep) if current_chunk else 0)

    if current_chunk:
        merged = sep.join(current_chunk).strip()
        if merged:
            chunks.append(merged)

    return chunks


def chunk_parsed_pages(
    pages: List[ParsedPage],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
) -> List[ChunkPayload]:
    """
    Chunks a list of parsed document pages while preserving page numbers.
    """
    c_size = chunk_size or settings.CHUNK_SIZE
    c_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    all_chunks: List[ChunkPayload] = []
    chunk_index = 0

    for page in pages:
        page_chunks = recursive_split_text(page.text, c_size, c_overlap)
        for piece in page_chunks:
            if not piece.strip():
                continue
            approx_tokens = max(1, len(piece) // 4)
            all_chunks.append(
                ChunkPayload(
                    chunk_index=chunk_index,
                    content=piece,
                    page_number=page.page_number,
                    token_count=approx_tokens
                )
            )
            chunk_index += 1

    return all_chunks
