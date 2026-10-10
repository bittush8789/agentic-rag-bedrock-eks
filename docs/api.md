# REST API Specification (v1)

Base URL: `/api/v1`  
Protocol: `HTTPS`  
Authentication: Optional Bearer token via `Authorization: Bearer <token>`  
Tenant Context: Required `X-Tenant-ID: <tenant_id>` (defaults to `tenant-default` in development)  
Correlation Header: `X-Request-ID: <uuid>` (returned in all responses)

---

## 1. Document Management Endpoints

### 1.1 Upload Document
- **Endpoint**: `POST /api/v1/documents`
- **Content-Type**: `multipart/form-data`
- **Status Code**: `202 Accepted`
- **Parameters**:
  - `file`: Binary file data (.pdf or .txt, max 25 MB)
- **Headers**:
  - `X-Tenant-ID`: string (e.g. `tenant-acme`)
- **Response**:
```json
{
  "document_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "job_id": "4e7a892b-8a9d-43c2-8495-201947b19283",
  "status": "QUEUED",
  "filename": "annual_financial_report.pdf",
  "file_size": 2490150,
  "message": "Document accepted and queued for processing"
}
```

### 1.2 List Documents
- **Endpoint**: `GET /api/v1/documents`
- **Query Parameters**:
  - `limit`: int (default `20`, max `100`)
  - `offset`: int (default `0`)
- **Status Code**: `200 OK`
- **Response**:
```json
{
  "documents": [
    {
      "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "tenant_id": "tenant-acme",
      "filename": "annual_financial_report.pdf",
      "content_type": "application/pdf",
      "file_size": 2490150,
      "status": "READY",
      "chunk_count": 42,
      "error_message": null,
      "created_at": "2026-10-10T12:00:00Z",
      "updated_at": "2026-10-10T12:00:45Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

### 1.3 Get Document Details
- **Endpoint**: `GET /api/v1/documents/{document_id}`
- **Status Code**: `200 OK` (or `404 Not Found`)

### 1.4 Delete Document
- **Endpoint**: `DELETE /api/v1/documents/{document_id}`
- **Status Code**: `204 No Content`
- **Behavior**: Cascades deletion across document record, raw S3 object, and all related pgvector chunks.

---

## 2. Agentic Chat & Retrieval Endpoints

### 2.1 Ask a Question
- **Endpoint**: `POST /api/v1/chat`
- **Content-Type**: `application/json`
- **Status Code**: `200 OK`
- **Request Body**:
```json
{
  "message": "What was the total operating revenue reported in Q3?",
  "conversation_id": "optional-uuid-to-continue-conversation",
  "document_ids": ["optional-filter-document-uuid"]
}
```
- **Response Body**:
```json
{
  "conversation_id": "6ddbc480-76da-4a5e-b06c-a1e14b2f88f6",
  "answer": "Operating revenue for Q3 totaled $14.2 billion, representing a 12% year-over-year increase [annual_financial_report.pdf, p.4].",
  "citations": [
    {
      "chunk_id": "c71a39f0-32b5-419b-8bc1-6fbb2944b029",
      "document_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "document_name": "annual_financial_report.pdf",
      "page_number": 4,
      "chunk_index": 7,
      "snippet": "Operating revenue for the third quarter was $14,200 million compared to $12,680 million in the prior period."
    }
  ],
  "meta": {
    "latency_ms": 640,
    "tokens_used": 185,
    "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
    "retrieval_count": 4,
    "refined_query": null
  }
}
```

---

## 3. Conversation Management Endpoints

### 3.1 List Conversations
- **Endpoint**: `GET /api/v1/conversations`
- **Status Code**: `200 OK`

### 3.2 Get Conversation Thread
- **Endpoint**: `GET /api/v1/conversations/{conversation_id}`
- **Status Code**: `200 OK` (returns full thread history with messages and citations)

---

## 4. Health & Readiness Probes

### 4.1 Liveness Probe
- **Endpoint**: `GET /health`
- **Status Code**: `200 OK`

### 4.2 Readiness Probe
- **Endpoint**: `GET /ready`
- **Status Code**: `200 OK` if PostgreSQL is reachable; `503 Service Unavailable` if database connection fails.
