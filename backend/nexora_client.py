"""NexoraDB client wrapper for external application communication.

This module provides the only interface between the FastAPI application
and NexoraDB. All database operations must go through this layer.
"""

from __future__ import annotations

from typing import Any, Optional, Dict, List

try:
    from nexoradb.api import connect, NexoraDBClient, NexoraDBError, NexoraDBAuthError
except ImportError:
    raise ImportError(
        "nexoradb package is not installed. "
        "Please install it from the main NexoraDB project."
    )


class NexoraDBConnectionError(RuntimeError):
    """Raised when NexoraDB is not reachable."""
    pass


class NexoraDBQueryError(RuntimeError):
    """Raised when a query execution fails."""
    pass


class NexoraClient:
    """Client wrapper for NexoraDB operations.

    This class encapsulates all interactions with the NexoraDB Python Driver.
    It provides lazy initialization, connection health checks, and query execution
    with proper error handling.

    Architecture Rule: This is the ONLY place where nexoradb.api is imported.
    """

    def __init__(self, url: str, token: str, timeout: float = 15.0):
        self._url = url
        self._token = token
        self._timeout = timeout
        self._client: Optional[NexoraDBClient] = None

    def _ensure_connection(self) -> None:
        """Ensure the driver connection is established."""
        if self._client is None:
            self._client = connect(
                url=self._url,
                token=self._token,
                timeout=self._timeout,
            )

    def ping(self) -> bool:
        """Check if NexoraDB is reachable and the token is valid."""
        try:
            self._ensure_connection()
            return self._client.ping()
        except (NexoraDBError, NexoraDBAuthError):
            return False

    def execute(self, query: str) -> Any:
        """Execute a query and return the raw result object."""
        try:
            self._ensure_connection()
            return self._client.execute(query)
        except NexoraDBAuthError as e:
            raise NexoraDBConnectionError(
                "Application token is invalid or has expired"
            ) from e
        except NexoraDBError as e:
            raise NexoraDBQueryError(f"Query execution failed: {str(e)}") from e

    def execute_raw(self, query: str) -> List[Dict[str, Any]]:
        """Execute a query and return rows as a list of dictionaries."""
        result = self.execute(query)
        return result.rows if hasattr(result, "rows") else []


def create_nexora_client(settings) -> NexoraClient:
    """Factory function for creating a NexoraClient from settings."""
    return NexoraClient(
        url=settings.NEXORADB_URL,
        token=settings.NEXORADB_APP_TOKEN,
        timeout=settings.DRIVER_TIMEOUT,
    )