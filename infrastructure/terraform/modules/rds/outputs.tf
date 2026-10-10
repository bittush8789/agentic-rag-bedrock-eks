output "endpoint" {
  description = "Connection endpoint address"
  value       = aws_db_instance.postgres.address
}

output "port" {
  description = "PostgreSQL port"
  value       = aws_db_instance.postgres.port
}

output "db_instance_id" {
  description = "RDS instance identifier"
  value       = aws_db_instance.postgres.id
}

output "secret_arn" {
  description = "ARN of Secrets Manager secret containing database credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}
