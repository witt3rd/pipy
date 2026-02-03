"""Tests for edit tool."""

import os
import tempfile
import pytest

from pipy_coding_agent.tools.edit import create_edit_tool


@pytest.fixture
def temp_dir():
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test file
        with open(os.path.join(tmpdir, "test.txt"), "w") as f:
            f.write("Hello, World!\nLine 2\nLine 3\n")
        
        # Create file with multiple occurrences
        with open(os.path.join(tmpdir, "duplicates.txt"), "w") as f:
            f.write("foo bar foo\nfoo baz foo\n")
        
        yield tmpdir


class TestEditTool:
    @pytest.mark.asyncio
    async def test_simple_replacement(self, temp_dir):
        tool = create_edit_tool(temp_dir)
        result = await tool.execute("call_1", {
            "path": "test.txt",
            "oldText": "Hello, World!",
            "newText": "Greetings, Universe!"
        })
        
        assert "Successfully replaced" in result.content[0].text
        assert result.details is not None
        assert result.details.diff is not None
        
        # Verify file was changed
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path) as f:
            content = f.read()
            assert "Greetings, Universe!" in content
            assert "Hello, World!" not in content

    @pytest.mark.asyncio
    async def test_multiline_replacement(self, temp_dir):
        tool = create_edit_tool(temp_dir)
        await tool.execute("call_1", {
            "path": "test.txt",
            "oldText": "Hello, World!\nLine 2",
            "newText": "New Header\nNew Line 2"
        })
        
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path) as f:
            content = f.read()
            assert "New Header\nNew Line 2" in content

    @pytest.mark.asyncio
    async def test_text_not_found(self, temp_dir):
        tool = create_edit_tool(temp_dir)
        
        with pytest.raises(RuntimeError, match="Could not find"):
            await tool.execute("call_1", {
                "path": "test.txt",
                "oldText": "Nonexistent text",
                "newText": "Replacement"
            })

    @pytest.mark.asyncio
    async def test_file_not_found(self, temp_dir):
        tool = create_edit_tool(temp_dir)
        
        with pytest.raises(RuntimeError, match="File not found"):
            await tool.execute("call_1", {
                "path": "nonexistent.txt",
                "oldText": "foo",
                "newText": "bar"
            })

    @pytest.mark.asyncio
    async def test_multiple_occurrences_rejected(self, temp_dir):
        tool = create_edit_tool(temp_dir)
        
        with pytest.raises(RuntimeError, match="occurrences"):
            await tool.execute("call_1", {
                "path": "duplicates.txt",
                "oldText": "foo",
                "newText": "qux"
            })

    @pytest.mark.asyncio
    async def test_unique_context_for_duplicate(self, temp_dir):
        """Test that providing more context makes duplicate text unique."""
        tool = create_edit_tool(temp_dir)
        
        # This should work because "foo bar foo" is unique
        result = await tool.execute("call_1", {
            "path": "duplicates.txt",
            "oldText": "foo bar foo",
            "newText": "qux bar qux"
        })
        
        assert "Successfully replaced" in result.content[0].text

    @pytest.mark.asyncio
    async def test_identical_replacement_rejected(self, temp_dir):
        tool = create_edit_tool(temp_dir)
        
        with pytest.raises(RuntimeError, match="No changes"):
            await tool.execute("call_1", {
                "path": "test.txt",
                "oldText": "Hello, World!",
                "newText": "Hello, World!"
            })

    @pytest.mark.asyncio
    async def test_fuzzy_match_trailing_whitespace(self, temp_dir):
        """Test that fuzzy matching handles trailing whitespace."""
        # Create file with trailing whitespace
        file_path = os.path.join(temp_dir, "whitespace.txt")
        with open(file_path, "w") as f:
            f.write("Hello   \nWorld\n")
        
        tool = create_edit_tool(temp_dir)
        # Should match even without trailing spaces
        result = await tool.execute("call_1", {
            "path": "whitespace.txt",
            "oldText": "Hello\nWorld",
            "newText": "Hi\nThere"
        })
        
        assert "Successfully replaced" in result.content[0].text


class TestEditToolLineEndings:
    @pytest.mark.asyncio
    async def test_crlf_preservation(self, temp_dir):
        """Test that CRLF line endings are preserved."""
        file_path = os.path.join(temp_dir, "crlf.txt")
        with open(file_path, "wb") as f:
            f.write(b"Line 1\r\nLine 2\r\nLine 3\r\n")
        
        tool = create_edit_tool(temp_dir)
        await tool.execute("call_1", {
            "path": "crlf.txt",
            "oldText": "Line 2",
            "newText": "Modified Line 2"
        })
        
        with open(file_path, "rb") as f:
            content = f.read()
            # Should still have CRLF
            assert b"\r\n" in content
            assert b"Modified Line 2" in content

    @pytest.mark.asyncio
    async def test_bom_preservation(self, temp_dir):
        """Test that UTF-8 BOM is preserved."""
        file_path = os.path.join(temp_dir, "bom.txt")
        with open(file_path, "wb") as f:
            f.write(b"\xef\xbb\xbfHello World\n")  # UTF-8 BOM + content
        
        tool = create_edit_tool(temp_dir)
        await tool.execute("call_1", {
            "path": "bom.txt",
            "oldText": "Hello",
            "newText": "Hi"
        })
        
        with open(file_path, "rb") as f:
            content = f.read()
            # Should still have BOM
            assert content.startswith(b"\xef\xbb\xbf")
            assert b"Hi World" in content
