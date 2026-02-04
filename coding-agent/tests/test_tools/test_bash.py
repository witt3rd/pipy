"""Tests for bash tool."""

import os
import sys
import tempfile
import pytest

from pipy_coding_agent.tools.bash import create_bash_tool, BashSpawnContext, BashSpawnHook


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestBashTool:
    @pytest.mark.asyncio
    async def test_simple_command(self, temp_dir):
        tool = create_bash_tool(temp_dir)
        
        if sys.platform == "win32":
            result = await tool.execute("call_1", {"command": "echo Hello"})
        else:
            result = await tool.execute("call_1", {"command": "echo Hello"})
        
        assert "Hello" in result.content[0].text

    @pytest.mark.asyncio
    async def test_command_with_output(self, temp_dir):
        tool = create_bash_tool(temp_dir)
        
        if sys.platform == "win32":
            result = await tool.execute("call_1", {"command": "dir"})
        else:
            result = await tool.execute("call_1", {"command": "ls -la"})
        
        assert len(result.content[0].text) > 0

    @pytest.mark.asyncio
    async def test_command_failure(self, temp_dir):
        tool = create_bash_tool(temp_dir)
        
        with pytest.raises(RuntimeError, match="exited with code"):
            if sys.platform == "win32":
                await tool.execute("call_1", {"command": "exit 1"})
            else:
                await tool.execute("call_1", {"command": "exit 1"})

    @pytest.mark.asyncio
    async def test_working_directory(self, temp_dir):
        """Test that commands run in the correct working directory."""
        # Create a file in temp_dir
        test_file = os.path.join(temp_dir, "test_marker.txt")
        with open(test_file, "w") as f:
            f.write("marker")
        
        tool = create_bash_tool(temp_dir)
        
        if sys.platform == "win32":
            result = await tool.execute("call_1", {"command": "dir"})
        else:
            result = await tool.execute("call_1", {"command": "ls"})
        
        assert "test_marker.txt" in result.content[0].text

    @pytest.mark.asyncio
    async def test_nonexistent_directory(self):
        tool = create_bash_tool("/nonexistent/directory")
        
        with pytest.raises(RuntimeError, match="does not exist"):
            await tool.execute("call_1", {"command": "echo test"})

    @pytest.mark.asyncio
    @pytest.mark.skipif(sys.platform == "win32", reason="Timeout test unreliable on Windows")
    async def test_timeout(self, temp_dir):
        """Test command timeout."""
        tool = create_bash_tool(temp_dir)
        
        with pytest.raises(RuntimeError, match="timed out"):
            await tool.execute("call_1", {
                "command": "sleep 10",
                "timeout": 1
            })

    @pytest.mark.asyncio
    async def test_multiline_output(self, temp_dir):
        tool = create_bash_tool(temp_dir)
        
        if sys.platform == "win32":
            result = await tool.execute("call_1", {
                "command": "echo Line1 && echo Line2 && echo Line3"
            })
        else:
            result = await tool.execute("call_1", {
                "command": "echo Line1; echo Line2; echo Line3"
            })
        
        text = result.content[0].text
        assert "Line1" in text
        assert "Line2" in text
        assert "Line3" in text


class TestBashSpawnHook:
    @pytest.mark.asyncio
    async def test_spawn_hook_modifies_env(self, temp_dir):
        """Test that spawn hook can modify environment variables."""
        def hook(ctx: BashSpawnContext) -> BashSpawnContext:
            ctx.env["MY_TEST_VAR"] = "hook_value"
            return ctx
        
        tool = create_bash_tool(temp_dir, spawn_hook=hook)
        
        # Use bash syntax - our shell detection now prefers bash on all platforms
        result = await tool.execute("call_1", {"command": "echo $MY_TEST_VAR"})
        
        assert "hook_value" in result.content[0].text

    @pytest.mark.asyncio
    async def test_spawn_hook_modifies_command(self, temp_dir):
        """Test that spawn hook can modify command."""
        def hook(ctx: BashSpawnContext) -> BashSpawnContext:
            ctx.command = ctx.command.replace("PLACEHOLDER", "World")
            return ctx
        
        tool = create_bash_tool(temp_dir, spawn_hook=hook)
        
        result = await tool.execute("call_1", {"command": "echo Hello PLACEHOLDER"})
        
        assert "Hello World" in result.content[0].text


class TestBashToolTruncation:
    @pytest.mark.asyncio
    @pytest.mark.skipif(sys.platform == "win32", reason="Large output test uses Unix commands")
    async def test_large_output_truncation(self, temp_dir):
        """Test that large output is truncated."""
        tool = create_bash_tool(temp_dir)
        
        # Generate a lot of output
        result = await tool.execute("call_1", {
            "command": "for i in $(seq 1 3000); do echo Line $i; done"
        })
        
        # Should have truncation info
        text = result.content[0].text
        assert "Showing lines" in text or result.details is not None
