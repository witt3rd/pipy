"""Tests for truncation utilities."""

import pytest

from pipy_coding_agent.tools.truncate import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    format_size,
    truncate_head,
    truncate_tail,
    truncate_line,
)


class TestFormatSize:
    def test_bytes(self):
        assert format_size(100) == "100B"
        assert format_size(0) == "0B"
        assert format_size(1023) == "1023B"

    def test_kilobytes(self):
        assert format_size(1024) == "1.0KB"
        assert format_size(2048) == "2.0KB"
        assert format_size(1536) == "1.5KB"

    def test_megabytes(self):
        assert format_size(1024 * 1024) == "1.0MB"
        assert format_size(2 * 1024 * 1024) == "2.0MB"


class TestTruncateHead:
    def test_no_truncation_needed(self):
        content = "line1\nline2\nline3"
        result = truncate_head(content)
        
        assert result.content == content
        assert not result.truncated
        assert result.truncated_by is None
        assert result.total_lines == 3
        assert result.output_lines == 3

    def test_truncate_by_lines(self):
        # Create content with more lines than default
        lines = [f"line{i}" for i in range(3000)]
        content = "\n".join(lines)
        
        result = truncate_head(content, max_lines=100)
        
        assert result.truncated
        assert result.truncated_by == "lines"
        assert result.output_lines == 100
        assert result.total_lines == 3000

    def test_truncate_by_bytes(self):
        # Create content that exceeds byte limit
        line = "x" * 1000  # 1KB per line
        lines = [line for _ in range(100)]  # 100KB total
        content = "\n".join(lines)
        
        result = truncate_head(content, max_bytes=10000)  # 10KB limit
        
        assert result.truncated
        assert result.truncated_by == "bytes"
        assert result.output_bytes <= 10000

    def test_first_line_exceeds_limit(self):
        # First line alone exceeds byte limit
        content = "x" * 60000  # 60KB single line
        
        result = truncate_head(content, max_bytes=50000)
        
        assert result.truncated
        assert result.first_line_exceeds_limit
        assert result.content == ""
        assert result.output_lines == 0


class TestTruncateTail:
    def test_no_truncation_needed(self):
        content = "line1\nline2\nline3"
        result = truncate_tail(content)
        
        assert result.content == content
        assert not result.truncated
        assert result.truncated_by is None

    def test_truncate_by_lines(self):
        # Create content with more lines than limit
        lines = [f"line{i}" for i in range(3000)]
        content = "\n".join(lines)
        
        result = truncate_tail(content, max_lines=100)
        
        assert result.truncated
        assert result.truncated_by == "lines"
        assert result.output_lines == 100
        # Should have the last 100 lines
        assert "line2999" in result.content
        assert "line2900" in result.content

    def test_truncate_by_bytes(self):
        # Create content that exceeds byte limit
        line = "x" * 1000
        lines = [line for _ in range(100)]
        content = "\n".join(lines)
        
        result = truncate_tail(content, max_bytes=10000)
        
        assert result.truncated
        assert result.truncated_by == "bytes"
        assert result.output_bytes <= 10000

    def test_partial_last_line(self):
        # Single very long line
        content = "x" * 60000
        
        result = truncate_tail(content, max_bytes=10000)
        
        assert result.truncated
        assert result.last_line_partial
        # Should have end of the long line
        assert len(result.content.encode("utf-8")) <= 10000


class TestTruncateLine:
    def test_no_truncation(self):
        line = "short line"
        text, truncated = truncate_line(line)
        
        assert text == line
        assert not truncated

    def test_truncation(self):
        line = "x" * 1000
        text, truncated = truncate_line(line, max_chars=100)
        
        assert truncated
        assert len(text) < len(line)
        assert "[truncated]" in text
        assert text.startswith("x" * 100)
