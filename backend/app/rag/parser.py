import io
import re
from typing import List, NamedTuple, Optional
from pypdf import PdfReader
from app.core.logging import logger


class ParsedPage(NamedTuple):
    page_number: int
    text: str


def sanitize_text(text: str) -> str:
    """Removes null bytes and cleans up excessive whitespace."""
    if not text:
        return ""
    # Strip null bytes
    clean = text.replace("\x00", "")
    # Normalize unicode whitespace
    clean = re.sub(r"[ \t]+", " ", clean)
    # Normalize multiple newlines
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()


def parse_pdf_bytes(content: bytes) -> List[ParsedPage]:
    """Extracts text per page from PDF bytes."""
    pages = []
    try:
        reader = PdfReader(io.BytesIO(content))
        for idx, page in enumerate(reader.pages):
            raw_text = page.extract_text() or ""
            cleaned = sanitize_text(raw_text)
            if cleaned:
                pages.append(ParsedPage(page_number=idx + 1, text=cleaned))
    except Exception as e:
        logger.error(f"Failed to parse PDF document: {e}")
        raise ValueError(f"Could not parse PDF content: {str(e)}")
    return pages


def parse_txt_bytes(content: bytes) -> List[ParsedPage]:
    """Extracts text from plain text bytes with encoding detection fallback."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            text = content.decode(encoding)
            cleaned = sanitize_text(text)
            if cleaned:
                return [ParsedPage(page_number=1, text=cleaned)]
            return []
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not decode TXT document with supported character encodings.")


def parse_document(filename: str, content: bytes) -> List[ParsedPage]:
    """Dispatches document parsing based on filename extension."""
    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        return parse_pdf_bytes(content)
    elif lower_name.endswith(".txt"):
        return parse_txt_bytes(content)
    else:
        raise ValueError(f"Unsupported file format for '{filename}'. Allowed: PDF, TXT.")
