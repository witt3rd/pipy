"""Tests for session context building."""

import pytest

from pipy_coding_agent.session.context import (
    SessionContext,
    build_session_context,
    create_compaction_summary_message,
    create_branch_summary_message,
)
from pipy_coding_agent.session.entries import (
    COMPACTION_SUMMARY_PREFIX,
    BRANCH_SUMMARY_PREFIX,
)


class TestCreateCompactionSummaryMessage:
    def test_creates_user_message(self):
        """Test that compaction summary creates a user message."""
        msg = create_compaction_summary_message(
            summary="Summary text",
            tokens_before=1000,
            timestamp="2024-01-01T00:00:00Z",
        )
        
        assert msg.role == "user"
        content = msg.content[0].text
        assert "Summary text" in content
        assert COMPACTION_SUMMARY_PREFIX in content


class TestCreateBranchSummaryMessage:
    def test_creates_user_message(self):
        """Test that branch summary creates a user message."""
        msg = create_branch_summary_message(
            summary="Branch summary",
            from_id="entry123",
            timestamp="2024-01-01T00:00:00Z",
        )
        
        assert msg.role == "user"
        content = msg.content[0].text
        assert "Branch summary" in content
        assert BRANCH_SUMMARY_PREFIX in content


class TestBuildSessionContext:
    def test_empty_entries(self):
        """Test building context from empty entries."""
        ctx = build_session_context([])
        
        assert ctx.messages == []
        assert ctx.thinking_level == "off"
        assert ctx.model is None

    def test_single_message(self):
        """Test building context with single message."""
        entries = [
            {
                "type": "message",
                "id": "msg1",
                "parentId": None,
                "timestamp": "2024-01-01T00:00:00Z",
                "message": {"role": "user", "content": "Hello"},
            }
        ]
        
        ctx = build_session_context(entries)
        
        assert len(ctx.messages) == 1
        assert ctx.messages[0]["content"] == "Hello"

    def test_chain_of_messages(self):
        """Test building context with message chain."""
        entries = [
            {
                "type": "message",
                "id": "msg1",
                "parentId": None,
                "timestamp": "2024-01-01T00:00:00Z",
                "message": {"role": "user", "content": "Hello"},
            },
            {
                "type": "message",
                "id": "msg2",
                "parentId": "msg1",
                "timestamp": "2024-01-01T00:00:01Z",
                "message": {"role": "assistant", "content": "Hi there"},
            },
            {
                "type": "message",
                "id": "msg3",
                "parentId": "msg2",
                "timestamp": "2024-01-01T00:00:02Z",
                "message": {"role": "user", "content": "How are you?"},
            },
        ]
        
        ctx = build_session_context(entries)
        
        assert len(ctx.messages) == 3
        assert ctx.messages[0]["content"] == "Hello"
        assert ctx.messages[1]["content"] == "Hi there"
        assert ctx.messages[2]["content"] == "How are you?"

    def test_extracts_thinking_level(self):
        """Test that thinking level is extracted."""
        entries = [
            {
                "type": "thinking_level_change",
                "id": "tl1",
                "parentId": None,
                "timestamp": "2024-01-01T00:00:00Z",
                "thinkingLevel": "high",
            },
            {
                "type": "message",
                "id": "msg1",
                "parentId": "tl1",
                "timestamp": "2024-01-01T00:00:01Z",
                "message": {"role": "user", "content": "Test"},
            },
        ]
        
        ctx = build_session_context(entries)
        
        assert ctx.thinking_level == "high"

    def test_extracts_model(self):
        """Test that model is extracted from model_change."""
        entries = [
            {
                "type": "model_change",
                "id": "mc1",
                "parentId": None,
                "timestamp": "2024-01-01T00:00:00Z",
                "provider": "anthropic",
                "modelId": "claude-3-opus",
            },
            {
                "type": "message",
                "id": "msg1",
                "parentId": "mc1",
                "timestamp": "2024-01-01T00:00:01Z",
                "message": {"role": "user", "content": "Test"},
            },
        ]
        
        ctx = build_session_context(entries)
        
        assert ctx.model == {"provider": "anthropic", "modelId": "claude-3-opus"}

    def test_handles_compaction(self):
        """Test that compaction is handled correctly."""
        entries = [
            {
                "type": "message",
                "id": "msg1",
                "parentId": None,
                "timestamp": "2024-01-01T00:00:00Z",
                "message": {"role": "user", "content": "Old message 1"},
            },
            {
                "type": "message",
                "id": "msg2",
                "parentId": "msg1",
                "timestamp": "2024-01-01T00:00:01Z",
                "message": {"role": "assistant", "content": "Old response"},
            },
            {
                "type": "message",
                "id": "msg3",
                "parentId": "msg2",
                "timestamp": "2024-01-01T00:00:02Z",
                "message": {"role": "user", "content": "Kept message"},
            },
            {
                "type": "compaction",
                "id": "comp1",
                "parentId": "msg3",
                "timestamp": "2024-01-01T00:00:03Z",
                "summary": "Summary of old messages",
                "firstKeptEntryId": "msg3",
                "tokensBefore": 1000,
                "details": None,
                "fromHook": None,
            },
            {
                "type": "message",
                "id": "msg4",
                "parentId": "comp1",
                "timestamp": "2024-01-01T00:00:04Z",
                "message": {"role": "assistant", "content": "New response"},
            },
        ]
        
        ctx = build_session_context(entries)
        
        # Should have: summary + kept message + new message
        assert len(ctx.messages) == 3
        # First should be summary (UserMessage object)
        first_msg = ctx.messages[0]
        assert "Summary of old messages" in first_msg.content[0].text
        # Second should be kept message (dict from entry)
        assert ctx.messages[1]["content"] == "Kept message"
        # Third should be new message (dict from entry)
        assert ctx.messages[2]["content"] == "New response"

    def test_walks_from_specific_leaf(self):
        """Test walking from a specific leaf ID."""
        entries = [
            {
                "type": "message",
                "id": "msg1",
                "parentId": None,
                "timestamp": "2024-01-01T00:00:00Z",
                "message": {"role": "user", "content": "Root"},
            },
            {
                "type": "message",
                "id": "msg2",
                "parentId": "msg1",
                "timestamp": "2024-01-01T00:00:01Z",
                "message": {"role": "assistant", "content": "Branch 1"},
            },
            {
                "type": "message",
                "id": "msg3",
                "parentId": "msg1",  # Also child of msg1 (different branch)
                "timestamp": "2024-01-01T00:00:02Z",
                "message": {"role": "assistant", "content": "Branch 2"},
            },
        ]
        
        # Walk to msg2 (branch 1)
        ctx1 = build_session_context(entries, leaf_id="msg2")
        assert len(ctx1.messages) == 2
        assert ctx1.messages[1]["content"] == "Branch 1"
        
        # Walk to msg3 (branch 2)
        ctx2 = build_session_context(entries, leaf_id="msg3")
        assert len(ctx2.messages) == 2
        assert ctx2.messages[1]["content"] == "Branch 2"
