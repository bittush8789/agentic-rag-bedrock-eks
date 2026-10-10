output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_name" {
  description = "EKS Cluster Name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS API Server Endpoint"
  value       = module.eks.cluster_endpoint
}

output "ecr_repository_urls" {
  description = "ECR Container Image Repositories"
  value       = module.ecr.repository_urls
}

output "s3_bucket_name" {
  description = "Documents S3 Bucket"
  value       = module.s3.bucket_id
}

output "sqs_queue_url" {
  description = "SQS Ingestion Queue URL"
  value       = module.sqs.queue_url
}

output "rds_endpoint" {
  description = "RDS PostgreSQL Endpoint"
  value       = module.rds.endpoint
}

output "rds_secret_arn" {
  description = "Secrets Manager DB Credentials Secret ARN"
  value       = module.rds.secret_arn
}
