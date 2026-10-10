# Troubleshooting Guide

## 1. Common Operational Issues & Fixes

### 1.1 Ingress Returns `502 Bad Gateway` or `504 Gateway Timeout`
- **Cause 1: Security Group Misconfiguration**: ALB security group is unable to reach EKS Node security group on port 8000 or 8080.
  - *Fix*: Check that `aws_security_group.node` ingress permits traffic from `aws_security_group.alb`.
- **Cause 2: Health Check Failure**: ALB target group health check failing.
  - *Fix*: Ensure target group healthcheck path is set to `/health` for backend and `/nginx-health` for frontend. Check pod logs.

### 1.2 Pod CrashLoopBackOff: `OperationalError: connection refused`
- **Cause**: Backend or worker started before RDS PostgreSQL became reachable or security group rule blocks port 5432.
  - *Fix*: Verify RDS endpoint and verify `aws_security_group.rds` allows ingress from the EKS node security group. Check `kubectl logs <pod-name> -n agentic-rag`.

### 1.3 Vector Dimension Mismatch (`different vector dimensions 1024 and 1536`)
- **Cause**: Embedding model dimension configuration mismatch. Amazon Titan Text Embeddings V2 defaults to 1024, whereas Titan V1 used 1536.
  - *Fix*: Ensure `BEDROCK_EMBEDDING_DIMENSION` environment variable matches the configured model. Never mix embeddings of different dimensions in the same vector column.

---

## 2. Essential Diagnostic Commands

```bash
# 1. Check pod events and termination reason
kubectl describe pod -l app.kubernetes.io/component=backend -n agentic-rag

# 2. View previous container logs before crash
kubectl logs -l app.kubernetes.io/component=backend -n agentic-rag --previous

# 3. Check ALB Ingress status and target group registrations
kubectl describe ingress -n agentic-rag

# 4. Verify Pod Identity IAM token association inside container
kubectl exec -it <backend-pod-name> -n agentic-rag -- env | grep AWS

# 5. Execute DB connection test from inside pod
kubectl exec -it <backend-pod-name> -n agentic-rag -- python -c "
import asyncio, os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
async def test():
    engine = create_async_engine(os.environ['DATABASE_URL'])
    async with engine.connect() as conn:
        res = await conn.execute(text('SELECT 1'))
        print('DB Connection Successful:', res.scalar())
asyncio.run(test())"
```
