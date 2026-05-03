"""Unit tests for InMemoryClientIdentityStore (Feature 002, BL-315).

Covers store/retrieve/clear operations, timestamp tracking, metadata handling,
error handling, and asyncio safety.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from stoat_ferret.api.websocket.identity import (
    InMemoryClientIdentityStore,
    generate_client_id,
)

VALID_ID = "a" * 32
VALID_ID2 = "b" * 32
INVALID_ID = "not-a-valid-token"


class TestStoreAndRetrieve:
    """Tests for basic store and retrieve operations."""

    def test_store_and_retrieve_returns_stored_entry(self) -> None:
        """store() followed by retrieve() returns the stored entry."""
        store = InMemoryClientIdentityStore()
        store.store(VALID_ID)
        entry = store.retrieve(VALID_ID)
        assert entry is not None
        assert entry["client_id"] == VALID_ID

    def test_retrieve_nonexistent_returns_none(self) -> None:
        """retrieve() returns None for a key that was never stored."""
        store = InMemoryClientIdentityStore()
        assert store.retrieve(VALID_ID) is None

    def test_retrieve_returns_metadata(self) -> None:
        """retrieve() returns the metadata that was passed to store()."""
        store = InMemoryClientIdentityStore()
        meta = {"user_agent": "test-client", "version": 2}
        store.store(VALID_ID, meta)
        entry = store.retrieve(VALID_ID)
        assert entry is not None
        assert entry["metadata"] == meta

    def test_store_without_metadata_uses_empty_dict(self) -> None:
        """store() without metadata argument defaults to empty dict."""
        store = InMemoryClientIdentityStore()
        store.store(VALID_ID)
        entry = store.retrieve(VALID_ID)
        assert entry is not None
        assert entry["metadata"] == {}

    def test_store_with_none_metadata_uses_empty_dict(self) -> None:
        """store(client_id, None) treats metadata as empty dict."""
        store = InMemoryClientIdentityStore()
        store.store(VALID_ID, None)
        entry = store.retrieve(VALID_ID)
        assert entry is not None
        assert entry["metadata"] == {}

    def test_retrieve_returns_exact_metadata(self) -> None:
        """retrieve() returns the exact metadata object passed to store()."""
        store = InMemoryClientIdentityStore()
        meta: dict = {"key": "value", "nested": {"x": 1}}
        store.store(VALID_ID, meta)
        entry = store.retrieve(VALID_ID)
        assert entry is not None
        assert entry["metadata"] == meta


class TestClearOperation:
    """Tests for clear() behavior."""

    def test_clear_removes_entry(self) -> None:
        """clear() removes the entry so retrieve() returns None."""
        store = InMemoryClientIdentityStore()
        store.store(VALID_ID)
        store.clear(VALID_ID)
        assert store.retrieve(VALID_ID) is None

    def test_clear_nonexistent_is_noop(self) -> None:
        """clear() on a non-existent key does not raise."""
        store = InMemoryClientIdentityStore()
        store.clear(VALID_ID)  # Should not raise

    def test_clear_invalid_client_id_is_noop(self) -> None:
        """clear() with invalid client_id does not raise."""
        store = InMemoryClientIdentityStore()
        store.clear(INVALID_ID)  # Should not raise
        store.clear("")  # Should not raise
        store.clear("a" * 31)  # Should not raise


class TestTimestamps:
    """Tests for created_at and last_seen timestamp management."""

    def test_store_sets_created_at(self) -> None:
        """store() sets created_at to a non-None ISO 8601 UTC timestamp."""
        store = InMemoryClientIdentityStore()
        before = datetime.now(timezone.utc)
        store.store(VALID_ID)
        after = datetime.now(timezone.utc)
        entry = store.retrieve(VALID_ID)
        assert entry is not None
        ts = datetime.fromisoformat(entry["created_at"])
        assert before <= ts <= after

    def test_store_sets_last_seen(self) -> None:
        """store() sets last_seen to a current UTC timestamp."""
        store = InMemoryClientIdentityStore()
        before = datetime.now(timezone.utc)
        store.store(VALID_ID)
        # Access internal state directly to avoid retrieve() updating last_seen
        raw_ts = store._store[VALID_ID]["last_seen"]
        ts = datetime.fromisoformat(raw_ts)
        assert ts >= before

    def test_created_at_immutable_on_second_store(self) -> None:
        """created_at is preserved when store() is called with the same key again."""
        store = InMemoryClientIdentityStore()
        store.store(VALID_ID)
        entry1 = store.retrieve(VALID_ID)
        assert entry1 is not None
        created_at_original = entry1["created_at"]

        # Store again with same key
        store.store(VALID_ID, {"updated": True})
        entry2 = store.retrieve(VALID_ID)
        assert entry2 is not None
        assert entry2["created_at"] == created_at_original

    def test_retrieve_updates_last_seen(self) -> None:
        """retrieve() updates last_seen timestamp."""
        store = InMemoryClientIdentityStore()
        store.store(VALID_ID)
        entry1 = store.retrieve(VALID_ID)
        assert entry1 is not None
        last_seen_1 = entry1["last_seen"]

        # Small delay to ensure timestamps differ
        import time

        time.sleep(0.001)

        entry2 = store.retrieve(VALID_ID)
        assert entry2 is not None
        last_seen_2 = entry2["last_seen"]
        # last_seen must be >= first retrieve's last_seen
        ts1 = datetime.fromisoformat(last_seen_1)
        ts2 = datetime.fromisoformat(last_seen_2)
        assert ts2 >= ts1

    def test_timestamps_are_utc_iso8601(self) -> None:
        """Timestamps must be ISO 8601 with UTC timezone info."""
        store = InMemoryClientIdentityStore()
        store.store(VALID_ID)
        entry = store.retrieve(VALID_ID)
        assert entry is not None
        for field in ("created_at", "last_seen"):
            ts = datetime.fromisoformat(entry[field])
            assert ts.tzinfo is not None, f"{field} is timezone-naive"


class TestMetadataHandling:
    """Tests for metadata update and storage behavior."""

    def test_store_updates_metadata_on_second_call(self) -> None:
        """Calling store() again with the same key updates metadata."""
        store = InMemoryClientIdentityStore()
        store.store(VALID_ID, {"version": 1})
        store.store(VALID_ID, {"version": 2})
        entry = store.retrieve(VALID_ID)
        assert entry is not None
        assert entry["metadata"]["version"] == 2

    def test_multiple_identities_independent(self) -> None:
        """Different client IDs are stored and retrieved independently."""
        store = InMemoryClientIdentityStore()
        meta1 = {"id": 1}
        meta2 = {"id": 2}
        store.store(VALID_ID, meta1)
        store.store(VALID_ID2, meta2)
        assert store.retrieve(VALID_ID)["metadata"] == meta1  # type: ignore[index]
        assert store.retrieve(VALID_ID2)["metadata"] == meta2  # type: ignore[index]


class TestErrorHandling:
    """Tests for error handling per AC-008."""

    def test_store_invalid_client_id_raises_valueerror(self) -> None:
        """store() with invalid client_id raises ValueError."""
        store = InMemoryClientIdentityStore()
        import pytest

        with pytest.raises(ValueError, match="client_id"):
            store.store(INVALID_ID)

    def test_store_wrong_length_client_id_raises_valueerror(self) -> None:
        """store() with wrong-length ID raises ValueError."""
        store = InMemoryClientIdentityStore()
        import pytest

        with pytest.raises(ValueError):
            store.store("a" * 31)
        with pytest.raises(ValueError):
            store.store("a" * 33)

    def test_store_invalid_metadata_raises_typeerror(self) -> None:
        """store() with non-dict metadata raises TypeError."""
        store = InMemoryClientIdentityStore()
        import pytest

        with pytest.raises(TypeError, match="metadata"):
            store.store(VALID_ID, "not-a-dict")  # type: ignore[arg-type]

        with pytest.raises(TypeError):
            store.store(VALID_ID, 42)  # type: ignore[arg-type]

        with pytest.raises(TypeError):
            store.store(VALID_ID, [1, 2])  # type: ignore[arg-type]

    def test_retrieve_invalid_client_id_returns_none(self) -> None:
        """retrieve() with invalid client_id returns None, not an error."""
        store = InMemoryClientIdentityStore()
        assert store.retrieve(INVALID_ID) is None
        assert store.retrieve("") is None
        assert store.retrieve("a" * 31) is None

    def test_clear_invalid_client_id_no_error(self) -> None:
        """clear() with invalid client_id is a no-op, not an error."""
        store = InMemoryClientIdentityStore()
        store.clear(INVALID_ID)  # Should not raise
        store.clear("")  # Should not raise


class TestSynchronousInterface:
    """Tests verifying all methods are synchronous (AC-007-1)."""

    def test_store_is_not_coroutine(self) -> None:
        """store() must not return a coroutine."""
        import inspect

        store = InMemoryClientIdentityStore()
        result = store.store(VALID_ID)
        assert not inspect.isawaitable(result)
        assert result is None

    def test_retrieve_is_not_coroutine(self) -> None:
        """retrieve() must not return a coroutine."""
        import inspect

        store = InMemoryClientIdentityStore()
        store.store(VALID_ID)
        result = store.retrieve(VALID_ID)
        assert not inspect.isawaitable(result)

    def test_clear_is_not_coroutine(self) -> None:
        """clear() must not return a coroutine."""
        import inspect

        store = InMemoryClientIdentityStore()
        result = store.clear(VALID_ID)
        assert not inspect.isawaitable(result)
        assert result is None


class TestAsyncioSafety:
    """Tests verifying asyncio safety (AC-007-3)."""

    async def test_store_operations_are_asyncio_safe(self) -> None:
        """Concurrent asyncio.gather store calls produce consistent final state.

        Calls store() for 50 distinct client IDs concurrently. Verifies that
        all 50 entries are present in the store after gather completes — no
        silent drops or corruption from interleaved execution.
        """
        store = InMemoryClientIdentityStore()
        client_ids = [generate_client_id() for _ in range(50)]

        async def async_store(client_id: str) -> None:
            store.store(client_id, {"cid": client_id})
            await asyncio.sleep(0)  # yield to event loop

        await asyncio.gather(*(async_store(cid) for cid in client_ids))

        for cid in client_ids:
            entry = store.retrieve(cid)
            assert entry is not None, f"Entry missing for {cid}"
            assert entry["metadata"]["cid"] == cid

    async def test_concurrent_retrieve_does_not_corrupt_state(self) -> None:
        """Concurrent retrieve calls don't corrupt the store."""
        store = InMemoryClientIdentityStore()
        store.store(VALID_ID, {"counter": 0})

        async def async_retrieve() -> None:
            store.retrieve(VALID_ID)
            await asyncio.sleep(0)

        await asyncio.gather(*(async_retrieve() for _ in range(20)))

        entry = store.retrieve(VALID_ID)
        assert entry is not None
        assert entry["client_id"] == VALID_ID


class TestProtocolConformance:
    """Tests verifying InMemoryClientIdentityStore satisfies the ClientIdentityStore Protocol."""

    def test_isinstance_of_protocol(self) -> None:
        """InMemoryClientIdentityStore must satisfy ClientIdentityStore Protocol."""
        from stoat_ferret.api.websocket.identity import ClientIdentityStore

        store = InMemoryClientIdentityStore()
        assert isinstance(store, ClientIdentityStore)
