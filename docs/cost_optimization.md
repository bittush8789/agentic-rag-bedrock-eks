# Cost Optimization & FinOps Guide

## 1. Cloud Cost Architecture Breakdown

| Component | Dev Estimated Monthly Cost | Prod Estimated Monthly Cost | Primary Cost Drivers |
| :--- | :--- | :--- | :--- |
| **Amazon EKS Cluster** | $73.00 (Fixed control plane) | $73.00 (Fixed control plane) | Cluster hour fee ($0.10/hr) |
| **EC2 Node Groups** | ~$60.00 (2x `t3.medium`) | ~$350.00 (3x `m6i.xlarge`) | Instance hours & EBS volumes |
| **NAT Gateways** | ~$35.00 (1 single NAT GW) | ~$105.00 (3 Multi-AZ NATs) | $0.045/hr + $0.045/GB data processed |
| **RDS PostgreSQL** | ~$15.00 (`db.t4g.micro`, 20GB) | ~$240.00 (`db.r6g.xlarge`, Multi-AZ) | Compute, Multi-AZ replication, IOPS |
| **Amazon Bedrock** | ~$5.00 - $15.00 | Variable based on usage | Input/output tokens & embedding tokens |
| **S3 + SQS** | < $2.00 | ~$10.00 - $25.00 | Storage GB and API requests |

---

## 2. Key FinOps Recommendations

### 2.1 NAT Gateway vs. VPC Endpoints
- **Problem**: NAT Gateways charge **$0.045 per GB** of data transferred to external endpoints, including Amazon S3, SQS, and Bedrock.
- **Optimization**: Provision **VPC Gateway Endpoints for S3** (100% free of charge).
- Provision **VPC Interface Endpoints (PrivateLink)** for SQS and Bedrock when monthly data transfer exceeds 1 TB, eliminating outbound internet egress fees.

### 2.2 Foundation Model Selection & Token Optimization
- **Embedding Model**: Use `amazon.titan-embed-text-v2:0` ($0.00002 per 1,000 input tokens) — **75% less expensive** than legacy embedding models with superior retrieval accuracy.
- **Generation Model**: Default to `anthropic.claude-3-haiku` ($0.00025 / 1K input tokens; $0.00125 / 1K output tokens) for high-speed document synthesis. Reserve Sonnet for complex multi-step reasoning.
- **Context Filtering**: Never pass raw documents to LLMs. Strict top-K vector filtering (k=4) with similarity thresholds ensures the prompt contains only the highest-scoring chunks, minimizing token waste.

### 2.3 Compute Optimization (Spot Instances & Graviton)
- **Ingestion Workers**: The asynchronous SQS ingestion worker is resilient to interruptions. Configure worker node groups to use **Amazon EC2 Spot Instances**, slashing compute costs by **60% to 80%**.
- **RDS Graviton (ARM64)**: Utilize AWS Graviton-based instances (`db.t4g`, `db.r6g`), providing **20% better price-performance** compared to equivalent x86 instances.
