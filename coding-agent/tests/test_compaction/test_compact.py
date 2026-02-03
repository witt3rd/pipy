"""Tests for main compaction functions."""

import pytest

from pipy_coding_agent.settings import CompactionSettings
from pipy_coding_agent.compaction.compact import should_compact


class TestShouldCompact:
    def test_under_threshold(self):
        """Test that compaction is not triggered under threshold."""
        settings = CompactionSettings(
            enabled=True,
            reserve_tokens=16384,
            keep_recent_tokens=20000,
        )

        # Context window of 100k, reserve 16k = threshold at 84k
        # With 50k tokens, should not compact
        result = should_compact(50000, 100000, settings)

        assert result is False

    def test_over_threshold(self):
        """Test that compaction is triggered over threshold."""
        settings = CompactionSettings(
            enabled=True,
            reserve_tokens=16384,
            keep_recent_tokens=20000,
        )

        # Context window of 100k, reserve 16k = threshold at 84k
        # With 90k tokens, should compact
        result = should_compact(90000, 100000, settings)

        assert result is True

    def test_at_threshold(self):
        """Test behavior at exact threshold."""
        settings = CompactionSettings(
            enabled=True,
            reserve_tokens=16384,
            keep_recent_tokens=20000,
        )

        # Exactly at threshold (100k - 16k = 84k)
        result = should_compact(83616, 100000, settings)

        # Should not trigger (not OVER threshold)
        assert result is False

        # One over threshold
        result = should_compact(83617, 100000, settings)
        assert result is True

    def test_disabled(self):
        """Test that disabled compaction never triggers."""
        settings = CompactionSettings(
            enabled=False,
            reserve_tokens=16384,
            keep_recent_tokens=20000,
        )

        # Even with high token count, should not compact
        result = should_compact(200000, 100000, settings)

        assert result is False

    def test_small_context_window(self):
        """Test with small context window."""
        settings = CompactionSettings(
            enabled=True,
            reserve_tokens=4000,
            keep_recent_tokens=8000,
        )

        # 32k context, reserve 4k = threshold at 28k
        result = should_compact(30000, 32000, settings)

        assert result is True

    def test_large_reserve(self):
        """Test with large reserve tokens."""
        settings = CompactionSettings(
            enabled=True,
            reserve_tokens=50000,  # Half the context
            keep_recent_tokens=20000,
        )

        # 100k context, reserve 50k = threshold at 50k
        result = should_compact(51000, 100000, settings)

        assert result is True


class TestCompactionResult:
    def test_result_structure(self):
        """Test CompactionResult dataclass."""
        from pipy_coding_agent.compaction.compact import CompactionResult

        result = CompactionResult(
            summary="Test summary",
            first_kept_entry_id="uuid-123",
            tokens_before=50000,
            details={"read_files": ["/a.txt"], "modified_files": ["/b.txt"]},
        )

        assert result.summary == "Test summary"
        assert result.first_kept_entry_id == "uuid-123"
        assert result.tokens_before == 50000
        assert "/a.txt" in result.details["read_files"]

    def test_result_default_details(self):
        """Test CompactionResult with default details."""
        from pipy_coding_agent.compaction.compact import CompactionResult

        result = CompactionResult(
            summary="Test",
            first_kept_entry_id="uuid",
            tokens_before=1000,
        )

        assert result.details == {}


# Note: The async compact() function would require mocking the LLM,
# which we'll handle in integration tests
