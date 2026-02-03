"""Tests for write tool."""

import os
import tempfile
import pytest

from pipy_coding_agent.tools.write import create_write_tool


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestWriteTool:
    @pytest.mark.asyncio
    async def test_write_new_file(self, temp_dir):
        tool = create_write_tool(temp_dir)
        result = await tool.execute("call_1", {
            "path": "new_file.txt",
            "content": "Hello, World!"
        })
        
        assert "Successfully wrote" in result.content[0].text
        assert "13 bytes" in result.content[0].text
        
        # Verify file was created
        file_path = os.path.join(temp_dir, "new_file.txt")
        assert os.path.exists(file_path)
        with open(file_path) as f:
            assert f.read() == "Hello, World!"

    @pytest.mark.asyncio
    async def test_overwrite_existing_file(self, temp_dir):
        # Create initial file
        file_path = os.path.join(temp_dir, "existing.txt")
        with open(file_path, "w") as f:
            f.write("Original content")
        
        tool = create_write_tool(temp_dir)
        await tool.execute("call_1", {
            "path": "existing.txt",
            "content": "New content"
        })
        
        with open(file_path) as f:
            assert f.read() == "New content"

    @pytest.mark.asyncio
    async def test_create_parent_directories(self, temp_dir):
        tool = create_write_tool(temp_dir)
        await tool.execute("call_1", {
            "path": "deep/nested/dir/file.txt",
            "content": "Nested content"
        })
        
        file_path = os.path.join(temp_dir, "deep", "nested", "dir", "file.txt")
        assert os.path.exists(file_path)
        with open(file_path) as f:
            assert f.read() == "Nested content"

    @pytest.mark.asyncio
    async def test_write_empty_file(self, temp_dir):
        tool = create_write_tool(temp_dir)
        result = await tool.execute("call_1", {
            "path": "empty.txt",
            "content": ""
        })
        
        assert "0 bytes" in result.content[0].text
        
        file_path = os.path.join(temp_dir, "empty.txt")
        assert os.path.exists(file_path)
        with open(file_path) as f:
            assert f.read() == ""

    @pytest.mark.asyncio
    async def test_write_multiline_content(self, temp_dir):
        tool = create_write_tool(temp_dir)
        content = "Line 1\nLine 2\nLine 3"
        await tool.execute("call_1", {
            "path": "multiline.txt",
            "content": content
        })
        
        file_path = os.path.join(temp_dir, "multiline.txt")
        with open(file_path) as f:
            assert f.read() == content

    @pytest.mark.asyncio
    async def test_write_with_absolute_path(self, temp_dir):
        tool = create_write_tool(temp_dir)
        abs_path = os.path.join(temp_dir, "absolute.txt")
        
        await tool.execute("call_1", {
            "path": abs_path,
            "content": "Absolute path content"
        })
        
        assert os.path.exists(abs_path)
        with open(abs_path) as f:
            assert f.read() == "Absolute path content"
