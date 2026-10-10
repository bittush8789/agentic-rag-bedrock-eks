import asyncio
import json
import os
import signal
import sys
import time
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.core.config import settings
from app.core.logging import setup_logging, logger
from worker.tasks import execute_ingestion_task

HEARTBEAT_FILE = "/tmp/worker_heartbeat"


class IngestionWorker:
    def __init__(self):
        self.running = True
        self.queue_url = settings.SQS_QUEUE_URL
        self.region = settings.AWS_REGION
        self.sqs = None

        if self.queue_url:
            try:
                self.sqs = boto3.client("sqs", region_name=self.region)
                logger.info(f"Connected to Amazon SQS Queue: {self.queue_url}")
            except Exception as e:
                logger.warning(f"Could not initialize SQS client: {e}. Worker will run in idle mode.")
        else:
            logger.info("No SQS_QUEUE_URL provided. Worker running in standalone heartbeat mode.")

    def update_heartbeat(self):
        try:
            with open(HEARTBEAT_FILE, "w") as f:
                f.write(str(int(time.time())))
        except Exception:
            pass

    def stop(self, *args):
        logger.info("Received termination signal. Initiating graceful worker shutdown...")
        self.running = False

    async def process_sqs_message(self, message: dict):
        receipt_handle = message.get("ReceiptHandle")
        body_raw = message.get("Body", "{}")

        try:
            payload = json.loads(body_raw)
            document_id = payload.get("document_id")
            tenant_id = payload.get("tenant_id")

            if not document_id or not tenant_id:
                logger.warning(f"Invalid message payload: {payload}. Deleting from queue.")
                self.delete_message(receipt_handle)
                return

            success = await execute_ingestion_task(document_id, tenant_id)
            if success:
                # Successfully processed; delete from SQS
                self.delete_message(receipt_handle)
            else:
                logger.warning(f"Task failed for document {document_id}; message left for DLQ redrive.")
        except Exception as e:
            logger.error(f"Error handling SQS message: {e}")

    def delete_message(self, receipt_handle: str):
        if not self.sqs or not self.queue_url or not receipt_handle:
            return
        try:
            self.sqs.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
        except ClientError as e:
            logger.error(f"Failed to delete SQS message: {e}")

    async def run(self):
        setup_logging(settings.LOG_LEVEL)
        logger.info("Starting Enterprise Ingestion Worker daemon...")

        # Setup OS signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.stop)
            except (NotImplementedError, AttributeError):
                # Windows signal compatibility
                signal.signal(sig, lambda s, f: self.stop())

        while self.running:
            self.update_heartbeat()

            if not self.sqs or not self.queue_url:
                await asyncio.sleep(5)
                continue

            try:
                # Long-poll SQS
                response = self.sqs.receive_message(
                    QueueUrl=self.queue_url,
                    MaxNumberOfMessages=5,
                    WaitTimeSeconds=10,
                    VisibilityTimeout=120
                )
                messages = response.get("Messages", [])
                if messages:
                    logger.info(f"Received {len(messages)} messages from SQS.")
                    for msg in messages:
                        if not self.running:
                            break
                        await self.process_sqs_message(msg)
            except ClientError as e:
                logger.error(f"SQS polling error: {e}")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Unexpected worker loop exception: {e}")
                await asyncio.sleep(2)

        logger.info("Worker process terminated cleanly.")


if __name__ == "__main__":
    worker = IngestionWorker()
    asyncio.run(worker.run())
