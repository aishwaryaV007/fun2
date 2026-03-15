"""
ai/core/security.py
===================
Security dependencies for FastAPI.
Provides API key validation using HTTP X-API-Key header.
"""

from fastapi import HTTPException, Query, Security, WebSocket, WebSocketException, status
from fastapi.security.api_key import APIKeyHeader

from core.config import ADMIN_API_KEY, API_KEY, ENFORCE_ADMIN_API_KEY

# Define the expected header name
API_KEY_NAME = "X-API-Key"

# Create the APIKeyHeader dependency
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    """
    Dependency that validates the API Key provided in the X-API-Key header.
    If the key is missing or invalid, raises an HTTP 403 Forbidden error.
    """
    if api_key_header == API_KEY:
        return api_key_header
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate API Key",
    )


def _validate_admin_api_key(provided_key: str | None) -> str | None:
    if not ENFORCE_ADMIN_API_KEY:
        return provided_key

    if provided_key == ADMIN_API_KEY:
        return provided_key

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate admin API Key",
    )


async def require_admin_api_key_if_enabled(
    api_key_header: str | None = Security(api_key_header),
    api_key_query: str | None = Query(default=None, alias="api_key"),
) -> str | None:
    """
    Enforce admin API-key authentication only when explicitly enabled by env.

    This keeps local development and current clients working by default while
    allowing production deployments to protect admin-only endpoints.
    """
    return _validate_admin_api_key(api_key_header or api_key_query)


def require_websocket_admin_api_key_if_enabled(websocket: WebSocket) -> None:
    """
    Validate admin API-key access for browser WebSockets when enforcement is on.

    Browser WebSocket clients cannot reliably send custom headers, so query-param
    auth is supported for the dashboard when ENFORCE_ADMIN_API_KEY=true.
    """
    if not ENFORCE_ADMIN_API_KEY:
        return

    provided_key = websocket.query_params.get("api_key") or websocket.headers.get(API_KEY_NAME)
    if provided_key == ADMIN_API_KEY:
        return

    raise WebSocketException(
        code=status.WS_1008_POLICY_VIOLATION,
        reason="Could not validate admin API Key",
    )
