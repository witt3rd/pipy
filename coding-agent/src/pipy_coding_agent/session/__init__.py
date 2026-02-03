"""Session management for conversation persistence."""

from .context import (
    SessionContext,
    build_session_context,
    create_branch_summary_message,
    create_compaction_summary_message,
    create_custom_message,
)
from .entries import (
    BRANCH_SUMMARY_PREFIX,
    BRANCH_SUMMARY_SUFFIX,
    COMPACTION_SUMMARY_PREFIX,
    COMPACTION_SUMMARY_SUFFIX,
    CURRENT_SESSION_VERSION,
    BranchSummaryEntry,
    CompactionEntry,
    CustomEntry,
    CustomMessageEntry,
    FileEntry,
    LabelEntry,
    ModelChangeEntry,
    SessionEntry,
    SessionHeader,
    SessionInfoEntry,
    SessionMessageEntry,
    ThinkingLevelChangeEntry,
    generate_id,
    now_iso,
)
from .manager import (
    SessionInfo,
    SessionManager,
    find_most_recent_session,
    get_default_session_dir,
    is_valid_session_file,
    load_entries_from_file,
)

# Convenience function
def list_sessions(session_dir):
    """List all sessions in a directory."""
    return SessionManager.list_sessions(session_dir)

__all__ = [
    # Manager
    "SessionManager",
    "SessionInfo",
    # Context
    "SessionContext",
    "build_session_context",
    "create_compaction_summary_message",
    "create_branch_summary_message",
    "create_custom_message",
    # Entry types
    "SessionHeader",
    "SessionEntry",
    "FileEntry",
    "SessionMessageEntry",
    "ThinkingLevelChangeEntry",
    "ModelChangeEntry",
    "CompactionEntry",
    "BranchSummaryEntry",
    "CustomEntry",
    "CustomMessageEntry",
    "LabelEntry",
    "SessionInfoEntry",
    # Constants
    "CURRENT_SESSION_VERSION",
    "COMPACTION_SUMMARY_PREFIX",
    "COMPACTION_SUMMARY_SUFFIX",
    "BRANCH_SUMMARY_PREFIX",
    "BRANCH_SUMMARY_SUFFIX",
    # Utilities
    "generate_id",
    "now_iso",
    "get_default_session_dir",
    "find_most_recent_session",
    "load_entries_from_file",
    "is_valid_session_file",
    "list_sessions",
]
