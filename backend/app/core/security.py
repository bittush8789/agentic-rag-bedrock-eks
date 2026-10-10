from fastapi import Header, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.core.config import settings
from app.core.logging import tenant_id_ctx

bearer_scheme = HTTPBearer(auto_error=False)


async def get_tenant_id(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> str:
    """
    Extracts and validates the tenant ID from the X-Tenant-ID header.
    Defaults to settings.DEFAULT_TENANT_ID if not supplied in dev mode.
    """
    tenant = x_tenant_id.strip() if x_tenant_id else settings.DEFAULT_TENANT_ID
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header 'X-Tenant-ID' is required for tenant isolation."
        )
    # Basic sanitize check for path traversal / SQL injection safety
    if not tenant.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant ID format. Must contain alphanumeric, dashes, or underscores only."
        )
    tenant_id_ctx.set(tenant)
    return tenant


async def verify_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> Optional[str]:
    """
    Validates optional Bearer token if API_KEY_SECRET is configured.
    """
    if settings.API_KEY_SECRET:
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Bearer Authorization header"
            )
        if credentials.credentials != settings.API_KEY_SECRET:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authorization token"
            )
        return credentials.credentials
    return None
