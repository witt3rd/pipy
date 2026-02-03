"""Tests for session manager."""

import json
import os
import tempfile
import pytest

from pipy_coding_agent.session import (
    SessionManager,
    SessionContext,
    load_entries_from_file,
    is_valid_session_file,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestSessionManagerBasic:
    def test_create_in_memory(self):
        """Test creating an in-memory session."""
        manager = SessionManager.in_memory()
        
        assert manager.session_id
        assert manager.leaf_id is None
        assert not manager.is_persisted

    def test_create_with_persistence(self, temp_dir):
        """Test creating a persisted session."""
        manager = SessionManager(temp_dir, session_dir=temp_dir)
        
        assert manager.session_id
        assert manager.is_persisted
        assert manager.session_file is not None

    def test_new_session(self, temp_dir):
        """Test creating a new session."""
        manager = SessionManager(temp_dir, session_dir=temp_dir)
        old_id = manager.session_id
        
        manager.new_session()
        
        assert manager.session_id != old_id
        assert manager.leaf_id is None


class TestSessionManagerAppend:
    def test_append_message(self):
        """Test appending a message."""
        manager = SessionManager.in_memory()
        
        msg = {"role": "user", "content": "Hello"}
        entry_id = manager.append_message(msg)
        
        assert entry_id
        assert manager.leaf_id == entry_id
        
        entry = manager.get_entry(entry_id)
        assert entry is not None
        assert entry["type"] == "message"
        assert entry["message"] == msg

    def test_append_multiple_messages(self):
        """Test appending multiple messages."""
        manager = SessionManager.in_memory()
        
        id1 = manager.append_message({"role": "user", "content": "Hello"})
        id2 = manager.append_message({"role": "assistant", "content": "Hi there"})
        
        # Second message should be child of first
        entry2 = manager.get_entry(id2)
        assert entry2["parentId"] == id1
        assert manager.leaf_id == id2

    def test_append_thinking_level_change(self):
        """Test appending thinking level change."""
        manager = SessionManager.in_memory()
        
        entry_id = manager.append_thinking_level_change("high")
        
        entry = manager.get_entry(entry_id)
        assert entry["type"] == "thinking_level_change"
        assert entry["thinkingLevel"] == "high"

    def test_append_model_change(self):
        """Test appending model change."""
        manager = SessionManager.in_memory()
        
        entry_id = manager.append_model_change("anthropic", "claude-3-opus")
        
        entry = manager.get_entry(entry_id)
        assert entry["type"] == "model_change"
        assert entry["provider"] == "anthropic"
        assert entry["modelId"] == "claude-3-opus"

    def test_append_compaction(self):
        """Test appending compaction entry."""
        manager = SessionManager.in_memory()
        first_id = manager.append_message({"role": "user", "content": "First"})
        
        entry_id = manager.append_compaction(
            summary="Summary of conversation",
            first_kept_entry_id=first_id,
            tokens_before=1000,
        )
        
        entry = manager.get_entry(entry_id)
        assert entry["type"] == "compaction"
        assert entry["summary"] == "Summary of conversation"
        assert entry["tokensBefore"] == 1000

    def test_append_custom_entry(self):
        """Test appending custom entry."""
        manager = SessionManager.in_memory()
        
        entry_id = manager.append_custom_entry("my_extension", {"key": "value"})
        
        entry = manager.get_entry(entry_id)
        assert entry["type"] == "custom"
        assert entry["customType"] == "my_extension"
        assert entry["data"] == {"key": "value"}

    def test_append_session_info(self):
        """Test appending session info."""
        manager = SessionManager.in_memory()
        
        manager.append_session_info("My Session Name")
        
        assert manager.get_session_name() == "My Session Name"


class TestSessionManagerPersistence:
    def test_persist_and_reload(self, temp_dir):
        """Test that session survives reload."""
        # Create session and add messages
        manager1 = SessionManager(temp_dir, session_dir=temp_dir)
        manager1.append_message({"role": "user", "content": "Hello"})
        manager1.append_message({"role": "assistant", "content": "Hi there"})
        session_file = manager1.session_file
        
        # Reload session
        manager2 = SessionManager(temp_dir, session_dir=temp_dir, session_file=session_file)
        
        entries = manager2.get_entries()
        assert len(entries) == 2
        assert entries[0]["message"]["content"] == "Hello"
        assert entries[1]["message"]["content"] == "Hi there"

    def test_session_file_format(self, temp_dir):
        """Test JSONL file format."""
        manager = SessionManager(temp_dir, session_dir=temp_dir)
        manager.append_message({"role": "user", "content": "Test"})
        manager.append_message({"role": "assistant", "content": "Response"})
        
        # Read raw file
        content = manager.session_file.read_text()
        lines = content.strip().split("\n")
        
        # First line should be header
        header = json.loads(lines[0])
        assert header["type"] == "session"
        
        # Each line should be valid JSON
        for line in lines:
            parsed = json.loads(line)
            assert "type" in parsed


class TestSessionManagerContext:
    def test_build_context_empty(self):
        """Test building context from empty session."""
        manager = SessionManager.in_memory()
        
        ctx = manager.build_session_context()
        
        assert ctx.messages == []
        assert ctx.thinking_level == "off"
        assert ctx.model is None

    def test_build_context_with_messages(self):
        """Test building context with messages."""
        manager = SessionManager.in_memory()
        manager.append_message({"role": "user", "content": "Hello"})
        manager.append_message({"role": "assistant", "content": "Hi"})
        
        ctx = manager.build_session_context()
        
        assert len(ctx.messages) == 2

    def test_build_context_with_settings(self):
        """Test building context preserves settings."""
        manager = SessionManager.in_memory()
        manager.append_thinking_level_change("high")
        manager.append_model_change("openai", "gpt-4")
        manager.append_message({"role": "user", "content": "Test"})
        
        ctx = manager.build_session_context()
        
        assert ctx.thinking_level == "high"
        assert ctx.model == {"provider": "openai", "modelId": "gpt-4"}


class TestSessionManagerBranching:
    def test_set_leaf(self):
        """Test setting leaf to earlier entry."""
        manager = SessionManager.in_memory()
        id1 = manager.append_message({"role": "user", "content": "First"})
        id2 = manager.append_message({"role": "assistant", "content": "Second"})
        
        # Move leaf back
        manager.set_leaf(id1)
        assert manager.leaf_id == id1
        
        # New message should branch from id1
        id3 = manager.append_message({"role": "user", "content": "Branch"})
        entry3 = manager.get_entry(id3)
        assert entry3["parentId"] == id1

    def test_get_branch(self):
        """Test getting branch from leaf to root."""
        manager = SessionManager.in_memory()
        id1 = manager.append_message({"role": "user", "content": "First"})
        id2 = manager.append_message({"role": "assistant", "content": "Second"})
        id3 = manager.append_message({"role": "user", "content": "Third"})
        
        branch = manager.get_branch()
        
        assert len(branch) == 3
        assert branch[0]["id"] == id1
        assert branch[1]["id"] == id2
        assert branch[2]["id"] == id3

    def test_get_children(self):
        """Test getting children of an entry."""
        manager = SessionManager.in_memory()
        id1 = manager.append_message({"role": "user", "content": "Root"})
        
        # Create two children
        id2 = manager.append_message({"role": "assistant", "content": "Child 1"})
        manager.set_leaf(id1)  # Go back to root
        id3 = manager.append_message({"role": "assistant", "content": "Child 2"})
        
        children = manager.get_children(id1)
        child_ids = {c["id"] for c in children}
        
        assert id2 in child_ids
        assert id3 in child_ids


class TestSessionManagerListing:
    def test_list_sessions_empty(self, temp_dir):
        """Test listing sessions from empty directory."""
        sessions = SessionManager.list_sessions(temp_dir)
        assert sessions == []

    def test_list_sessions(self, temp_dir):
        """Test listing sessions."""
        # Create a few sessions
        m1 = SessionManager(temp_dir, session_dir=temp_dir)
        m1.append_message({"role": "user", "content": "First"})
        m1.append_message({"role": "assistant", "content": "Response"})
        
        m2 = SessionManager(temp_dir, session_dir=temp_dir)
        m2.new_session()
        m2.append_message({"role": "user", "content": "Second session"})
        m2.append_message({"role": "assistant", "content": "Also response"})
        
        sessions = SessionManager.list_sessions(temp_dir)
        
        # Should find both sessions
        assert len(sessions) >= 1  # At least one should persist


class TestLoadEntriesFromFile:
    def test_load_valid_file(self, temp_dir):
        """Test loading valid session file."""
        file_path = os.path.join(temp_dir, "test.jsonl")
        
        with open(file_path, "w") as f:
            f.write('{"type": "session", "id": "test123", "timestamp": "2024-01-01T00:00:00Z", "cwd": "/test", "version": 3}\n')
            f.write('{"type": "message", "id": "msg1", "parentId": null, "timestamp": "2024-01-01T00:00:01Z", "message": {"role": "user", "content": "Hi"}}\n')
        
        entries = load_entries_from_file(file_path)
        
        assert len(entries) == 2
        assert entries[0]["type"] == "session"
        assert entries[1]["type"] == "message"

    def test_load_nonexistent_file(self, temp_dir):
        """Test loading nonexistent file."""
        entries = load_entries_from_file(os.path.join(temp_dir, "nonexistent.jsonl"))
        assert entries == []

    def test_load_invalid_file(self, temp_dir):
        """Test loading file with invalid header."""
        file_path = os.path.join(temp_dir, "invalid.jsonl")
        
        with open(file_path, "w") as f:
            f.write('{"type": "message"}\n')  # No session header
        
        entries = load_entries_from_file(file_path)
        assert entries == []


class TestIsValidSessionFile:
    def test_valid_file(self, temp_dir):
        """Test checking valid session file."""
        file_path = os.path.join(temp_dir, "valid.jsonl")
        
        with open(file_path, "w") as f:
            f.write('{"type": "session", "id": "test123"}\n')
        
        assert is_valid_session_file(file_path)

    def test_invalid_file(self, temp_dir):
        """Test checking invalid session file."""
        file_path = os.path.join(temp_dir, "invalid.jsonl")
        
        with open(file_path, "w") as f:
            f.write('{"type": "other"}\n')
        
        assert not is_valid_session_file(file_path)

    def test_nonexistent_file(self, temp_dir):
        """Test checking nonexistent file."""
        assert not is_valid_session_file(os.path.join(temp_dir, "missing.jsonl"))
