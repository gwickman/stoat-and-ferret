"""Unit tests for client identity token generation and validation (Feature 002, BL-315).

Covers generate_client_id() and is_valid_client_id() from
stoat_ferret.api.websocket.identity.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from stoat_ferret.api.websocket.identity import generate_client_id, is_valid_client_id


class TestGenerateClientId:
    """Tests for generate_client_id()."""

    def test_generate_client_id_returns_string(self) -> None:
        """generate_client_id() must return a str."""
        token = generate_client_id()
        assert isinstance(token, str)

    def test_generate_client_id_returns_32_char(self) -> None:
        """generate_client_id() must return exactly 32 characters."""
        token = generate_client_id()
        assert len(token) == 32

    def test_generate_client_id_returns_lowercase_hex(self) -> None:
        """generate_client_id() must return only lowercase hex characters."""
        token = generate_client_id()
        assert all(c in "0123456789abcdef" for c in token)

    def test_generate_client_id_produces_different_values(self) -> None:
        """Multiple calls to generate_client_id() should produce distinct tokens."""
        tokens = {generate_client_id() for _ in range(20)}
        assert len(tokens) == 20

    def test_generate_client_id_passes_validation(self) -> None:
        """Tokens from generate_client_id() must pass is_valid_client_id()."""
        for _ in range(10):
            token = generate_client_id()
            assert is_valid_client_id(token), f"Generated token failed validation: {token}"


class TestIsValidClientId:
    """Tests for is_valid_client_id()."""

    def test_accepts_valid_32_char_hex(self) -> None:
        """Valid 32-char lowercase hex tokens are accepted."""
        assert is_valid_client_id("a" * 32) is True
        assert is_valid_client_id("0" * 32) is True
        assert is_valid_client_id("0123456789abcdef" * 2) is True

    def test_accepts_generated_tokens(self) -> None:
        """Tokens produced by generate_client_id() are accepted."""
        for _ in range(5):
            assert is_valid_client_id(generate_client_id()) is True

    def test_rejects_empty_string(self) -> None:
        """Empty string is rejected."""
        assert is_valid_client_id("") is False

    def test_rejects_none(self) -> None:
        """None is rejected (returns False, not TypeError)."""
        assert is_valid_client_id(None) is False

    def test_rejects_uppercase_hex(self) -> None:
        """Uppercase hex characters are rejected."""
        assert is_valid_client_id("A" * 32) is False
        assert is_valid_client_id("ABCDEF0123456789" * 2) is False

    def test_rejects_too_short(self) -> None:
        """Strings shorter than 32 chars are rejected."""
        assert is_valid_client_id("a" * 31) is False
        assert is_valid_client_id("a" * 16) is False
        assert is_valid_client_id("a") is False

    def test_rejects_too_long(self) -> None:
        """Strings longer than 32 chars are rejected."""
        assert is_valid_client_id("a" * 33) is False
        assert is_valid_client_id("a" * 64) is False

    def test_rejects_non_hex_chars(self) -> None:
        """Non-hex characters (including dashes, g-z) are rejected."""
        assert is_valid_client_id("g" * 32) is False
        assert is_valid_client_id("z" * 32) is False
        # UUID with dashes — 36 chars, also wrong length
        assert is_valid_client_id("550e8400-e29b-41d4-a716-446655440000") is False
        # 32 chars but with a dash in the middle
        assert is_valid_client_id("a" * 16 + "-" + "a" * 15) is False

    def test_rejects_int(self) -> None:
        """Integer input is rejected."""
        assert is_valid_client_id(12345) is False

    def test_rejects_list(self) -> None:
        """List input is rejected."""
        assert is_valid_client_id(["a" * 32]) is False

    def test_rejects_dict(self) -> None:
        """Dict input is rejected."""
        assert is_valid_client_id({"token": "a" * 32}) is False

    def test_rejects_bytes(self) -> None:
        """Bytes input is rejected."""
        assert is_valid_client_id(b"a" * 32) is False

    @given(st.text(min_size=0, max_size=64))
    @settings(max_examples=200)
    def test_property_only_valid_format_accepted(self, token: str) -> None:
        """Only 32-char lowercase hex strings pass validation."""
        result = is_valid_client_id(token)
        if result:
            assert isinstance(token, str)
            assert len(token) == 32
            assert all(c in "0123456789abcdef" for c in token)
        else:
            assert not (
                isinstance(token, str)
                and len(token) == 32
                and all(c in "0123456789abcdef" for c in token)
            )
