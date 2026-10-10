output "vpc_id" {
  description = "Production VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_name" {
  description = "Production EKS Cluster Name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "Production EKS API Endpoint"
  value       = module.eks.cluster_endpoint
}

output "ecr_repository_urls" {
  description = "Production ECR Image Repositories"
  value       = module.ecr.repository_urls
}

output "s3_bucket_name" {
  description = "Production Documents S3 Bucket"
  value       = module.s3.bucket_id
}

output "sqs_queue_url" {
  description = "Production Ingestion SQS Queue URL"
  value       = module.sqs.queue_url
}

output "rds_endpoint" {
  description = "Production RDS PostgreSQL Endpoint"
  value       = module.rds.endpoint
}
