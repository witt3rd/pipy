"""Text utilities for terminal display."""

import unicodedata
from dataclasses import dataclass


def visible_width(text: str) -> int:
    """Calculate visible width of text in terminal columns.

    Accounts for:
    - Wide characters (CJK, emoji) = 2 columns
    - Zero-width characters = 0 columns
    - ANSI escape sequences = 0 columns
    - Normal characters = 1 column

    Args:
        text: Text to measure

    Returns:
        Width in terminal columns
    """
    width = 0
    in_escape = False

    i = 0
    while i < len(text):
        char = text[i]

        # Skip ANSI escape sequences
        if char == "\x1b":
            in_escape = True
            i += 1
            continue

        if in_escape:
            if char in "mGKHJsu" or (char.isalpha() and char not in "O["):
                in_escape = False
            i += 1
            continue

        # Get character width
        char_width = _char_width(char)
        width += char_width
        i += 1

    return width


def _char_width(char: str) -> int:
    """Get display width of a single character."""
    if len(char) != 1:
        return sum(_char_width(c) for c in char)

    # Control characters
    if ord(char) < 32:
        return 0

    # Check East Asian Width
    ea_width = unicodedata.east_asian_width(char)

    # Wide characters (CJK, etc.)
    if ea_width in ("F", "W"):
        return 2

    # Zero-width characters
    category = unicodedata.category(char)
    if category in ("Mn", "Me", "Cf"):  # Mark, Enclosing, Format
        return 0

    return 1


@dataclass
class TextChunk:
    """A chunk of wrapped text with position tracking."""

    text: str
    start_index: int  # Start position in original line
    end_index: int  # End position in original line


def word_wrap_line(line: str, max_width: int) -> list[TextChunk]:
    """Wrap a line at word boundaries.

    Args:
        line: Text line to wrap
        max_width: Maximum visible width per chunk

    Returns:
        List of TextChunks with position information
    """
    if not line or max_width <= 0:
        return [TextChunk(text="", start_index=0, end_index=0)]

    line_width = visible_width(line)
    if line_width <= max_width:
        return [TextChunk(text=line, start_index=0, end_index=len(line))]

    chunks: list[TextChunk] = []
    current_width = 0
    chunk_start = 0

    # Track wrap opportunity (after whitespace, before non-whitespace)
    wrap_opp_index = -1
    wrap_opp_width = 0

    i = 0
    while i < len(line):
        char = line[i]
        char_width = _char_width(char)
        is_whitespace = char in " \t"

        # Check for overflow
        if current_width + char_width > max_width:
            if wrap_opp_index >= 0:
                # Wrap at last opportunity
                chunks.append(
                    TextChunk(
                        text=line[chunk_start:wrap_opp_index],
                        start_index=chunk_start,
                        end_index=wrap_opp_index,
                    )
                )
                chunk_start = wrap_opp_index
                current_width -= wrap_opp_width
            elif chunk_start < i:
                # Force break at current position
                chunks.append(
                    TextChunk(
                        text=line[chunk_start:i],
                        start_index=chunk_start,
                        end_index=i,
                    )
                )
                chunk_start = i
                current_width = 0

            wrap_opp_index = -1

        current_width += char_width

        # Record wrap opportunity
        if is_whitespace and i + 1 < len(line) and line[i + 1] not in " \t":
            wrap_opp_index = i + 1
            wrap_opp_width = current_width

        i += 1

    # Final chunk
    chunks.append(
        TextChunk(
            text=line[chunk_start:],
            start_index=chunk_start,
            end_index=len(line),
        )
    )

    return chunks


def is_word_char(char: str) -> bool:
    """Check if character is part of a word."""
    if not char:
        return False
    return char.isalnum() or char == "_"


def is_whitespace(char: str) -> bool:
    """Check if character is whitespace."""
    return char in " \t\n\r"


def find_word_boundary_left(text: str, pos: int) -> int:
    """Find the start of the word to the left of pos.

    Emacs-style: skip whitespace, then skip word chars.
    """
    if pos <= 0:
        return 0

    i = pos - 1

    # Skip whitespace
    while i > 0 and is_whitespace(text[i]):
        i -= 1

    # Skip word characters
    while i > 0 and is_word_char(text[i - 1]):
        i -= 1

    # If we're on a non-word char and didn't move, skip non-word chars
    if i == pos - 1 and not is_word_char(text[i]):
        while i > 0 and not is_word_char(text[i - 1]) and not is_whitespace(text[i - 1]):
            i -= 1

    return max(0, i)


def find_word_boundary_right(text: str, pos: int) -> int:
    """Find the end of the word to the right of pos.

    Emacs-style: skip word chars, then skip whitespace.
    """
    if pos >= len(text):
        return len(text)

    i = pos

    # Skip word characters
    while i < len(text) and is_word_char(text[i]):
        i += 1

    # Skip whitespace
    while i < len(text) and is_whitespace(text[i]):
        i += 1

    # If we didn't move and on non-word, skip non-word chars
    if i == pos and i < len(text) and not is_word_char(text[i]):
        while i < len(text) and not is_word_char(text[i]) and not is_whitespace(text[i]):
            i += 1
        # Then skip whitespace
        while i < len(text) and is_whitespace(text[i]):
            i += 1

    return min(len(text), i)


def truncate_to_width(text: str, max_width: int, ellipsis: str = "…") -> str:
    """Truncate text to fit within max_width columns.

    Args:
        text: Text to truncate
        max_width: Maximum visible width
        ellipsis: String to append when truncated

    Returns:
        Truncated text with ellipsis if needed
    """
    if visible_width(text) <= max_width:
        return text

    ellipsis_width = visible_width(ellipsis)
    target_width = max_width - ellipsis_width

    if target_width <= 0:
        return ellipsis[:max_width] if max_width > 0 else ""

    result = []
    current_width = 0

    for char in text:
        char_width = _char_width(char)
        if current_width + char_width > target_width:
            break
        result.append(char)
        current_width += char_width

    return "".join(result) + ellipsis
