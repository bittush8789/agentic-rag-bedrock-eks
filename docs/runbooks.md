# Operational Incident Response Runbooks

## Runbook 1: High Latency (> 2s) on `/api/v1/chat`

### Symptoms & Alerts
- Alert `FastAPIP95LatencyHigh` triggers.
- Users report delayed responses in the web chat interface.

### Triage Steps
1. **Check Grafana Latency Breakdown**:
   - Is the delay occurring in vector retrieval (`vector_store.py`) or LLM inference (`bedrock.py`)?
2. **If Bedrock Latency is Elevated**:
   - Verify AWS Bedrock Service Health Dashboard for regional API throttling or degraded performance.
   - Check if Bedrock model quotas are being saturated.
3. **If Vector Retrieval is Elevated**:
   - Check RDS PostgreSQL CPU and IOPS in CloudWatch.
   - Run `EXPLAIN ANALYZE` on vector distance query in PostgreSQL to verify HNSW index usage:
     ```sql
     EXPLAIN ANALYZE SELECT id, content, (embedding <=> '[...]') 
     FROM chunks WHERE tenant_id = '...' ORDER BY 3 LIMIT 4;
     ```
   - If index scan is not occurring, increase `ef_search` or verify index creation.

---

## Runbook 2: Messages Accumulating in SQS Dead-Letter Queue (DLQ)

### Symptoms & Alerts
- Alert `SQSDeadLetterQueueMessagesPresent` triggers (`approximate_number_of_messages_visible > 0`).

### Triage Steps
1. **Inspect DLQ Messages**:
   ```bash
   aws sqs receive-message \
     --queue-url https://sqs.us-east-1.amazonaws.com/.../agentic-rag-ingestion-dlq \
     --max-number-of-messages 1
   ```
2. **Retrieve Correlated Document ID**:
   - Extract `document_id` from the message payload.
3. **Query Document Error State**:
   ```sql
   SELECT id, filename, status, error_message, updated_at 
   FROM documents WHERE id = '<document_id>';
   ```
4. **Common Root Causes**:
   - **Corrupted PDF**: PyPDF could not extract text (password-protected or scanned raster image without text layer).
   - **Bedrock Throttling**: Embeddings API exceeded TPS limits during bulk batch upload.
5. **Remediation & Redrive**:
   - Once underlying issue is resolved (e.g. quota increase), redrive messages from DLQ to the main ingestion queue via AWS SQS Console or CLI:
     ```bash
     aws sqs start-message-move-task \
       --source-arn arn:aws:sqs:...:ingestion-dlq \
       --destination-arn arn:aws:sqs:...:ingestion-queue
     ```

---

## Runbook 3: Amazon Bedrock Throttling (`ThrottlingException`)

### Symptoms & Alerts
- Backend or worker logs show `botocore.exceptions.ClientError: An error occurred (ThrottlingException)`.

### Remediation
1. Verify configured retry backoff policy in `bedrock.py`.
2. Request a Bedrock Service Quotas increase for `anthropic.claude-3-haiku` and `amazon.titan-embed-text-v2:0` in the target AWS region.
3. Enable cross-region inference profiles or provisioned throughput if enterprise concurrency demands exceed standard on-demand quotas.
