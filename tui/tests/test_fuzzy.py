"""Tests for fuzzy matching."""

import pytest
from pipy_tui import fuzzy_match, fuzzy_filter, highlight_match, FuzzyMatch


class TestFuzzyMatch:
    def test_exact_match(self):
        result = fuzzy_match("hello", "hello")
        assert result is not None
        assert result.indices == [0, 1, 2, 3, 4]
        assert result.score > 100  # High score for exact

    def test_prefix_match(self):
        result = fuzzy_match("hello", "hel")
        assert result is not None
        assert result.indices == [0, 1, 2]

    def test_fuzzy_match(self):
        result = fuzzy_match("hello_world", "hw")
        assert result is not None
        assert result.indices == [0, 6]

    def test_no_match(self):
        result = fuzzy_match("hello", "xyz")
        assert result is None

    def test_empty_pattern(self):
        result = fuzzy_match("hello", "")
        assert result is not None
        assert result.indices == []
        assert result.score == 0

    def test_case_insensitive(self):
        result = fuzzy_match("HelloWorld", "hw")
        assert result is not None
        assert result.indices == [0, 5]

    def test_consecutive_bonus(self):
        # "hel" should score higher than "h_e_l" due to consecutive bonus
        result1 = fuzzy_match("hello", "hel")
        result2 = fuzzy_match("h_e_l_lo", "hel")
        assert result1 is not None
        assert result2 is not None
        assert result1.score > result2.score

    def test_word_boundary_bonus(self):
        # Match at word boundary should score higher
        result1 = fuzzy_match("get_weather", "w")
        result2 = fuzzy_match("getweather", "w")
        assert result1 is not None
        assert result2 is not None
        # 'w' at boundary (_w) should score higher
        assert result1.score > result2.score


class TestFuzzyFilter:
    def test_filter_and_sort(self):
        items = ["help", "history", "hello", "hi"]
        result = fuzzy_filter(items, "he")
        # "help" and "hello" should be top (prefix match)
        assert "help" in result[:2]
        assert "hello" in result[:2]

    def test_empty_pattern(self):
        items = ["a", "b", "c"]
        result = fuzzy_filter(items, "")
        assert result == items

    def test_no_matches(self):
        items = ["apple", "banana", "cherry"]
        result = fuzzy_filter(items, "xyz")
        assert result == []

    def test_custom_key(self):
        items = [{"name": "help"}, {"name": "hello"}]
        result = fuzzy_filter(items, "he", key=lambda x: x["name"])
        assert len(result) == 2
        assert result[0]["name"] in ["help", "hello"]


class TestHighlightMatch:
    def test_highlight(self):
        result = highlight_match("hello", [0, 2], lambda s: f"*{s}*")
        assert result == "*h*e*l*lo"

    def test_no_indices(self):
        result = highlight_match("hello", [], lambda s: f"*{s}*")
        assert result == "hello"

    def test_all_highlighted(self):
        result = highlight_match("hi", [0, 1], lambda s: f"[{s}]")
        assert result == "[h][i]"
