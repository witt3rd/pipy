"""Main compaction function."""

from dataclasses import dataclass, field
from typing import Any

from ..settings import CompactionSettings
from .file_ops import compute_file_lists, format_file_operations
from .prepare import CompactionPreparation
from .summarize import generate_summary, generate_turn_prefix_summary


@dataclass
class CompactionResult:
    """Result from compaction."""

    summary: str
    """Generated summary text."""

    first_kept_entry_id: str
    """UUID of first entry to keep."""

    tokens_before: int
    """Token count before compaction."""

    details: dict[str, Any] = field(default_factory=dict)
    """Extension-specific data (e.g., file lists)."""


def should_compact(
    context_tokens: int,
    context_window: int,
    settings: CompactionSettings,
) -> bool:
    """
    Check if compaction should trigger based on context usage.

    Args:
        context_tokens: Current estimated context tokens
        context_window: Model's context window size
        settings: Compaction settings

    Returns:
        True if compaction should be triggered
    """
    if not settings.enabled:
        return False
    return context_tokens > context_window - settings.reserve_tokens


async def compact(
    preparation: CompactionPreparation,
    model: str,
    api_key: str | None = None,
    custom_instructions: str | None = None,
) -> CompactionResult:
    """
    Generate summaries for compaction using prepared data.

    Args:
        preparation: Pre-calculated preparation from prepare_compaction()
        model: Model identifier for summarization
        api_key: API key (optional)
        custom_instructions: Optional custom focus for the summary

    Returns:
        CompactionResult with summary and metadata
    """
    settings = preparation.settings

    # Generate summaries
    if preparation.is_split_turn and preparation.turn_prefix_messages:
        # Generate both summaries
        history_summary = await generate_summary(
            preparation.messages_to_summarize,
            model,
            settings.reserve_tokens,
            api_key,
            custom_instructions,
            preparation.previous_summary,
        ) if preparation.messages_to_summarize else "No prior history."

        turn_prefix_summary = await generate_turn_prefix_summary(
            preparation.turn_prefix_messages,
            model,
            settings.reserve_tokens,
            api_key,
        )

        # Merge into single summary
        summary = f"{history_summary}\n\n---\n\n**Turn Context (split turn):**\n\n{turn_prefix_summary}"
    else:
        # Just generate history summary
        summary = await generate_summary(
            preparation.messages_to_summarize,
            model,
            settings.reserve_tokens,
            api_key,
            custom_instructions,
            preparation.previous_summary,
        )

    # Compute file lists and append to summary
    read_files, modified_files = compute_file_lists(preparation.file_ops)
    summary += format_file_operations(read_files, modified_files)

    if not preparation.first_kept_entry_id:
        raise ValueError("First kept entry has no UUID - session may need migration")

    return CompactionResult(
        summary=summary,
        first_kept_entry_id=preparation.first_kept_entry_id,
        tokens_before=preparation.tokens_before,
        details={
            "read_files": read_files,
            "modified_files": modified_files,
        },
    )
