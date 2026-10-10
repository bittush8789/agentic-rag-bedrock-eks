variable "environment" {
  description = "Target deployment environment"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of documents S3 bucket"
  type        = string
}

variable "sqs_queue_arn" {
  description = "ARN of ingestion SQS queue"
  type        = string
}

variable "sqs_dlq_arn" {
  description = "ARN of ingestion dead-letter queue"
  type        = string
}

variable "db_secret_arn" {
  description = "ARN of database credentials secret in Secrets Manager"
  type        = string
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
