import pytest
from app.rag.citations import extract_and_validate_citations


def test_extract_valid_citations():
    context_chunks = [
        {
            "id": "chunk-101",
            "document_id": "doc-01",
            "document_name": "kubernetes-guide.pdf",
            "page_number": 4,
            "chunk_index": 0,
            "content": "EKS Managed node groups handle Amazon EC2 provisioning automatically."
        },
        {
            "id": "chunk-102",
            "document_id": "doc-01",
            "document_name": "kubernetes-guide.pdf",
            "page_number": 5,
            "chunk_index": 1,
            "content": "Pod Identity provides IAM credentials directly to service accounts."
        }
    ]

    raw_answer = (
        "Node groups automate EC2 instances [Chunk chunk-101]. "
        "Pod Identity secures credentials [Chunk chunk-102]."
    )

    cleaned_answer, citations = extract_and_validate_citations(raw_answer, context_chunks)

    assert len(citations) == 2
    assert citations[0].chunk_id == "chunk-101"
    assert citations[0].page_number == 4
    assert citations[1].chunk_id == "chunk-102"
    assert citations[1].page_number == 5
    assert "[Chunk chunk-101]" not in cleaned_answer


def test_filters_hallucinated_citations():
    context_chunks = [
        {
            "id": "real-chunk",
            "document_id": "doc-01",
            "document_name": "real-doc.txt",
            "page_number": 1,
            "chunk_index": 0,
            "content": "This is real evidence."
        }
    ]

    raw_answer = "This claims something [Chunk hallucinated-fake-id]."
    cleaned_answer, citations = extract_and_validate_citations(raw_answer, context_chunks)

    assert len(citations) == 0
    assert "[Chunk hallucinated-fake-id]" not in cleaned_answer
