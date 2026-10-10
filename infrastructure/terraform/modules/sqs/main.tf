# 1. Dead-Letter Queue (DLQ)
resource "aws_sqs_queue" "dlq" {
  name                      = "${var.environment}-agentic-rag-ingestion-dlq"
  message_retention_seconds = 1209600 # 14 days
  sqs_managed_sse_enabled   = true

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-ingestion-dlq"
    }
  )
}

# 2. Main Document Ingestion Queue
resource "aws_sqs_queue" "ingestion" {
  name                       = "${var.environment}-agentic-rag-ingestion-queue"
  visibility_timeout_seconds = 180
  message_retention_seconds  = 345600 # 4 days
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-ingestion-queue"
    }
  )
}
