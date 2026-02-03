"""Tests for read tool."""

import os
import tempfile
import pytest

from pipy_coding_agent.tools.read import create_read_tool


@pytest.fixture
def temp_dir():
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        with open(os.path.join(tmpdir, "test.txt"), "w") as f:
            f.write("Hello, World!\nLine 2\nLine 3\n")
        
        with open(os.path.join(tmpdir, "large.txt"), "w") as f:
            for i in range(3000):
                f.write(f"Line {i}\n")
        
        yield tmpdir


class TestReadTool:
    @pytest.mark.asyncio
    async def test_read_simple_file(self, temp_dir):
        tool = create_read_tool(temp_dir)
        result = await tool.execute("call_1", {"path": "test.txt"})
        
        assert len(result.content) == 1
        assert result.content[0].type == "text"
        assert "Hello, World!" in result.content[0].text
        assert "Line 2" in result.content[0].text

    @pytest.mark.asyncio
    async def test_read_with_at_prefix(self, temp_dir):
        """Test that @-prefixed paths are resolved correctly."""
        tool = create_read_tool(temp_dir)
        result = await tool.execute("call_1", {"path": "@test.txt"})
        
        assert len(result.content) == 1
        assert "Hello, World!" in result.content[0].text

    @pytest.mark.asyncio
    async def test_read_with_offset(self, temp_dir):
        tool = create_read_tool(temp_dir)
        result = await tool.execute("call_1", {"path": "test.txt", "offset": 2})
        
        assert len(result.content) == 1
        text = result.content[0].text
        assert "Hello" not in text
        assert "Line 2" in text

    @pytest.mark.asyncio
    async def test_read_with_limit(self, temp_dir):
        tool = create_read_tool(temp_dir)
        result = await tool.execute("call_1", {"path": "test.txt", "limit": 1})
        
        text = result.content[0].text
        assert "Hello, World!" in text
        assert "Line 2" not in text

    @pytest.mark.asyncio
    async def test_read_large_file_truncation(self, temp_dir):
        tool = create_read_tool(temp_dir)
        result = await tool.execute("call_1", {"path": "large.txt"})
        
        text = result.content[0].text
        # Should have truncation notice
        assert "offset=" in text.lower() or "showing" in text.lower()
        # Should have details
        assert result.details is not None

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, temp_dir):
        tool = create_read_tool(temp_dir)
        
        with pytest.raises(FileNotFoundError):
            await tool.execute("call_1", {"path": "nonexistent.txt"})

    @pytest.mark.asyncio
    async def test_read_with_absolute_path(self, temp_dir):
        tool = create_read_tool(temp_dir)
        abs_path = os.path.join(temp_dir, "test.txt")
        result = await tool.execute("call_1", {"path": abs_path})
        
        assert "Hello, World!" in result.content[0].text

    @pytest.mark.asyncio
    async def test_read_offset_beyond_file(self, temp_dir):
        tool = create_read_tool(temp_dir)
        
        with pytest.raises(ValueError, match="beyond end of file"):
            await tool.execute("call_1", {"path": "test.txt", "offset": 1000})


class TestReadToolImage:
    @pytest.fixture
    def temp_dir_with_image(self):
        """Create temp dir with a simple PNG file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a minimal PNG file (1x1 pixel)
            png_data = bytes([
                0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,  # PNG signature
                0x00, 0x00, 0x00, 0x0d, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
                0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
                0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
                0xde, 0x00, 0x00, 0x00, 0x0c, 0x49, 0x44, 0x41,  # IDAT chunk
                0x54, 0x08, 0xd7, 0x63, 0xf8, 0xff, 0xff, 0x3f,
                0x00, 0x05, 0xfe, 0x02, 0xfe, 0xdc, 0xcc, 0x59,
                0xe7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4e,  # IEND chunk
                0x44, 0xae, 0x42, 0x60, 0x82,
            ])
            
            with open(os.path.join(tmpdir, "test.png"), "wb") as f:
                f.write(png_data)
            
            yield tmpdir

    @pytest.mark.asyncio
    async def test_read_image_file(self, temp_dir_with_image):
        tool = create_read_tool(temp_dir_with_image)
        result = await tool.execute("call_1", {"path": "test.png"})
        
        # Should return text note and image content
        assert len(result.content) == 2
        assert result.content[0].type == "text"
        assert "image" in result.content[0].text.lower()
        assert result.content[1].type == "image"
        assert result.content[1].mime_type == "image/png"
