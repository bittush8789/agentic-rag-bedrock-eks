terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state backend template (Uncomment and configure for production S3 state locking)
  # backend "s3" {
  #   bucket         = "myorg-terraform-state-dev"
  #   key            = "agentic-rag/dev/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "myorg-terraform-locks-dev"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "dev"
      Project     = "Agentic-RAG"
      ManagedBy   = "Terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  cluster_name = "dev-agentic-rag-eks"
  environment  = "dev"
  account_id   = data.aws_caller_identity.current.account_id
}

# 1. Networking (VPC)
module "vpc" {
  source             = "../../modules/vpc"
  environment        = local.environment
  cluster_name       = local.cluster_name
  vpc_cidr           = "10.10.0.0/16"
  max_azs            = 2
  single_nat_gateway = true # Cost savings for dev
}

# 2. Security Groups
module "security_groups" {
  source       = "../../modules/security_groups"
  environment  = local.environment
  vpc_id       = module.vpc.vpc_id
  cluster_name = local.cluster_name
}

# 3. ECR Repositories
module "ecr" {
  source      = "../../modules/ecr"
  environment = local.environment
}

# 4. S3 Storage
module "s3" {
  source      = "../../modules/s3"
  environment = local.environment
  account_id  = local.account_id
}

# 5. SQS Ingestion Queues
module "sqs" {
  source      = "../../modules/sqs"
  environment = local.environment
}

# 6. RDS PostgreSQL with pgvector
module "rds" {
  source                  = "../../modules/rds"
  environment             = local.environment
  db_name                 = "agentic_rag"
  db_username             = "rag_admin"
  instance_class          = "db.t4g.micro"
  allocated_storage       = 20
  max_allocated_storage   = 50
  db_subnet_group_name    = module.vpc.db_subnet_group_name
  security_group_id       = module.security_groups.rds_security_group_id
  multi_az                = false
  deletion_protection     = false
  skip_final_snapshot     = true
  backup_retention_period = 3
}

# 7. IAM & Pod Identity
module "iam" {
  source        = "../../modules/iam"
  environment   = local.environment
  s3_bucket_arn = module.s3.bucket_arn
  sqs_queue_arn = module.sqs.queue_arn
  sqs_dlq_arn   = module.sqs.dlq_arn
  db_secret_arn = module.rds.secret_arn
}

# 8. EKS Cluster
module "eks" {
  source                 = "../../modules/eks"
  environment            = local.environment
  cluster_role_arn       = module.iam.cluster_role_arn
  node_role_arn          = module.iam.node_role_arn
  public_subnet_ids      = module.vpc.public_subnet_ids
  private_subnet_ids     = module.vpc.private_subnet_ids
  node_security_group_id = module.security_groups.node_security_group_id
  instance_types         = ["t3.medium"]
  capacity_type          = "ON_DEMAND"
  desired_nodes          = 2
  min_nodes              = 1
  max_nodes              = 3
  namespace              = "agentic-rag"
  backend_pod_role_arn   = module.iam.backend_pod_role_arn
  worker_pod_role_arn    = module.iam.worker_pod_role_arn
}
