# Disaster Recovery & Business Continuity Guide

## 1. Objectives & SLAs

| Metric | Target SLA | Strategy |
| :--- | :--- | :--- |
| **Recovery Point Objective (RPO)** | < 5 Minutes | RDS continuous WAL backups; S3 object versioning enabled. |
| **Recovery Time Objective (RTO)** | < 30 Minutes | Infrastructure automated via Terraform; workloads deployed via Argo CD / Helm. |

---

## 2. Backup Architecture

1. **Relational & Vector Data (RDS)**:
   - Automated continuous snapshots retained for 30 days in production.
   - Point-In-Time Recovery (PITR) supported down to any specific second within the retention window.
2. **Original Documents (S3)**:
   - S3 Versioning enabled with MFA Delete in production.
   - Cross-Region Replication (CRR) configured to a secondary recovery region.
3. **Configuration & Infrastructure (Git)**:
   - Monorepo stored in GitHub; Terraform remote state encrypted in S3 with DynamoDB state locks.

---

## 3. Disaster Recovery Procedures

### 3.1 Scenario: RDS Database Corruption or Deletion
To restore PostgreSQL from automated backup or point-in-time:

```bash
# 1. Identify latest restore point
aws rds describe-db-instances \
  --db-instance-identifier prod-agentic-rag-postgres \
  --query "DBInstances[0].LatestRestorableTime"

# 2. Restore to new instance
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier prod-agentic-rag-postgres \
  --target-db-instance-identifier prod-agentic-rag-postgres-restored \
  --restore-time "2026-10-10T14:00:00Z" \
  --db-subnet-group-name prod-agentic-rag-db-subnet-group

# 3. Update connection string in Secrets Manager
aws secretsmanager update-secret \
  --secret-id prod-agentic-rag-db-credentials \
  --secret-string file://new_db_credentials.json
```

### 3.2 Scenario: Total EKS Cluster Loss
1. Execute Terraform apply to recreate cluster and node groups:
   ```bash
   cd infrastructure/terraform/environments/prod
   terraform apply -auto-approve
   ```
2. Reconnect `kubectl` to the newly provisioned cluster.
3. Install AWS Load Balancer Controller and Argo CD.
4. Apply GitOps manifests:
   ```bash
   kubectl apply -f deploy/argocd/application-prod.yaml
   ```
   Argo CD will automatically reconcile all pods, services, HPAs, and Ingress resources within 10 minutes.
