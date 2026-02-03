"""Tests for find tool."""

import os
import tempfile
import pytest

from pipy_coding_agent.tools.find import create_find_tool


@pytest.fixture
def temp_dir():
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        open(os.path.join(tmpdir, "file1.txt"), "w").close()
        open(os.path.join(tmpdir, "file2.txt"), "w").close()
        open(os.path.join(tmpdir, "data.json"), "w").close()
        
        # Create subdirectory with files
        subdir = os.path.join(tmpdir, "subdir")
        os.makedirs(subdir)
        open(os.path.join(subdir, "nested.txt"), "w").close()
        open(os.path.join(subdir, "config.json"), "w").close()
        
        # Create deeper nesting
        deep = os.path.join(subdir, "deep")
        os.makedirs(deep)
        open(os.path.join(deep, "deep.txt"), "w").close()
        
        yield tmpdir


class TestFindTool:
    @pytest.mark.asyncio
    async def test_find_all_txt_files(self, temp_dir):
        tool = create_find_tool(temp_dir)
        result = await tool.execute("call_1", {"pattern": "*.txt"})
        
        text = result.content[0].text
        assert "file1.txt" in text
        assert "file2.txt" in text
        # Should not include json files
        assert "data.json" not in text

    @pytest.mark.asyncio
    async def test_find_nested_files(self, temp_dir):
        tool = create_find_tool(temp_dir)
        result = await tool.execute("call_1", {"pattern": "*.txt"})
        
        text = result.content[0].text
        assert "nested.txt" in text
        assert "deep.txt" in text

    @pytest.mark.asyncio
    async def test_find_json_files(self, temp_dir):
        tool = create_find_tool(temp_dir)
        result = await tool.execute("call_1", {"pattern": "*.json"})
        
        text = result.content[0].text
        assert "data.json" in text
        assert "config.json" in text
        # Should not include txt files
        assert "file1.txt" not in text

    @pytest.mark.asyncio
    async def test_find_specific_file(self, temp_dir):
        tool = create_find_tool(temp_dir)
        result = await tool.execute("call_1", {"pattern": "config.json"})
        
        text = result.content[0].text
        assert "config.json" in text

    @pytest.mark.asyncio
    async def test_find_in_subdirectory(self, temp_dir):
        tool = create_find_tool(temp_dir)
        result = await tool.execute("call_1", {
            "pattern": "*.txt",
            "path": "subdir"
        })
        
        text = result.content[0].text
        assert "nested.txt" in text
        assert "deep.txt" in text
        # Should not include root files
        assert "file1.txt" not in text

    @pytest.mark.asyncio
    async def test_no_matches(self, temp_dir):
        tool = create_find_tool(temp_dir)
        result = await tool.execute("call_1", {"pattern": "*.xyz"})
        
        text = result.content[0].text
        assert "No files found" in text

    @pytest.mark.asyncio
    async def test_path_not_found(self, temp_dir):
        tool = create_find_tool(temp_dir)
        
        with pytest.raises(RuntimeError, match="not found"):
            await tool.execute("call_1", {
                "pattern": "*.txt",
                "path": "nonexistent"
            })

    @pytest.mark.asyncio
    async def test_result_limit(self, temp_dir):
        """Test that result limit is respected."""
        # Create many files
        for i in range(50):
            open(os.path.join(temp_dir, f"test{i}.txt"), "w").close()
        
        tool = create_find_tool(temp_dir)
        result = await tool.execute("call_1", {
            "pattern": "test*.txt",
            "limit": 10
        })
        
        text = result.content[0].text
        lines = [l for l in text.split("\n") if l.strip() and not l.startswith("[")]
        assert len(lines) <= 10

    @pytest.mark.asyncio
    async def test_results_are_sorted(self, temp_dir):
        tool = create_find_tool(temp_dir)
        result = await tool.execute("call_1", {"pattern": "*.txt"})
        
        text = result.content[0].text
        lines = [l for l in text.split("\n") if l.strip() and not l.startswith("[")]
        # Files should be sorted
        sorted_lines = sorted(lines, key=str.lower)
        assert lines == sorted_lines
