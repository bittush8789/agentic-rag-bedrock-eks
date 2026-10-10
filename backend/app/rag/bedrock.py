import hashlib
import json
import math
import re
import time
from typing import List, Dict, Any, Tuple, Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from app.core.config import settings
from app.core.logging import logger


class BedrockClient:
    def __init__(self):
        self.embedding_model_id = settings.BEDROCK_EMBEDDING_MODEL_ID
        self.generation_model_id = settings.BEDROCK_GENERATION_MODEL_ID
        self.dimension = settings.BEDROCK_EMBEDDING_DIMENSION
        self.mock_mode = settings.MOCK_BEDROCK

        self._client = None
        if not self.mock_mode:
            try:
                session = boto3.Session(region_name=settings.AWS_REGION)
                if not session.get_credentials() and settings.ENVIRONMENT == "dev":
                    logger.info("No AWS credentials located in dev environment. Activating mock Bedrock provider.")
                    self.mock_mode = True
                else:
                    boto_config = Config(
                        region_name=settings.AWS_REGION,
                        retries={"max_attempts": 3, "mode": "standard"},
                        connect_timeout=5,
                        read_timeout=60
                    )
                    self._client = boto3.client(
                        "bedrock-runtime",
                        region_name=settings.AWS_REGION,
                        config=boto_config
                    )
            except Exception as e:
                logger.warning(f"Could not initialize AWS Bedrock client: {e}. Falling back to mock mode.")
                self.mock_mode = True

    def _mock_embedding(self, text: str) -> List[float]:
        """
        Generates a deterministic unit vector for local testing and offline execution.
        Uses bag-of-words hashing so texts sharing semantic terms have high cosine similarity.
        """
        words = re.findall(r"\b[a-z0-9_-]{2,}\b", text.lower())
        if not words:
            words = ["empty"]

        vec = [0.0] * self.dimension
        for word in words:
            for salt in ("a", "b", "c"):
                h = int(hashlib.md5(f"{word}:{salt}".encode("utf-8")).hexdigest(), 16)
                idx = h % self.dimension
                vec[idx] += 1.0

        # Normalize to unit length for cosine similarity
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    async def get_embedding(self, text: str) -> List[float]:
        """Generates embedding vector for a text string."""
        if self.mock_mode or not self._client:
            return self._mock_embedding(text)

        try:
            if "titan-embed" in self.embedding_model_id:
                body = {"inputText": text}
                if "v2" in self.embedding_model_id:
                    body["dimensions"] = self.dimension
                    body["normalize"] = True
            elif "cohere" in self.embedding_model_id:
                body = {"texts": [text], "input_type": "search_document"}
            else:
                body = {"inputText": text}

            response = self._client.invoke_model(
                modelId=self.embedding_model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body)
            )
            response_body = json.loads(response["body"].read())

            if "embedding" in response_body:
                return response_body["embedding"]
            elif "embeddings" in response_body:
                return response_body["embeddings"][0]
            else:
                raise ValueError("Unexpected embedding response schema from Bedrock")
        except (ClientError, BotoCoreError, Exception) as e:
            logger.warning(f"Bedrock embedding failed ({e}). Falling back to mock embedding.")
            if settings.ENVIRONMENT == "dev":
                self.mock_mode = True
                return self._mock_embedding(text)
            raise

    async def generate_answer(
        self,
        system_prompt: str,
        user_message: str,
        context_chunks: List[Dict[str, Any]]
    ) -> Tuple[str, int, int]:
        """
        Generates grounded answer using configured Bedrock LLM.
        Returns: (answer_text, tokens_used, latency_ms)
        """
        start_time = time.time()

        if self.mock_mode or not self._client:
            latency_ms = int((time.time() - start_time) * 1000)
            if not context_chunks:
                return (
                    "I could not find sufficient evidence in the uploaded documents to answer your question.",
                    50,
                    latency_ms
                )
            
            top_chunk = context_chunks[0]
            doc_name = top_chunk.get("document_name", "Document")
            page_info = f"page {top_chunk.get('page_number')}" if top_chunk.get("page_number") else "the text"
            chunk_id = top_chunk.get("id")
            snippet = top_chunk.get("content", "")[:200]

            answer = (
                f"Based on **{doc_name}** ({page_info}), here is what the documents state:\n\n"
                f"> \"{snippet}...\"\n\n"
                f"This information is grounded in [Chunk {chunk_id}]."
            )
            return answer, 120, latency_ms

        try:
            messages = [
                {
                    "role": "user",
                    "content": [{"text": user_message}]
                }
            ]
            system = [{"text": system_prompt}]

            response = self._client.converse(
                modelId=self.generation_model_id,
                messages=messages,
                system=system,
                inferenceConfig={"maxTokens": 1024, "temperature": 0.1}
            )

            latency_ms = int((time.time() - start_time) * 1000)
            output_msg = response["output"]["message"]["content"][0]["text"]
            usage = response.get("usage", {})
            tokens_used = usage.get("totalTokens", 0)

            return output_msg, tokens_used, latency_ms
        except (ClientError, BotoCoreError, Exception) as e:
            logger.warning(f"Bedrock generation failed: {e}")
            if settings.ENVIRONMENT == "dev":
                self.mock_mode = True
                latency_ms = int((time.time() - start_time) * 1000)
                if not context_chunks:
                    return (
                        "I could not find sufficient evidence in the uploaded documents to answer your question.",
                        0,
                        latency_ms
                    )
                top_chunk = context_chunks[0]
                return (
                    f"Based on **{top_chunk.get('document_name', 'Document')}**, {top_chunk.get('content', '')[:180]} [Chunk {top_chunk.get('id')}].",
                    50,
                    latency_ms
                )
            raise


bedrock_client = BedrockClient()
