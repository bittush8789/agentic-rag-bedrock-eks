import pytest
from app.rag.chunker import recursive_split_text, chunk_parsed_pages
from app.rag.parser import ParsedPage


def test_recursive_split_text_small():
    text = "Short text under limit."
    chunks = recursive_split_text(text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_recursive_split_text_paragraphs():
    p1 = "First paragraph with details about AWS EKS and Kubernetes."
    p2 = "Second paragraph about Amazon Bedrock and LangGraph agent workflow."
    text = f"{p1}\n\n{p2}"
    chunks = recursive_split_text(text, chunk_size=60, chunk_overlap=15)
    assert len(chunks) >= 2
    assert "AWS EKS" in chunks[0]
    assert any("Amazon Bedrock" in c for c in chunks)


def test_chunk_parsed_pages_preserves_page_numbers():
    pages = [
        ParsedPage(page_number=1, text="Page 1 has confidential policies."),
        ParsedPage(page_number=2, text="Page 2 defines multi-tenant vector storage.")
    ]
    chunks = chunk_parsed_pages(pages, chunk_size=40, chunk_overlap=10)
    assert len(chunks) >= 2
    assert chunks[0].page_number == 1
    assert chunks[-1].page_number == 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
