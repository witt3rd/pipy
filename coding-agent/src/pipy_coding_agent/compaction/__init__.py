"""Context compaction for long sessions."""

from .tokens import (
    estimate_tokens,
    estimate_context_tokens,
    calculate_context_tokens,
    ContextUsageEstimate,
)
from .file_ops import (
    FileOperations,
    create_file_ops,
    extract_file_ops_from_message,
    compute_file_lists,
    format_file_operations,
)
from .cut_point import (
    find_cut_point,
    find_turn_start_index,
    find_valid_cut_points,
    CutPointResult,
)
from .prepare import (
    prepare_compaction,
    CompactionPreparation,
)
from .summarize import (
    generate_summary,
    serialize_conversation,
    SUMMARIZATION_SYSTEM_PROMPT,
    SUMMARIZATION_PROMPT,
    UPDATE_SUMMARIZATION_PROMPT,
)
from .compact import (
    compact,
    should_compact,
    CompactionResult,
)

__all__ = [
    # Tokens
    "estimate_tokens",
    "estimate_context_tokens",
    "calculate_context_tokens",
    "ContextUsageEstimate",
    # File operations
    "FileOperations",
    "create_file_ops",
    "extract_file_ops_from_message",
    "compute_file_lists",
    "format_file_operations",
    # Cut point
    "find_cut_point",
    "find_turn_start_index",
    "find_valid_cut_points",
    "CutPointResult",
    # Prepare
    "prepare_compaction",
    "CompactionPreparation",
    # Summarize
    "generate_summary",
    "serialize_conversation",
    "SUMMARIZATION_SYSTEM_PROMPT",
    "SUMMARIZATION_PROMPT",
    "UPDATE_SUMMARIZATION_PROMPT",
    # Compact
    "compact",
    "should_compact",
    "CompactionResult",
]
