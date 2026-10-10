import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Add backend directory to path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.db.base import Base
from app.db.session import engine, AsyncSessionLocal
from app.services.document_service import document_service
from app.services.chat_service import chat_service
from app.core.config import settings
from app.core.logging import setup_logging, logger


async def run_evaluation():
    setup_logging("WARNING")
    dataset_path = Path(__file__).parent / "eval_dataset.json"
    if not dataset_path.exists():
        print(f"Dataset file not found at {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    print("\n=======================================================")
    print("      AGENTIC RAG BENCHMARK & EVALUATION SUITE")
    print("=======================================================")
    print(f"Loaded {len(samples)} benchmark evaluation samples.")

    # Initialize tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    results = []
    eval_tenant = "eval-benchmark-tenant"

    for idx, item in enumerate(samples, 1):
        print(f"\n[{idx}/{len(samples)}] Evaluating: {item['question']}")
        
        async with AsyncSessionLocal() as session:
            # 1. Ingest evaluation document
            doc_bytes = item["document_text"].encode("utf-8")
            doc, _ = await document_service.create_document(
                tenant_id=eval_tenant,
                filename=item["document_filename"],
                content=doc_bytes,
                content_type="text/plain",
                background_tasks=None,
                db=session
            )

            # 2. Execute RAG Chat query
            t0 = time.time()
            chat_response = await chat_service.process_chat(
                tenant_id=eval_tenant,
                message=item["question"],
                conversation_id=None,
                document_ids=[doc.id],
                db=session
            )
            elapsed_ms = int((time.time() - t0) * 1000)

            # 3. Groundedness and citation scoring
            answer = chat_response.answer.lower()
            citations = chat_response.citations

            # Keyword recall check
            matched_kw = [kw for kw in item["expected_keywords"] if kw.lower() in answer]
            recall_score = len(matched_kw) / len(item["expected_keywords"]) if item["expected_keywords"] else 1.0

            # Citation validation check
            citation_valid = len(citations) > 0 and all(c.document_name == item["document_filename"] for c in citations)

            results.append({
                "id": item["id"],
                "question": item["question"],
                "latency_ms": elapsed_ms,
                "tokens": chat_response.meta.tokens_used,
                "keyword_recall": round(recall_score, 2),
                "citations_count": len(citations),
                "citations_valid": citation_valid,
                "answer_preview": chat_response.answer[:120] + "..."
            })

            # Cleanup document
            await document_service.delete_document(eval_tenant, doc.id, session)

    # Summary table
    print("\n" + "=" * 80)
    print(f"{'ID':<10} {'Latency(ms)':<14} {'Recall':<10} {'Citations':<12} {'Valid':<8}")
    print("-" * 80)
    total_latency = 0
    total_recall = 0
    valid_citations_count = 0

    for r in results:
        total_latency += r["latency_ms"]
        total_recall += r["keyword_recall"]
        if r["citations_valid"]:
            valid_citations_count += 1
        print(f"{r['id']:<10} {r['latency_ms']:<14} {r['keyword_recall']:<10.2f} {r['citations_count']:<12} {str(r['citations_valid']):<8}")

    n = len(results)
    avg_latency = total_latency / n if n else 0
    avg_recall = (total_recall / n) * 100 if n else 0
    citation_accuracy = (valid_citations_count / n) * 100 if n else 0

    print("=" * 80)
    print(f"Average Latency:      {avg_latency:.1f} ms")
    print(f"Fact Recall Score:    {avg_recall:.1f}%")
    print(f"Citation Accuracy:    {citation_accuracy:.1f}%")
    print("=" * 80 + "\n")

    report_path = Path("./evaluation/evaluation_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "metrics": {
                "average_latency_ms": avg_latency,
                "fact_recall_percent": avg_recall,
                "citation_accuracy_percent": citation_accuracy
            },
            "results": results
        }, f, indent=2)
    print(f"Detailed evaluation report saved to {report_path.resolve()}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
