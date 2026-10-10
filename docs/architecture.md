# Architecture & System Design

## 1. High-Level Architecture Overview

The **Enterprise Agentic Document Intelligence Platform** is built as a resilient, multi-tenant cloud-native application on **AWS EKS**, leveraging **Amazon Bedrock** for foundation models and **PostgreSQL with pgvector** for vector storage.

```mermaid
graph TB
    subgraph Client_Layer["Client Layer"]
        UserBrowser["User Browser<br>(HTML5 / CSS / Vanilla JS)"]
    end

    subgraph AWS_Networking["AWS Networking & Ingress"]
        ALB["Internet-Facing AWS ALB"]
        subgraph PublicSubnets["Public Subnets (Multi-AZ)"]
            NAT["NAT Gateways (Egress)"]
        end
    end

    subgraph EKS_Cluster["Amazon EKS Cluster (Private Subnets)"]
        FrontendPods["Frontend Pods<br>(Nginx Non-Root :8080)"]
        BackendPods["Backend Pods<br>(FastAPI + LangGraph :8000)"]
        WorkerPods["Ingestion Worker Pods<br>(SQS Consumer Daemon)"]
        PodIdentity["EKS Pod Identity Agent"]
    end

    subgraph AWS_Services["AWS Managed Services Plane"]
        S3Bucket["Amazon S3<br>(AES-256 / KMS Encrypted)"]
        SQSQueue["Amazon SQS + DLQ<br>(Ingestion Queue)"]
        RDSInstance["Amazon RDS PostgreSQL 16<br>(pgvector Extension)"]
        BedrockService["Amazon Bedrock<br>(Claude 3 & Titan Embeddings)"]
        SecretsMgr["AWS Secrets Manager<br>(DB Credentials)"]
        CWLogs["Amazon CloudWatch<br>(Logs & Alarms)"]
    end

    UserBrowser -->|HTTPS| ALB
    ALB -->|/| FrontendPods
    ALB -->|/api/v1| BackendPods
    FrontendPods -.->|Static Assets & Reverse Proxy| BackendPods

    BackendPods -->|1. Store Raw File| S3Bucket
    BackendPods -->|2. Publish Ingestion Task| SQSQueue
    BackendPods -->|3. Similarity Query| RDSInstance
    BackendPods -->|4. Inference & Grounding| BedrockService
    BackendPods -->|Credentials| SecretsMgr

    WorkerPods -->|Poll Ingestion Jobs| SQSQueue
    WorkerPods -->|Fetch Raw Bytes| S3Bucket
    WorkerPods -->|Generate Embeddings| BedrockService
    WorkerPods -->|Insert Chunks & Vectors| RDSInstance

    EKS_Cluster -->|Egress to AWS APIs| NAT
    EKS_Cluster -.->|Audit & Metrics| CWLogs
```

---

## 2. Document Ingestion Flow

The document ingestion pipeline processes files asynchronously to guarantee zero HTTP request timeouts on large documents.

```mermaid
sequenceDiagram
    autonumber
    actor User as Authenticated User
    participant Frontend as Vanilla JS UI
    participant API as FastAPI Backend
    participant S3 as Amazon S3
    participant SQS as Amazon SQS
    participant Worker as Ingestion Worker Pod
    participant Bedrock as Amazon Bedrock (Titan V2)
    participant RDS as PostgreSQL (pgvector)

    User->>Frontend: Drag & drop PDF/TXT file
    Frontend->>API: POST /api/v1/documents (FormData + X-Tenant-ID)
    API->>API: Validate file extension & compute SHA-256
    API->>API: Check duplicate checksum within tenant
    API->>S3: Upload raw document bytes to s3://bucket/tenant/doc_id/file
    API->>RDS: Create Document (QUEUED) & IngestionJob (QUEUED)
    API->>SQS: Send message {document_id, tenant_id}
    API-->>Frontend: HTTP 202 Accepted {document_id, job_id, status: QUEUED}

    loop Background Ingestion Worker
        Worker->>SQS: Long poll receive_message (WaitTime: 10s)
        SQS-->>Worker: Deliver job message
        Worker->>RDS: Update Document & Job status to PROCESSING
        Worker->>S3: Fetch original document bytes
        Worker->>Worker: Parse text per page (PyPDF / TXT)
        Worker->>Worker: Recursive character chunking with overlap
        loop For Each Chunk
            Worker->>Bedrock: invoke_model(titan-embed-text-v2:0, dim=1024)
            Bedrock-->>Worker: 1024-dimension float vector
        end
        Worker->>RDS: Bulk insert Chunks with embeddings
        Worker->>RDS: Update Document & Job status to READY
        Worker->>SQS: Delete message from queue
    end

    Frontend->>API: Poll GET /api/v1/documents/{document_id}
    API-->>Frontend: Status: READY, chunk_count: N
```

---

## 3. Question Answering & LangGraph Agent Flow

Every user inquiry goes through an explicit, bounded 7-step LangGraph workflow defending against prompt injection and validating source citations.

```mermaid
graph TD
    Start([User Question Received]) --> Node1[1. validate_query<br>Adversarial Pattern Guard]
    
    Node1 -->|Flagged / Injection Attack| Blocked([Security Block Response])
    Node1 -->|Safe Query| Node2[2. retrieve<br>Query Embedding & pgvector Search]

    Node2 --> Node3[3. evaluate_relevance<br>Score Threshold Check]

    Node3 -->|Score < Threshold AND retry_count == 0| Node4[4. refine_query<br>Semantic Keyword Rewrite]
    Node4 --> Node2

    Node3 -->|Score < Threshold AND retries exhausted| Fallback[7a. insufficient_evidence<br>Polite Grounded Fallback]
    
    Node3 -->|Score >= Threshold| Node5[5. generate_answer<br>Bedrock Claude 3 Grounded Generation]

    Node5 --> Node6[6. validate_citations<br>Verify Citations Match Real Chunks]

    Node6 --> FinalResponse[7b. format_response<br>Return Answer + Citations + Latency]
```

---

## 4. GitOps & Platform Delivery Pipeline

Infrastructure and application code follow strict separation of concerns:

```mermaid
graph LR
    Dev([Developer]) -->|Git Push| Repo[GitHub Monorepo]
    Repo -->|PR Trigger| CI[GitHub Actions CI<br>Lint, Bandit, Pytest, Trivy]
    CI -->|Pass| Merge[Merge to Main]
    Merge -->|CD Pipeline| CD[GitHub Actions CD<br>Build Docker & Push to ECR]
    CD -->|Update Helm Image Tag| GitOpsRepo[GitOps Branch / Manifests]
    GitOpsRepo -->|Continuous Sync| ArgoCD[Argo CD on EKS]
    ArgoCD -->|Rolling Upgrade| EKSWorkloads[EKS Pods: Frontend, Backend, Worker]
```
