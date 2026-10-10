from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    tenant_id: str
    status: str
    error_message: Optional[str] = None
    attempts: int
    created_at: datetime
    updated_at: datetime
