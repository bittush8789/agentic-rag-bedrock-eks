output "repository_urls" {
  description = "Map of component names to ECR repository URLs"
  value       = { for k, v in aws_ecr_repository.repos : k => v.repository_url }
}

output "repository_arns" {
  description = "Map of component names to ECR repository ARNs"
  value       = { for k, v in aws_ecr_repository.repos : k => v.arn }
}
