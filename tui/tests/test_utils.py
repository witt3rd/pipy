"""Tests for text utilities."""

from pipy_tui import (
    visible_width,
    word_wrap_line,
    find_word_boundary_left,
    find_word_boundary_right,
    truncate_to_width,
)


class TestVisibleWidth:
    def test_ascii(self):
        assert visible_width("hello") == 5

    def test_empty(self):
        assert visible_width("") == 0

    def test_wide_chars(self):
        # CJK characters are 2 columns wide
        assert visible_width("你好") == 4

    def test_mixed(self):
        assert visible_width("hi你好") == 2 + 4  # 6

    def test_ansi_escape(self):
        # ANSI escapes should not count
        assert visible_width("\x1b[31mred\x1b[0m") == 3


class TestWordWrapLine:
    def test_no_wrap_needed(self):
        chunks = word_wrap_line("hello", 10)
        assert len(chunks) == 1
        assert chunks[0].text == "hello"

    def test_empty_line(self):
        chunks = word_wrap_line("", 10)
        assert len(chunks) == 1
        assert chunks[0].text == ""

    def test_simple_wrap(self):
        chunks = word_wrap_line("hello world", 6)
        assert len(chunks) == 2
        assert chunks[0].text == "hello "
        assert chunks[1].text == "world"

    def test_long_word(self):
        # Word longer than width should force-break
        chunks = word_wrap_line("supercalifragilistic", 5)
        assert len(chunks) > 1
        for chunk in chunks:
            assert visible_width(chunk.text) <= 5

    def test_preserves_indices(self):
        chunks = word_wrap_line("hello world", 6)
        assert chunks[0].start_index == 0
        assert chunks[0].end_index == 6
        assert chunks[1].start_index == 6


class TestWordBoundaries:
    def test_word_boundary_left_middle(self):
        # "hello world" with cursor at 'o' in world (pos 8)
        pos = find_word_boundary_left("hello world", 8)
        assert pos == 6  # Start of "world"

    def test_word_boundary_left_start(self):
        pos = find_word_boundary_left("hello", 0)
        assert pos == 0

    def test_word_boundary_left_after_space(self):
        pos = find_word_boundary_left("hello world", 6)
        assert pos == 0  # Skips space, goes to start of "hello"

    def test_word_boundary_right_middle(self):
        pos = find_word_boundary_right("hello world", 2)
        assert pos == 6  # End of "hello" + space

    def test_word_boundary_right_end(self):
        pos = find_word_boundary_right("hello", 5)
        assert pos == 5

    def test_word_boundary_with_underscores(self):
        # Underscores are word chars
        pos = find_word_boundary_left("hello_world", 11)
        assert pos == 0  # One word


class TestTruncateToWidth:
    def test_no_truncate(self):
        result = truncate_to_width("hello", 10)
        assert result == "hello"

    def test_truncate(self):
        result = truncate_to_width("hello world", 8)
        assert result == "hello w…"
        assert visible_width(result) <= 8

    def test_exact_width(self):
        result = truncate_to_width("hello", 5)
        assert result == "hello"

    def test_very_short(self):
        result = truncate_to_width("hello", 2)
        assert visible_width(result) <= 2

    def test_custom_ellipsis(self):
        result = truncate_to_width("hello world", 8, ellipsis="...")
        assert result.endswith("...")
