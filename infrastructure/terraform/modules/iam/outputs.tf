output "cluster_role_arn" {
  description = "EKS Cluster IAM role ARN"
  value       = aws_iam_role.cluster.arn
}

output "node_role_arn" {
  description = "EKS Node Group IAM role ARN"
  value       = aws_iam_role.node.arn
}

output "backend_pod_role_arn" {
  description = "Pod Identity IAM role ARN for Backend service"
  value       = aws_iam_role.backend_pod.arn
}

output "worker_pod_role_arn" {
  description = "Pod Identity IAM role ARN for Ingestion Worker service"
  value       = aws_iam_role.worker_pod.arn
}
