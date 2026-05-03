"""Client identity primitives for WebSocket connections.

Provides token generation, validation, and in-memory identity storage for
the WebSocket client identity mechanism (BL-315).
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable


def generate_client_id() -> str:
    """Generate a cryptographically random 32-char lowercase hex client ID.

    Returns:
        A 32-character lowercase hex string suitable for use as a client identity token.
    """
    return secrets.token_hex(16)


def is_valid_client_id(token: Any) -> bool:
    """Return True if token is a valid 32-char lowercase hex string.

    Args:
        token: Value to validate.

    Returns:
        True if token is a non-empty string of exactly 32 lowercase hex characters.
    """
    if not isinstance(token, str):
        return False
    if len(token) != 32:
        return False
    return all(c in "0123456789abcdef" for c in token)


@runtime_checkable
class ClientIdentityStore(Protocol):
    """Protocol for client identity storage backends.

    All methods are synchronous. Asyncio's single-threaded execution model
    guarantees atomicity of consecutive synchronous statements between yield
    points, so no asyncio.Lock is required (FG-001).
    """

    def store(self, client_id: str, metadata: dict[str, Any] | None = None) -> None:
        """Store a client identity entry.

        Args:
            client_id: 32-char hex client token. Must pass is_valid_client_id().
            metadata: Optional free-form metadata dict. Defaults to empty dict.

        Raises:
            ValueError: If client_id is not a valid 32-char hex string.
            TypeError: If metadata is not a dict or None.
        """
        ...

    def retrieve(self, client_id: str) -> dict[str, Any] | None:
        """Retrieve a stored identity entry, touching last_seen.

        Args:
            client_id: 32-char hex client token.

        Returns:
            The stored entry dict (with client_id, metadata, created_at, last_seen),
            or None if not found or client_id is invalid.
        """
        ...

    def clear(self, client_id: str) -> None:
        """Remove a stored identity entry.

        Args:
            client_id: 32-char hex client token.

        No-op if client_id is invalid or not found; never raises.
        """
        ...


class InMemoryClientIdentityStore:
    """In-memory implementation of ClientIdentityStore backed by a plain dict.

    Suitable for single-process deployments (v056). Thread-safety is provided
    by asyncio's single-threaded execution model; no lock is required (FG-001).
    """

    def __init__(self) -> None:
        """Initialize an empty identity store."""
        self._store: dict[str, dict[str, Any]] = {}

    def store(self, client_id: str, metadata: dict[str, Any] | None = None) -> None:
        """Store a client identity entry with timestamps.

        If client_id already exists, metadata is updated and created_at is preserved.

        Args:
            client_id: 32-char hex client token.
            metadata: Optional free-form metadata dict. Defaults to empty dict.

        Raises:
            ValueError: If client_id is not a valid 32-char hex string.
            TypeError: If metadata is not a dict or None.
        """
        if not is_valid_client_id(client_id):
            raise ValueError(
                f"client_id must be a 32-char lowercase hex string, got: {client_id!r}"
            )
        if metadata is not None and not isinstance(metadata, dict):
            raise TypeError(f"metadata must be a dict or None, got: {type(metadata).__name__}")

        resolved_metadata: dict[str, Any] = metadata if metadata is not None else {}
        now = datetime.now(timezone.utc).isoformat()

        if client_id in self._store:
            self._store[client_id]["metadata"] = resolved_metadata
            self._store[client_id]["last_seen"] = now
        else:
            self._store[client_id] = {
                "client_id": client_id,
                "metadata": resolved_metadata,
                "created_at": now,
                "last_seen": now,
            }

    def retrieve(self, client_id: str) -> dict[str, Any] | None:
        """Retrieve a stored identity entry, updating last_seen.

        Args:
            client_id: 32-char hex client token.

        Returns:
            The stored entry dict, or None if not found or client_id is invalid.
        """
        if not is_valid_client_id(client_id):
            return None
        entry = self._store.get(client_id)
        if entry is None:
            return None
        entry["last_seen"] = datetime.now(timezone.utc).isoformat()
        return entry

    def clear(self, client_id: str) -> None:
        """Remove a stored identity entry.

        Args:
            client_id: 32-char hex client token.

        No-op if client_id is invalid or not found; never raises.
        """
        if not is_valid_client_id(client_id):
            return
        self._store.pop(client_id, None)
