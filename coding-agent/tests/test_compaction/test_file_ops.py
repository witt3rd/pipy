"""Tests for file operation tracking."""

import pytest

from pipy_ai import UserMessage, AssistantMessage

from pipy_coding_agent.compaction.file_ops import (
    FileOperations,
    create_file_ops,
    extract_file_ops_from_message,
    compute_file_lists,
    format_file_operations,
)


class TestFileOperations:
    def test_create_empty(self):
        """Test creating empty file operations."""
        ops = create_file_ops()

        assert len(ops.read) == 0
        assert len(ops.written) == 0
        assert len(ops.edited) == 0

    def test_add_files(self):
        """Test adding files to operations."""
        ops = FileOperations()
        ops.read.add("/path/to/file.txt")
        ops.written.add("/path/to/new.txt")
        ops.edited.add("/path/to/edit.txt")

        assert "/path/to/file.txt" in ops.read
        assert "/path/to/new.txt" in ops.written
        assert "/path/to/edit.txt" in ops.edited


class TestExtractFileOpsFromMessage:
    def test_extract_read(self):
        """Test extracting Read tool calls."""
        msg = AssistantMessage(
            role="assistant",
            content=[{
                "type": "toolCall",
                "id": "123",
                "name": "Read",
                "arguments": {"path": "/test/file.txt"},
            }],
            stop_reason="toolUse",
        )
        ops = create_file_ops()

        extract_file_ops_from_message(msg, ops)

        assert "/test/file.txt" in ops.read

    def test_extract_write(self):
        """Test extracting Write tool calls."""
        msg = AssistantMessage(
            role="assistant",
            content=[{
                "type": "toolCall",
                "id": "123",
                "name": "Write",
                "arguments": {"path": "/test/new.txt", "content": "hello"},
            }],
            stop_reason="toolUse",
        )
        ops = create_file_ops()

        extract_file_ops_from_message(msg, ops)

        assert "/test/new.txt" in ops.written

    def test_extract_edit(self):
        """Test extracting Edit tool calls."""
        msg = AssistantMessage(
            role="assistant",
            content=[{
                "type": "toolCall",
                "id": "123",
                "name": "Edit",
                "arguments": {"path": "/test/edit.txt", "oldText": "a", "newText": "b"},
            }],
            stop_reason="toolUse",
        )
        ops = create_file_ops()

        extract_file_ops_from_message(msg, ops)

        assert "/test/edit.txt" in ops.edited

    def test_extract_multiple(self):
        """Test extracting multiple tool calls."""
        msg = AssistantMessage(
            role="assistant",
            content=[
                {
                    "type": "toolCall",
                    "id": "1",
                    "name": "Read",
                    "arguments": {"path": "/a.txt"},
                },
                {
                    "type": "toolCall",
                    "id": "2",
                    "name": "Write",
                    "arguments": {"path": "/b.txt", "content": "x"},
                },
                {
                    "type": "toolCall",
                    "id": "3",
                    "name": "Edit",
                    "arguments": {"path": "/c.txt", "oldText": "x", "newText": "y"},
                },
            ],
            stop_reason="toolUse",
        )
        ops = create_file_ops()

        extract_file_ops_from_message(msg, ops)

        assert "/a.txt" in ops.read
        assert "/b.txt" in ops.written
        assert "/c.txt" in ops.edited

    def test_skip_non_assistant(self):
        """Test that non-assistant messages are skipped."""
        msg = UserMessage(role="user", content="Read /test.txt")
        ops = create_file_ops()

        extract_file_ops_from_message(msg, ops)

        assert len(ops.read) == 0

    def test_skip_non_tool_blocks(self):
        """Test that non-tool blocks are skipped."""
        msg = AssistantMessage(
            role="assistant",
            content=[
                {"type": "text", "text": "Reading file..."},
            ],
            stop_reason="stop",
        )
        ops = create_file_ops()

        extract_file_ops_from_message(msg, ops)

        assert len(ops.read) == 0


class TestComputeFileLists:
    def test_read_only(self):
        """Test files only read."""
        ops = FileOperations()
        ops.read.add("/a.txt")
        ops.read.add("/b.txt")

        read_files, modified_files = compute_file_lists(ops)

        assert read_files == ["/a.txt", "/b.txt"]
        assert modified_files == []

    def test_modified_only(self):
        """Test files only modified."""
        ops = FileOperations()
        ops.written.add("/new.txt")
        ops.edited.add("/edit.txt")

        read_files, modified_files = compute_file_lists(ops)

        assert read_files == []
        assert "/edit.txt" in modified_files
        assert "/new.txt" in modified_files

    def test_read_then_modified(self):
        """Test files read then modified."""
        ops = FileOperations()
        ops.read.add("/file.txt")
        ops.edited.add("/file.txt")  # Same file edited

        read_files, modified_files = compute_file_lists(ops)

        # Should only appear in modified, not read
        assert read_files == []
        assert "/file.txt" in modified_files

    def test_sorted_output(self):
        """Test output is sorted."""
        ops = FileOperations()
        ops.read.add("/z.txt")
        ops.read.add("/a.txt")
        ops.read.add("/m.txt")

        read_files, modified_files = compute_file_lists(ops)

        assert read_files == ["/a.txt", "/m.txt", "/z.txt"]


class TestFormatFileOperations:
    def test_empty(self):
        """Test formatting empty lists."""
        result = format_file_operations([], [])
        assert result == ""

    def test_read_only(self):
        """Test formatting read files only."""
        result = format_file_operations(["/a.txt", "/b.txt"], [])

        assert "<read-files>" in result
        assert "/a.txt" in result
        assert "/b.txt" in result
        assert "<modified-files>" not in result

    def test_modified_only(self):
        """Test formatting modified files only."""
        result = format_file_operations([], ["/new.txt"])

        assert "<modified-files>" in result
        assert "/new.txt" in result
        assert "<read-files>" not in result

    def test_both(self):
        """Test formatting both read and modified."""
        result = format_file_operations(["/read.txt"], ["/write.txt"])

        assert "<read-files>" in result
        assert "/read.txt" in result
        assert "<modified-files>" in result
        assert "/write.txt" in result
