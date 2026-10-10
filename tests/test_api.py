import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_and_readiness_endpoints(client: AsyncClient):
    # Liveness
    resp_liveness = await client.get("/health")
    assert resp_liveness.status_code == 200
    data = resp_liveness.json()
    assert data["status"] == "healthy"

    # Readiness
    resp_readiness = await client.get("/ready")
    assert resp_readiness.status_code == 200
    data = resp_readiness.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_document_lifecycle_and_agentic_chat(client: AsyncClient):
    tenant_headers = {"X-Tenant-ID": "tenant-alpha"}

    # 1. Upload Document
    doc_content = (
        b"Amazon Elastic Kubernetes Service (Amazon EKS) is a managed container service to run Kubernetes on AWS.\n\n"
        b"EKS automatically manages the availability and scalability of the Kubernetes control plane nodes.\n\n"
        b"With AWS Bedrock, generative AI models like Claude and Titan can be called securely without managing GPUs."
    )
    files = {"file": ("eks_guide.txt", doc_content, "text/plain")}

    upload_resp = await client.post("/api/v1/documents", headers=tenant_headers, files=files)
    assert upload_resp.status_code == 202
    upload_data = upload_resp.json()
    doc_id = upload_data["document_id"]
    assert doc_id is not None
    assert upload_data["filename"] == "eks_guide.txt"

    # 2. Get Document Status
    get_doc_resp = await client.get(f"/api/v1/documents/{doc_id}", headers=tenant_headers)
    assert get_doc_resp.status_code == 200
    doc_data = get_doc_resp.json()
    assert doc_data["status"] == "READY"
    assert doc_data["chunk_count"] > 0

    # 3. List Documents
    list_resp = await client.get("/api/v1/documents", headers=tenant_headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(d["id"] == doc_id for d in list_data["documents"])

    # 4. Agentic Chat Query
    chat_payload = {
        "message": "What is Amazon EKS and how does it manage control plane nodes?",
        "conversation_id": None
    }
    chat_resp = await client.post("/api/v1/chat", headers=tenant_headers, json=chat_payload)
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()

    assert "conversation_id" in chat_data
    convo_id = chat_data["conversation_id"]
    assert len(chat_data["answer"]) > 0
    assert len(chat_data["citations"]) >= 1
    assert chat_data["meta"]["retrieval_count"] >= 1

    # 5. Fetch Conversation History
    convo_resp = await client.get(f"/api/v1/conversations/{convo_id}", headers=tenant_headers)
    assert convo_resp.status_code == 200
    convo_data = convo_resp.json()
    assert len(convo_data["messages"]) >= 2  # user + assistant

    # 6. Tenant Isolation Verification
    # Tenant Beta should NOT see Tenant Alpha's document
    other_tenant_headers = {"X-Tenant-ID": "tenant-beta"}
    beta_list_resp = await client.get("/api/v1/documents", headers=other_tenant_headers)
    assert beta_list_resp.status_code == 200
    beta_data = beta_list_resp.json()
    assert not any(d["id"] == doc_id for d in beta_data["documents"])

    beta_get_doc = await client.get(f"/api/v1/documents/{doc_id}", headers=other_tenant_headers)
    assert beta_get_doc.status_code == 404

    # 7. Delete Document
    del_resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=tenant_headers)
    assert del_resp.status_code == 204

    # Verify document is gone
    del_check = await client.get(f"/api/v1/documents/{doc_id}", headers=tenant_headers)
    assert del_check.status_code == 404
