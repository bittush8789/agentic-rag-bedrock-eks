# Terraform Infrastructure Provisioning Guide

## 1. Directory Structure

```
infrastructure/terraform/
├── modules/
│   ├── vpc/             # Multi-AZ VPC, subnets, NAT Gateways
│   ├── security_groups/ # ALB, EKS Node, and RDS security groups
│   ├── ecr/             # Container repositories with lifecycle policies
│   ├── s3/              # Encrypted document storage bucket
│   ├── sqs/             # Ingestion queue and dead-letter queue
│   ├── rds/             # PostgreSQL 16 with pgvector & Secrets Manager
│   ├── iam/             # EKS cluster role, node role, Pod Identity roles
│   └── eks/             # EKS v1.31, managed node groups, add-ons
└── environments/
    ├── dev/             # Cost-conscious development setup
    └── prod/            # High-availability production setup
```

---

## 2. Environment Differences

| Component | Development (`dev`) | Production (`prod`) |
| :--- | :--- | :--- |
| **Availability Zones** | 2 AZs | 3 AZs |
| **NAT Gateways** | 1 (shared across public subnets) | 3 (dedicated NAT per AZ) |
| **Node Groups** | 2x `t3.medium` instances | 3-12x `m6i.xlarge` instances |
| **RDS PostgreSQL** | Single-AZ (`db.t4g.micro`), 20 GB | Multi-AZ (`db.r6g.xlarge`), 100 GB |
| **Deletion Protection** | Disabled (`false`) | Enabled (`true`) |
| **Backup Retention** | 3 days | 30 days |
| **EKS API Endpoint** | Public + Private | Private + Restricted Public CIDRs |

---

## 3. Provisioning Step-by-Step

### 3.1 Prerequisites
- AWS CLI v2 configured (`aws configure`)
- Terraform CLI `>= 1.5.0`
- IAM permissions: VPC, EKS, RDS, S3, SQS, IAM, Secrets Manager

### 3.2 Deploying Development Infrastructure
```bash
cd infrastructure/terraform/environments/dev

# 1. Initialize Terraform providers and modules
terraform init

# 2. Review execution plan
terraform plan -out=tfplan

# 3. Apply infrastructure (requires operator confirmation)
terraform apply tfplan

# 4. View critical outputs
terraform output
```

### 3.3 Deploying Production Infrastructure
```bash
cd infrastructure/terraform/environments/prod

# 1. Ensure backend S3 bucket and DynamoDB table are created for remote state locking
terraform init

# 2. Create custom tfvars with admin IP CIDR
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with approved corporate VPN CIDR blocks

# 3. Generate plan
terraform plan -out=tfplan-prod

# 4. Apply under change management approval
terraform apply tfplan-prod
```

---

## 4. Teardown & Resource Cleanup

To prevent stranded cloud expenses:

```bash
cd infrastructure/terraform/environments/dev

# Destroy dev resources
terraform destroy -auto-approve
```
