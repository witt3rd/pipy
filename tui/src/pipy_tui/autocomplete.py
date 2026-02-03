"""Autocomplete provider system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
import os
import subprocess

from .fuzzy import fuzzy_filter, fuzzy_match


@dataclass
class AutocompleteItem:
    """An autocomplete suggestion."""

    value: str  # What gets inserted
    label: str  # What's displayed in the popup
    description: str = ""  # Optional description


@dataclass
class AutocompleteResult:
    """Result from an autocomplete provider."""

    items: list[AutocompleteItem]
    prefix: str  # What we're matching against (for replacement)


@dataclass
class CompletionResult:
    """Result of applying a completion."""

    lines: list[str]
    cursor_line: int
    cursor_col: int


class AutocompleteProvider(ABC):
    """Base class for autocomplete providers."""

    @abstractmethod
    def get_suggestions(
        self, lines: list[str], cursor_line: int, cursor_col: int
    ) -> AutocompleteResult | None:
        """Get autocomplete suggestions for current position.

        Args:
            lines: Current editor lines
            cursor_line: Current cursor line (0-indexed)
            cursor_col: Current cursor column (0-indexed)

        Returns:
            AutocompleteResult with items and prefix, or None if no suggestions
        """
        ...

    def apply_completion(
        self,
        lines: list[str],
        cursor_line: int,
        cursor_col: int,
        item: AutocompleteItem,
        prefix: str,
    ) -> CompletionResult:
        """Apply selected completion.

        Default implementation replaces prefix with item.value.
        Override for custom behavior.
        """
        line = lines[cursor_line]
        prefix_start = cursor_col - len(prefix)

        new_line = line[:prefix_start] + item.value + line[cursor_col:]
        new_lines = lines.copy()
        new_lines[cursor_line] = new_line

        new_col = prefix_start + len(item.value)

        return CompletionResult(
            lines=new_lines,
            cursor_line=cursor_line,
            cursor_col=new_col,
        )


@dataclass
class SlashCommand:
    """Definition of a slash command."""

    name: str
    description: str = ""
    argument_provider: AutocompleteProvider | None = None


class SlashCommandProvider(AutocompleteProvider):
    """Provides /command completions."""

    def __init__(self, commands: list[SlashCommand]) -> None:
        self.commands = commands

    def get_suggestions(
        self, lines: list[str], cursor_line: int, cursor_col: int
    ) -> AutocompleteResult | None:
        line = lines[cursor_line]
        text_before = line[:cursor_col]

        # Must start with / at beginning of line (with optional whitespace)
        stripped = text_before.lstrip()
        if not stripped.startswith("/"):
            return None

        # Check if we're past the command (have a space)
        space_idx = stripped.find(" ")
        if space_idx != -1:
            # We're in argument territory - check if command has argument provider
            cmd_name = stripped[1:space_idx]
            cmd = next((c for c in self.commands if c.name == cmd_name), None)
            if cmd and cmd.argument_provider:
                # Delegate to argument provider
                arg_text = stripped[space_idx + 1 :]
                return cmd.argument_provider.get_suggestions(lines, cursor_line, cursor_col)
            return None

        # Still typing command name
        prefix = stripped  # Include the /
        query = stripped[1:]  # Without /

        # Filter commands by fuzzy match
        matches = fuzzy_filter(self.commands, query, key=lambda c: c.name)

        if not matches:
            return None

        items = [
            AutocompleteItem(
                value=f"/{cmd.name}",
                label=f"/{cmd.name}",
                description=cmd.description,
            )
            for cmd in matches
        ]

        return AutocompleteResult(items=items, prefix=prefix)

    def apply_completion(
        self,
        lines: list[str],
        cursor_line: int,
        cursor_col: int,
        item: AutocompleteItem,
        prefix: str,
    ) -> CompletionResult:
        """Apply slash command completion, adding a space after."""
        line = lines[cursor_line]

        # Find where the / starts
        text_before = line[:cursor_col]
        slash_idx = text_before.rfind("/")
        if slash_idx == -1:
            slash_idx = cursor_col - len(prefix)

        new_line = line[:slash_idx] + item.value + " " + line[cursor_col:]
        new_lines = lines.copy()
        new_lines[cursor_line] = new_line

        new_col = slash_idx + len(item.value) + 1  # +1 for space

        return CompletionResult(
            lines=new_lines,
            cursor_line=cursor_line,
            cursor_col=new_col,
        )


class FilePathProvider(AutocompleteProvider):
    """Provides @file/path completions with fuzzy matching."""

    def __init__(
        self,
        base_path: Path | None = None,
        use_fd: bool = True,
        max_results: int = 50,
    ) -> None:
        self.base_path = base_path or Path.cwd()
        self.use_fd = use_fd and self._check_fd_available()
        self.max_results = max_results

    def _check_fd_available(self) -> bool:
        """Check if fd command is available."""
        try:
            result = subprocess.run(
                ["fd", "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_suggestions(
        self, lines: list[str], cursor_line: int, cursor_col: int
    ) -> AutocompleteResult | None:
        line = lines[cursor_line]
        text_before = line[:cursor_col]

        # Extract @prefix
        prefix = self._extract_at_prefix(text_before)
        if prefix is None:
            return None

        # Get the path part (without @)
        path_query = prefix[1:]  # Remove @

        # Handle quotes
        if path_query.startswith('"'):
            path_query = path_query[1:]
            is_quoted = True
        else:
            is_quoted = False

        # Search for files
        if self.use_fd:
            items = self._search_with_fd(path_query, is_quoted)
        else:
            items = self._search_directory(path_query, is_quoted)

        if not items:
            return None

        return AutocompleteResult(items=items, prefix=prefix)

    def _extract_at_prefix(self, text: str) -> str | None:
        """Extract @... prefix from text."""
        # Find the last @ that starts a token
        delimiters = set(" \t\"'=")

        for i in range(len(text) - 1, -1, -1):
            if text[i] == "@":
                # Check if it's at token start
                if i == 0 or text[i - 1] in delimiters:
                    return text[i:]
            elif text[i] in delimiters and i < len(text) - 1:
                # We passed a delimiter without finding @
                break

        return None

    def _search_with_fd(self, query: str, is_quoted: bool) -> list[AutocompleteItem]:
        """Search for files using fd (fast, respects .gitignore)."""
        try:
            args = [
                "fd",
                "--base-directory",
                str(self.base_path),
                "--max-results",
                str(self.max_results),
                "--type",
                "f",
                "--type",
                "d",
            ]

            if query:
                args.append(query)

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(self.base_path),
            )

            if result.returncode != 0:
                return []

            items = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                is_dir = line.endswith("/") or (self.base_path / line).is_dir()
                name = Path(line).name
                display = name + ("/" if is_dir else "")

                # Build value with @ and optional quotes
                value = self._build_value(line, is_dir, is_quoted)

                items.append(
                    AutocompleteItem(
                        value=value,
                        label=display,
                        description=line,
                    )
                )

            return items

        except (subprocess.TimeoutExpired, Exception):
            return []

    def _search_directory(self, query: str, is_quoted: bool) -> list[AutocompleteItem]:
        """Search directory without fd (fallback)."""
        try:
            # Determine search directory and prefix
            if "/" in query:
                search_dir = self.base_path / Path(query).parent
                prefix = Path(query).name
            else:
                search_dir = self.base_path
                prefix = query

            if not search_dir.exists():
                return []

            items = []
            for entry in search_dir.iterdir():
                name = entry.name

                # Skip hidden files unless query starts with .
                if name.startswith(".") and not prefix.startswith("."):
                    continue

                # Fuzzy match
                if prefix and not fuzzy_match(name, prefix):
                    continue

                is_dir = entry.is_dir()
                rel_path = entry.relative_to(self.base_path)
                display = name + ("/" if is_dir else "")

                value = self._build_value(str(rel_path), is_dir, is_quoted)

                items.append(
                    AutocompleteItem(
                        value=value,
                        label=display,
                        description=str(rel_path),
                    )
                )

            # Sort: directories first, then alphabetically
            items.sort(key=lambda x: (not x.label.endswith("/"), x.label.lower()))

            return items[: self.max_results]

        except Exception:
            return []

    def _build_value(self, path: str, is_dir: bool, is_quoted: bool) -> str:
        """Build the completion value with @ and optional quotes."""
        needs_quote = is_quoted or " " in path

        if is_dir and not path.endswith("/"):
            path = path + "/"

        if needs_quote:
            return f'@"{path}"'
        else:
            return f"@{path}"

    def apply_completion(
        self,
        lines: list[str],
        cursor_line: int,
        cursor_col: int,
        item: AutocompleteItem,
        prefix: str,
    ) -> CompletionResult:
        """Apply file path completion."""
        line = lines[cursor_line]

        # Find where the @ starts
        prefix_start = cursor_col - len(prefix)

        # Don't add space after directories (allow continued completion)
        is_dir = item.label.endswith("/")
        suffix = "" if is_dir else " "

        new_line = line[:prefix_start] + item.value + suffix + line[cursor_col:]
        new_lines = lines.copy()
        new_lines[cursor_line] = new_line

        # Position cursor appropriately
        if is_dir and item.value.endswith('"'):
            # Inside quotes before closing quote
            new_col = prefix_start + len(item.value) - 1
        else:
            new_col = prefix_start + len(item.value) + len(suffix)

        return CompletionResult(
            lines=new_lines,
            cursor_line=cursor_line,
            cursor_col=new_col,
        )


class CombinedProvider(AutocompleteProvider):
    """Combines multiple autocomplete providers."""

    def __init__(self, providers: list[AutocompleteProvider]) -> None:
        self.providers = providers

    def get_suggestions(
        self, lines: list[str], cursor_line: int, cursor_col: int
    ) -> AutocompleteResult | None:
        """Try each provider in order, return first result."""
        for provider in self.providers:
            result = provider.get_suggestions(lines, cursor_line, cursor_col)
            if result and result.items:
                # Store which provider matched for apply_completion
                self._last_provider = provider
                return result

        self._last_provider = None
        return None

    def apply_completion(
        self,
        lines: list[str],
        cursor_line: int,
        cursor_col: int,
        item: AutocompleteItem,
        prefix: str,
    ) -> CompletionResult:
        """Delegate to the provider that produced the suggestion."""
        if self._last_provider:
            return self._last_provider.apply_completion(
                lines, cursor_line, cursor_col, item, prefix
            )

        # Fallback to default behavior
        return super().apply_completion(lines, cursor_line, cursor_col, item, prefix)
