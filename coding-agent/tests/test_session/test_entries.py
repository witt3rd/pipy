"""Tests for session entry utilities."""

import pytest

from pipy_coding_agent.session.entries import (
    CURRENT_SESSION_VERSION,
    generate_id,
    now_iso,
)


class TestGenerateId:
    def test_unique_ids(self):
        """Test that generated IDs are unique."""
        existing = set()
        for _ in range(100):
            new_id = generate_id(existing)
            assert new_id not in existing
            existing.add(new_id)

    def test_id_format(self):
        """Test that IDs are 8 hex characters."""
        new_id = generate_id(set())
        assert len(new_id) == 8
        assert all(c in "0123456789abcdef" for c in new_id)

    def test_avoids_collisions(self):
        """Test that generator avoids existing IDs."""
        # Pre-populate with some IDs
        existing = {"abcd1234", "efgh5678"}
        new_id = generate_id(existing)
        assert new_id not in existing


class TestNowIso:
    def test_format(self):
        """Test ISO timestamp format."""
        ts = now_iso()
        # Should be ISO format with Z suffix
        assert ts.endswith("Z")
        # Should be parseable
        from datetime import datetime
        dt = datetime.fromisoformat(ts.rstrip("Z"))
        assert dt is not None


class TestSessionVersion:
    def test_current_version(self):
        """Test that current version is defined."""
        assert CURRENT_SESSION_VERSION == 3
