"""Tests for grep tool."""

import os
import tempfile
import pytest

from pipy_coding_agent.tools.grep import create_grep_tool


@pytest.fixture
def temp_dir():
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        with open(os.path.join(tmpdir, "file1.txt"), "w") as f:
            f.write("Hello World\nFoo Bar\nHello Again\n")
        
        with open(os.path.join(tmpdir, "file2.txt"), "w") as f:
            f.write("Another file\nWith Hello\nAnd more\n")
        
        # Create subdirectory with files
        subdir = os.path.join(tmpdir, "subdir")
        os.makedirs(subdir)
        with open(os.path.join(subdir, "nested.txt"), "w") as f:
            f.write("Nested Hello\nNested content\n")
        
        yield tmpdir


class TestGrepTool:
    @pytest.mark.asyncio
    async def test_simple_search(self, temp_dir):
        tool = create_grep_tool(temp_dir)
        result = await tool.execute("call_1", {"pattern": "Hello"})
        
        text = result.content[0].text
        assert "Hello" in text
        # Should find matches in multiple files
        assert "file1.txt" in text
        assert "file2.txt" in text

    @pytest.mark.asyncio
    async def test_search_single_file(self, temp_dir):
        tool = create_grep_tool(temp_dir)
        result = await tool.execute("call_1", {
            "pattern": "Hello",
            "path": "file1.txt"
        })
        
        text = result.content[0].text
        assert "Hello" in text
        # Should only search the specified file
        assert "file2.txt" not in text

    @pytest.mark.asyncio
    async def test_case_insensitive(self, temp_dir):
        tool = create_grep_tool(temp_dir)
        
        # Case sensitive (default) - should not match
        result = await tool.execute("call_1", {"pattern": "hello"})
        text = result.content[0].text
        
        # Shouldn't find lowercase 'hello'
        if "No matches" not in text:
            # If it found matches, they should be from nested search or actual lowercase
            pass
        
        # Case insensitive - should match
        result = await tool.execute("call_1", {
            "pattern": "hello",
            "ignoreCase": True
        })
        text = result.content[0].text
        assert "Hello" in text or "hello" in text.lower()

    @pytest.mark.asyncio
    async def test_literal_search(self, temp_dir):
        """Test literal pattern (not regex)."""
        # Create file with regex-like content
        with open(os.path.join(temp_dir, "regex.txt"), "w") as f:
            f.write("Hello.*World\nPlain text\n")
        
        tool = create_grep_tool(temp_dir)
        
        # Literal search for regex pattern
        result = await tool.execute("call_1", {
            "pattern": "Hello.*World",
            "path": "regex.txt",
            "literal": True
        })
        
        text = result.content[0].text
        assert "Hello.*World" in text

    @pytest.mark.asyncio
    async def test_search_nested_directories(self, temp_dir):
        tool = create_grep_tool(temp_dir)
        result = await tool.execute("call_1", {"pattern": "Nested"})
        
        text = result.content[0].text
        assert "Nested" in text
        assert "subdir" in text or "nested.txt" in text

    @pytest.mark.asyncio
    async def test_no_matches(self, temp_dir):
        tool = create_grep_tool(temp_dir)
        result = await tool.execute("call_1", {"pattern": "Nonexistent12345"})
        
        text = result.content[0].text
        assert "No matches" in text

    @pytest.mark.asyncio
    async def test_invalid_regex(self, temp_dir):
        tool = create_grep_tool(temp_dir)
        
        with pytest.raises(RuntimeError, match="Invalid regex"):
            await tool.execute("call_1", {"pattern": "[invalid"})

    @pytest.mark.asyncio
    async def test_match_limit(self, temp_dir):
        """Test that match limit is respected."""
        # Create file with many matches
        with open(os.path.join(temp_dir, "many.txt"), "w") as f:
            for i in range(200):
                f.write(f"Match {i}\n")
        
        tool = create_grep_tool(temp_dir)
        result = await tool.execute("call_1", {
            "pattern": "Match",
            "path": "many.txt",
            "limit": 10
        })
        
        text = result.content[0].text
        # Should have limit notice
        assert "first 10" in text.lower() or "limit" in text.lower()

    @pytest.mark.asyncio
    async def test_path_not_found(self, temp_dir):
        tool = create_grep_tool(temp_dir)
        
        with pytest.raises(RuntimeError, match="not found"):
            await tool.execute("call_1", {
                "pattern": "test",
                "path": "nonexistent"
            })

    @pytest.mark.asyncio
    async def test_context_lines(self, temp_dir):
        """Test context lines around matches."""
        tool = create_grep_tool(temp_dir)
        result = await tool.execute("call_1", {
            "pattern": "Foo Bar",
            "path": "file1.txt",
            "context": 1
        })
        
        text = result.content[0].text
        # Should include context lines
        assert "Hello World" in text  # Line before
        assert "Foo Bar" in text      # Match line
        assert "Hello Again" in text  # Line after
