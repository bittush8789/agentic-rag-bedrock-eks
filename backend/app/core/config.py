import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Environment
    ENVIRONMENT: str = Field(default="dev", description="Environment: dev or prod")
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    HOST: str = Field(default="0.0.0.0", description="API Host")
    PORT: int = Field(default=8000, description="API Port")
    CORS_ORIGINS: List[str] = Field(default=["*"], description="Allowed CORS origins")

    # Security & Tenancy
    DEFAULT_TENANT_ID: str = Field(default="tenant-default", description="Fallback tenant ID")
    API_KEY_SECRET: Optional[str] = Field(default=None, description="Optional shared secret for API authentication")

    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./test_agentic_rag.db",
        description="SQLAlchemy async connection URL (PostgreSQL asyncpg or SQLite aiosqlite)"
    )
    DB_POOL_SIZE: int = Field(default=10, description="Database pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, description="Database max overflow")

    # AWS Configuration
    AWS_REGION: str = Field(default="us-east-1", description="AWS Region")
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, description="AWS Access Key")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, description="AWS Secret Key")
    AWS_SESSION_TOKEN: Optional[str] = Field(default=None, description="AWS Session Token")

    # Bedrock Models
    BEDROCK_EMBEDDING_MODEL_ID: str = Field(
        default="amazon.titan-embed-text-v2:0",
        description="Amazon Bedrock embedding model ID"
    )
    BEDROCK_GENERATION_MODEL_ID: str = Field(
        default="anthropic.claude-3-haiku-20240307-v1:0",
        description="Amazon Bedrock LLM generation model ID"
    )
    BEDROCK_EMBEDDING_DIMENSION: int = Field(
        default=1024,
        description="Embedding vector dimension (1024 for Titan v2 default)"
    )
    MOCK_BEDROCK: bool = Field(
        default=False,
        description="Use deterministic mock Bedrock provider for local dev and testing"
    )

    # Storage (S3 / Local)
    STORAGE_BACKEND: str = Field(
        default="local",
        description="Storage backend: 's3' or 'local'"
    )
    S3_BUCKET_NAME: str = Field(
        default="agentic-rag-documents",
        description="Amazon S3 bucket name"
    )
    LOCAL_STORAGE_DIR: str = Field(
        default="./data/uploads",
        description="Local directory for document storage in local mode"
    )

    # SQS Ingestion Queue
    SQS_QUEUE_URL: Optional[str] = Field(default=None, description="SQS Ingestion Queue URL")
    SQS_DLQ_URL: Optional[str] = Field(default=None, description="SQS Dead-Letter Queue URL")
    ASYNC_PROCESSING_MODE: str = Field(
        default="inline",
        description="Mode: 'sqs' (production worker) or 'inline' (local background task)"
    )

    # Document Chunking & RAG Limits
    MAX_UPLOAD_SIZE_BYTES: int = Field(
        default=25 * 1024 * 1024,
        description="Max upload size in bytes (25MB)"
    )
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".pdf", ".txt"],
        description="Permitted document file extensions"
    )
    CHUNK_SIZE: int = Field(default=500, description="Chunk size in characters")
    CHUNK_OVERLAP: int = Field(default=100, description="Chunk overlap in characters")
    TOP_K_RETRIEVAL: int = Field(default=4, description="Top-K vector matches to retrieve")
    SIMILARITY_THRESHOLD: float = Field(default=0.30, description="Minimum cosine similarity cutoff")
    MAX_RETRIEVAL_RETRIES: int = Field(default=1, description="Max query refinement retries in LangGraph")


settings = Settings()
