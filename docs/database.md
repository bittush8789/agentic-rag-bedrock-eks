# Database Schema & pgvector Guide

## 1. Database Architecture

The application uses **Amazon RDS for PostgreSQL 16** with the **pgvector** open-source extension.

```
+--------------------------------------------------------------------------+
|                              PostgreSQL 16                                |
|                                                                          |
|  +--------------------+        1:N         +--------------------------+  |
|  |     documents      | -----------------> |          chunks          |  |
|  | id (PK)            |                    | id (PK)                  |  |
|  | tenant_id (Index)  |                    | document_id (FK Cascades)|  |
|  | sha256_checksum    |                    | tenant_id (Index)        |  |
|  | status             |                    | embedding vector(1024)   |  |
|  +--------------------+                    | HNSW Cosine Index        |  |
|           | 1:N                            +--------------------------+  |
|           v                                                              |
|  +--------------------+                    +--------------------------+  |
|  |   ingestion_jobs   |                    |       conversations      |  |
|  | id (PK)            |                    | id (PK), tenant_id       |  |
|  | status, attempts   |                    +--------------------------+  |
|  +--------------------+                                 | 1:N            |
|                                                         v                |
|  +--------------------+                    +--------------------------+  |
|  |    audit_events    |                    |         messages         |  |
|  | id (PK), tenant_id |                    | id (PK), role, citations |  |
|  +--------------------+                    +--------------------------+  |
+--------------------------------------------------------------------------+
```

---

## 2. Table Definitions

### 2.1 `documents` Table
Stores uploaded document metadata and processing lifecycle states.
- `id` (VARCHAR(36), PK): UUID
- `tenant_id` (VARCHAR(64), Index): Multi-tenant isolation key
- `filename` (VARCHAR(255)): Original filename
- `content_type` (VARCHAR(100)): MIME type (application/pdf, text/plain)
- `file_size` (INTEGER): Size in bytes
- `s3_key` (VARCHAR(512)): S3 object storage location (`tenant/doc_id/filename`)
- `sha256_checksum` (VARCHAR(64)): Deduplication checksum
- `status` (VARCHAR(20)): `QUEUED`, `PROCESSING`, `READY`, `FAILED`
- `chunk_count` (INTEGER): Number of vector chunks created
- `created_at` / `updated_at` (TIMESTAMPTZ)
- **Indexes**:
  - `idx_doc_tenant_checksum` on `(tenant_id, sha256_checksum)`
  - `idx_doc_tenant_status` on `(tenant_id, status)`

### 2.2 `chunks` Table
Stores parsed text segments and dense vector embeddings.
- `id` (VARCHAR(36), PK): UUID
- `document_id` (VARCHAR(36), FK -> documents.id ON DELETE CASCADE)
- `tenant_id` (VARCHAR(64), Index): Enforces query partitioning
- `chunk_index` (INTEGER): Sequential position in original file
- `content` (TEXT): Text chunk payload
- `embedding` (`vector(1024)`): Dense float vector (Titan Text Embeddings V2)
- `page_number` (INTEGER): Page number in source document
- `token_count` (INTEGER): Approximate token count
- **Vector Index**:
  ```sql
  CREATE INDEX idx_chunks_embedding_hnsw ON chunks 
  USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
  ```

### 2.3 `conversations` & `messages` Tables
Maintains conversational context and verified citation history.
- `conversations.id`: UUID, `tenant_id`, `title`, timestamps
- `messages.id`: UUID, `conversation_id` (FK), `role` (user/assistant), `content`, `citations` (JSON)

### 2.4 `ingestion_jobs` Table
Tracks asynchronous processing attempts, errors, and dead-letter state.
- `id`: UUID, `document_id` (FK), `status`, `error_message`, `attempts`

### 2.5 `audit_events` Table
Captures compliance logs for sensitive user actions (uploads, deletions, queries).
- `id`: UUID, `tenant_id`, `actor`, `action`, `resource_type`, `resource_id`, `details` (JSON)

---

## 3. Database Migrations (Alembic)

Database schema migrations are version-controlled with **Alembic**:

```bash
# Apply migrations to target database
alembic upgrade head

# Generate a new migration revision
alembic revision -m "add_metadata_column"

# Rollback last migration
alembic downgrade -1
```
