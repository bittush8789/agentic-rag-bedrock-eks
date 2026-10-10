from typing import Optional, Any
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error type identifier")
    detail: str = Field(..., description="Human-readable error explanation")
    correlation_id: Optional[str] = Field(default=None, description="Request correlation tracking ID")


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Overall service status")
    version: str = Field(default="1.0.0", description="API version")
    database: str = Field(default="connected", description="Database connectivity status")
    environment: str = Field(..., description="Deployment environment")
