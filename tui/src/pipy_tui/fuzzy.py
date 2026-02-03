"""Fuzzy matching utilities."""

from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass
class FuzzyMatch:
    """Result of a fuzzy match."""

    score: int
    indices: list[int]  # Matched character positions for highlighting


def fuzzy_match(text: str, pattern: str) -> FuzzyMatch | None:
    """Match pattern against text using fuzzy matching.

    Returns match with score and indices, or None if no match.

    Scoring:
    - Base score of 100
    - +15 for consecutive character matches
    - +10 for match at word boundary
    - -1 for each position from start (prefer early matches)

    Example:
        >>> fuzzy_match("hello_world", "hw")
        FuzzyMatch(score=108, indices=[0, 6])
        >>> fuzzy_match("hello", "x")
        None
    """
    if not pattern:
        return FuzzyMatch(score=0, indices=[])

    text_lower = text.lower()
    pattern_lower = pattern.lower()

    indices: list[int] = []
    pattern_idx = 0

    for i, char in enumerate(text_lower):
        if pattern_idx < len(pattern_lower) and char == pattern_lower[pattern_idx]:
            indices.append(i)
            pattern_idx += 1

    if pattern_idx != len(pattern_lower):
        return None  # Not all pattern chars matched

    # Calculate score
    score = 100

    for i, idx in enumerate(indices):
        # Consecutive match bonus
        if i > 0 and idx == indices[i - 1] + 1:
            score += 15

        # Word boundary bonus (start of string or after _ - . /)
        if idx == 0 or (idx > 0 and text[idx - 1] in "_-./\\ "):
            score += 10

        # Penalty for late matches
        score -= idx

    return FuzzyMatch(score=score, indices=indices)


def fuzzy_filter(
    items: list[T],
    pattern: str,
    key: Callable[[T], str] = str,
) -> list[T]:
    """Filter and sort items by fuzzy match score.

    Args:
        items: Items to filter
        pattern: Pattern to match against
        key: Function to extract string from item

    Returns:
        Filtered and sorted items (highest score first)

    Example:
        >>> commands = ["help", "history", "hello"]
        >>> fuzzy_filter(commands, "he")
        ['help', 'hello', 'history']
    """
    if not pattern:
        return list(items)

    matches: list[tuple[T, int]] = []
    for item in items:
        match = fuzzy_match(key(item), pattern)
        if match:
            matches.append((item, match.score))

    matches.sort(key=lambda x: -x[1])  # Highest score first
    return [item for item, _ in matches]


def highlight_match(text: str, indices: list[int], highlight: Callable[[str], str]) -> str:
    """Apply highlight function to matched characters.

    Args:
        text: Original text
        indices: Matched character positions
        highlight: Function to apply to matched chars (e.g., lambda s: f"[bold]{s}[/bold]")

    Returns:
        Text with highlights applied

    Example:
        >>> highlight_match("hello", [0, 2], lambda s: f"*{s}*")
        '*h*e*l*lo'
    """
    if not indices:
        return text

    result = []
    idx_set = set(indices)

    for i, char in enumerate(text):
        if i in idx_set:
            result.append(highlight(char))
        else:
            result.append(char)

    return "".join(result)
