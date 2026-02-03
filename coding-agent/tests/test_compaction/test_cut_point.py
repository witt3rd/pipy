"""Tests for cut point detection."""

import pytest

from pipy_ai import Message, AssistantMessage

from pipy_coding_agent.compaction.cut_point import (
    find_cut_point,
    find_turn_start_index,
    find_valid_cut_points,
    CutPointResult,
)


def make_user_entry(content: str, entry_id: str | None = None) -> dict:
    """Helper to create a user message entry."""
    return {
        "type": "message",
        "id": entry_id or f"id-{content[:10]}",
        "parentId": None,
        "timestamp": "2024-01-01T00:00:00Z",
        "message": {"role": "user", "content": content},
    }


def make_assistant_entry(content: str, entry_id: str | None = None) -> dict:
    """Helper to create an assistant message entry."""
    return {
        "type": "message",
        "id": entry_id or f"id-{content[:10]}",
        "parentId": None,
        "timestamp": "2024-01-01T00:00:00Z",
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": content}],
            "stop_reason": "end_turn",
        },
    }


def make_tool_result_entry(content: str, entry_id: str | None = None) -> dict:
    """Helper to create a tool result entry."""
    return {
        "type": "message",
        "id": entry_id or "id-tool",
        "parentId": None,
        "timestamp": "2024-01-01T00:00:00Z",
        "message": {"role": "tool", "content": content, "tool_use_id": "123"},
    }


class TestFindValidCutPoints:
    def test_user_and_assistant(self):
        """Test finding cut points at user and assistant messages."""
        entries = [
            make_user_entry("User 1"),
            make_assistant_entry("Assistant 1"),
            make_user_entry("User 2"),
            make_assistant_entry("Assistant 2"),
        ]

        cut_points = find_valid_cut_points(entries, 0, 4)

        assert cut_points == [0, 1, 2, 3]

    def test_skip_tool_results(self):
        """Test that tool results are skipped."""
        entries = [
            make_user_entry("User 1"),
            make_assistant_entry("Calling tool"),
            make_tool_result_entry("Tool output"),
            make_assistant_entry("Got result"),
        ]

        cut_points = find_valid_cut_points(entries, 0, 4)

        # Tool result at index 2 should be skipped
        assert cut_points == [0, 1, 3]

    def test_range_limits(self):
        """Test that range limits are respected."""
        entries = [
            make_user_entry("User 1"),
            make_assistant_entry("Assistant 1"),
            make_user_entry("User 2"),
            make_assistant_entry("Assistant 2"),
        ]

        cut_points = find_valid_cut_points(entries, 1, 3)

        # Only indices 1 and 2
        assert cut_points == [1, 2]


class TestFindTurnStartIndex:
    def test_find_user_start(self):
        """Test finding turn start at user message."""
        entries = [
            make_user_entry("User 1"),
            make_assistant_entry("Assistant 1"),
            make_user_entry("User 2"),
            make_assistant_entry("Assistant 2"),
        ]

        # Turn containing index 3 (assistant) starts at index 2 (user)
        result = find_turn_start_index(entries, 3, 0)

        assert result == 2

    def test_at_user_message(self):
        """Test when already at user message."""
        entries = [
            make_user_entry("User 1"),
            make_assistant_entry("Assistant 1"),
        ]

        result = find_turn_start_index(entries, 0, 0)

        assert result == 0

    def test_no_turn_start(self):
        """Test when no turn start found."""
        entries = [
            make_assistant_entry("Assistant only"),
        ]

        result = find_turn_start_index(entries, 0, 0)

        # No user message before
        assert result == -1


class TestFindCutPoint:
    def test_keep_all_under_budget(self):
        """Test that all messages are kept when under budget."""
        entries = [
            make_user_entry("Short"),  # ~2 tokens
            make_assistant_entry("Also short"),  # ~3 tokens
        ]

        result = find_cut_point(entries, 0, 2, keep_recent_tokens=1000)

        # Should keep from first entry
        assert result.first_kept_entry_index == 0
        assert not result.is_split_turn

    def test_cut_at_budget(self):
        """Test cutting when budget is exceeded."""
        # Create messages with known sizes
        entries = [
            make_user_entry("x" * 100),  # ~25 tokens
            make_assistant_entry("y" * 100),  # ~25 tokens
            make_user_entry("z" * 100),  # ~25 tokens
            make_assistant_entry("w" * 100),  # ~25 tokens
        ]

        # Keep only ~50 tokens (last 2 messages)
        result = find_cut_point(entries, 0, 4, keep_recent_tokens=50)

        # Should cut, keeping later entries
        assert result.first_kept_entry_index >= 1

    def test_no_cut_points(self):
        """Test with no valid cut points."""
        entries: list = []

        result = find_cut_point(entries, 0, 0, keep_recent_tokens=100)

        assert result.first_kept_entry_index == 0
        assert not result.is_split_turn

    def test_split_turn_detection(self):
        """Test detecting split turns."""
        entries = [
            make_user_entry("User question"),
            make_assistant_entry("x" * 400),  # Long response
        ]

        # Try to keep only ~50 tokens - will cut at assistant
        result = find_cut_point(entries, 0, 2, keep_recent_tokens=50)

        # If cut at assistant (index 1), it's a split turn
        if result.first_kept_entry_index == 1:
            assert result.is_split_turn
            assert result.turn_start_index == 0

    def test_respect_boundary_start(self):
        """Test respecting boundary start."""
        entries = [
            make_user_entry("Old message"),
            {
                "type": "compaction",
                "id": "compact-1",
                "parentId": None,
                "timestamp": "2024-01-01T00:00:00Z",
                "summary": "Previous summary",
                "firstKeptEntryId": "next-id",
                "tokensBefore": 5000,
                "details": None,
                "fromHook": None,
            },
            make_user_entry("New message"),
            make_assistant_entry("Response"),
        ]

        # Start from index 2 (after compaction)
        result = find_cut_point(entries, 2, 4, keep_recent_tokens=1000)

        assert result.first_kept_entry_index >= 2
