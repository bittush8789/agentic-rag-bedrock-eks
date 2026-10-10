# Observability & Monitoring Guide

## 1. Observability Architecture

The platform implements a unified observability plane across metrics, logs, and distributed traces:

```
[FastAPI / Worker Pods]
     │
     ├── Logs (JSON) ─────────────> [Amazon CloudWatch Logs]
     ├── Metrics (Prometheus) ───> [Prometheus Server] ───> [Grafana Dashboards]
     └── Traces (OTel SDK) ──────> [OpenTelemetry Collector] ───> [AWS X-Ray / Jaeger]
```

---

## 2. Structured JSON Logging & Request Tracing

- Every incoming HTTP request is assigned a unique `correlation_id` (via `X-Request-ID` header or generated UUID).
- Context variable propagation ensures all logs emitted during that request lifecycle include `correlation_id` and `tenant_id`.
- Example log entry in CloudWatch:
```json
{
  "timestamp": "2026-10-10 14:22:15,102",
  "level": "INFO",
  "message": "POST /api/v1/chat -> 200 (620ms)",
  "logger": "agentic_rag",
  "module": "main",
  "line": 64,
  "correlation_id": "9c18d32b-42fa-48bc-b53d-24958194a819",
  "tenant_id": "tenant-acme"
}
```

---

## 3. Prometheus Metrics & Scrape Targets

The FastAPI application exports Prometheus metrics:
- `http_requests_total{method, path, status}`: Request count counter.
- `http_request_duration_seconds{method, path, le}`: Histogram measuring request latency.
- `document_ingestion_seconds`: Histogram measuring parsing, chunking, and embedding duration.
- `bedrock_tokens_total{model_id, type}`: Counter tracking prompt and completion token usage.
- `bedrock_latency_seconds`: Latency of Amazon Bedrock API calls.

---

## 4. Operational Dashboards in Grafana

Import `observability/grafana/dashboards/agentic-rag-dashboard.json`:
- **API Throughput & Error Rate**: Real-time traffic broken down by HTTP status code.
- **Latency Heatmap**: p50, p95, and p99 response times.
- **SQS Backlog Depth**: Pending ingestion queue count vs Dead-Letter Queue messages.
- **Pod Replicas**: Real-time HPA autoscaling states.
