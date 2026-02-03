"""Tests for ls tool."""

import os
import tempfile
import pytest

from pipy_coding_agent.tools.ls import create_ls_tool


@pytest.fixture
def temp_dir():
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        open(os.path.join(tmpdir, "file1.txt"), "w").close()
        open(os.path.join(tmpdir, "file2.txt"), "w").close()
        open(os.path.join(tmpdir, ".hidden"), "w").close()
        
        # Create subdirectories
        os.makedirs(os.path.join(tmpdir, "subdir1"))
        os.makedirs(os.path.join(tmpdir, "subdir2"))
        
        yield tmpdir


class TestLsTool:
    @pytest.mark.asyncio
    async def test_list_current_directory(self, temp_dir):
        tool = create_ls_tool(temp_dir)
        result = await tool.execute("call_1", {})
        
        text = result.content[0].text
        assert "file1.txt" in text
        assert "file2.txt" in text

    @pytest.mark.asyncio
    async def test_list_with_path(self, temp_dir):
        tool = create_ls_tool(temp_dir)
        result = await tool.execute("call_1", {"path": "."})
        
        text = result.content[0].text
        assert "file1.txt" in text

    @pytest.mark.asyncio
    async def test_directories_have_slash(self, temp_dir):
        tool = create_ls_tool(temp_dir)
        result = await tool.execute("call_1", {})
        
        text = result.content[0].text
        assert "subdir1/" in text
        assert "subdir2/" in text

    @pytest.mark.asyncio
    async def test_includes_hidden_files(self, temp_dir):
        tool = create_ls_tool(temp_dir)
        result = await tool.execute("call_1", {})
        
        text = result.content[0].text
        assert ".hidden" in text

    @pytest.mark.asyncio
    async def test_sorted_alphabetically(self, temp_dir):
        tool = create_ls_tool(temp_dir)
        result = await tool.execute("call_1", {})
        
        text = result.content[0].text
        lines = [l for l in text.split("\n") if l.strip() and not l.startswith("[")]
        sorted_lines = sorted(lines, key=lambda x: x.lower().rstrip("/"))
        assert lines == sorted_lines

    @pytest.mark.asyncio
    async def test_path_not_found(self, temp_dir):
        tool = create_ls_tool(temp_dir)
        
        with pytest.raises(RuntimeError, match="not found"):
            await tool.execute("call_1", {"path": "nonexistent"})

    @pytest.mark.asyncio
    async def test_not_a_directory(self, temp_dir):
        tool = create_ls_tool(temp_dir)
        
        with pytest.raises(RuntimeError, match="Not a directory"):
            await tool.execute("call_1", {"path": "file1.txt"})

    @pytest.mark.asyncio
    async def test_empty_directory(self, temp_dir):
        # Create empty directory
        empty_dir = os.path.join(temp_dir, "empty")
        os.makedirs(empty_dir)
        
        tool = create_ls_tool(temp_dir)
        result = await tool.execute("call_1", {"path": "empty"})
        
        text = result.content[0].text
        assert "empty" in text.lower()

    @pytest.mark.asyncio
    async def test_entry_limit(self, temp_dir):
        """Test that entry limit is respected."""
        # Create many files
        for i in range(100):
            open(os.path.join(temp_dir, f"file{i:03d}.txt"), "w").close()
        
        tool = create_ls_tool(temp_dir)
        result = await tool.execute("call_1", {"limit": 10})
        
        text = result.content[0].text
        lines = [l for l in text.split("\n") if l.strip() and not l.startswith("[")]
        assert len(lines) <= 10

    @pytest.mark.asyncio
    async def test_list_subdirectory(self, temp_dir):
        # Create file in subdirectory
        open(os.path.join(temp_dir, "subdir1", "nested.txt"), "w").close()
        
        tool = create_ls_tool(temp_dir)
        result = await tool.execute("call_1", {"path": "subdir1"})
        
        text = result.content[0].text
        assert "nested.txt" in text
        # Should not include parent directory files
        assert "file1.txt" not in text
