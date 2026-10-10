output "alb_security_group_id" {
  description = "Security Group ID of the ALB"
  value       = aws_security_group.alb.id
}

output "node_security_group_id" {
  description = "Security Group ID of the EKS worker nodes"
  value       = aws_security_group.node.id
}

output "rds_security_group_id" {
  description = "Security Group ID of the RDS PostgreSQL instance"
  value       = aws_security_group.rds.id
}
