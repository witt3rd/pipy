"""Session manager for conversation persistence.

Manages sessions as append-only trees stored in JSONL files.
Each entry has an id and parentId forming a tree structure.
"""

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from pipy_agent import AgentMessage

from .context import SessionContext, build_session_context
from .entries import (
    CURRENT_SESSION_VERSION,
    CompactionEntry,
    CustomEntry,
    CustomMessageEntry,
    FileEntry,
    ModelChangeEntry,
    SessionEntry,
    SessionHeader,
    SessionInfoEntry,
    SessionMessageEntry,
    ThinkingLevelChangeEntry,
    generate_id,
    now_iso,
)


@dataclass
class SessionInfo:
    """Information about a session for listing."""

    path: str
    id: str
    cwd: str
    name: str | None
    parent_session_path: str | None
    created: datetime
    modified: datetime
    message_count: int
    first_message: str
    all_messages_text: str


def get_default_session_dir(cwd: str) -> Path:
    """
    Compute the default session directory for a cwd.
    Encodes cwd into a safe directory name under ~/.pipy/sessions/.
    """
    # Encode cwd into safe directory name
    safe_path = f"--{cwd.lstrip('/').lstrip('\\').replace('/', '-').replace('\\', '-').replace(':', '-')}--"
    session_dir = Path.home() / ".pipy" / "sessions" / safe_path
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def load_entries_from_file(file_path: str | Path) -> list[FileEntry]:
    """Load and parse session entries from a JSONL file."""
    file_path = Path(file_path)
    if not file_path.exists():
        return []

    entries: list[FileEntry] = []
    try:
        content = file_path.read_text(encoding="utf-8")
        for line in content.strip().split("\n"):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError:
                # Skip malformed lines
                pass

        # Validate session header
        if not entries:
            return entries
        header = entries[0]
        if header.get("type") != "session" or not isinstance(header.get("id"), str):
            return []

        return entries
    except Exception:
        return []


def is_valid_session_file(file_path: str | Path) -> bool:
    """Quick check if file is a valid session file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            first_line = f.readline()
        if not first_line:
            return False
        header = json.loads(first_line)
        return header.get("type") == "session" and isinstance(header.get("id"), str)
    except Exception:
        return False


def find_most_recent_session(session_dir: str | Path) -> str | None:
    """Find the most recently modified session file in a directory."""
    session_dir = Path(session_dir)
    if not session_dir.exists():
        return None

    try:
        files = [
            (f, f.stat().st_mtime)
            for f in session_dir.glob("*.jsonl")
            if is_valid_session_file(f)
        ]
        if not files:
            return None
        files.sort(key=lambda x: x[1], reverse=True)
        return str(files[0][0])
    except Exception:
        return None


class SessionManager:
    """
    Manages conversation sessions as append-only trees stored in JSONL files.

    Each session entry has an id and parentId forming a tree structure. The "leaf"
    pointer tracks the current position. Appending creates a child of the current leaf.
    Branching moves the leaf to an earlier entry, allowing new branches without
    modifying history.
    """

    def __init__(
        self,
        cwd: str | Path,
        session_dir: str | Path | None = None,
        session_file: str | Path | None = None,
        persist: bool = True,
    ):
        """
        Initialize session manager.

        Args:
            cwd: Working directory for the session
            session_dir: Directory for session files (default: ~/.pipy/sessions/<cwd>)
            session_file: Specific session file to load/create
            persist: Whether to persist to disk (False for in-memory)
        """
        self._cwd = str(cwd)
        self._persist = persist
        self._flushed = False

        # Initialize session directory
        if session_dir:
            self._session_dir = Path(session_dir)
        else:
            self._session_dir = get_default_session_dir(self._cwd)

        if persist:
            self._session_dir.mkdir(parents=True, exist_ok=True)

        # Session state
        self._session_id = ""
        self._session_file: Path | None = None
        self._file_entries: list[FileEntry] = []
        self._by_id: dict[str, SessionEntry] = {}
        self._labels_by_id: dict[str, str] = {}
        self._leaf_id: str | None = None

        # Initialize session
        if session_file:
            self.set_session_file(session_file)
        else:
            self.new_session()

    @classmethod
    def create(cls, cwd: str | Path) -> "SessionManager":
        """Create a new session manager, resuming most recent session if available."""
        cwd_str = str(cwd)
        session_dir = get_default_session_dir(cwd_str)
        most_recent = find_most_recent_session(session_dir)
        return cls(cwd_str, session_dir, most_recent)

    @classmethod
    def in_memory(cls, cwd: str | Path = ".") -> "SessionManager":
        """Create an in-memory session manager (no persistence)."""
        return cls(cwd, persist=False)

    # =========================================================================
    # Session File Management
    # =========================================================================

    def set_session_file(self, session_file: str | Path) -> None:
        """Switch to a different session file."""
        self._session_file = Path(session_file).resolve()

        if self._session_file.exists():
            self._file_entries = load_entries_from_file(self._session_file)

            # If file was empty or corrupted, start fresh
            if not self._file_entries:
                explicit_path = self._session_file
                self.new_session()
                self._session_file = explicit_path
                self._rewrite_file()
                self._flushed = True
                return

            # Extract session ID from header
            header = next((e for e in self._file_entries if e.get("type") == "session"), None)
            self._session_id = header.get("id", str(uuid.uuid4())) if header else str(uuid.uuid4())

            # Run migrations if needed
            if self._migrate_if_needed():
                self._rewrite_file()

            self._build_index()
            self._flushed = True
        else:
            explicit_path = self._session_file
            self.new_session()
            self._session_file = explicit_path

    def new_session(self, parent_session: str | None = None) -> str | None:
        """Create a new session. Returns the session file path."""
        self._session_id = str(uuid.uuid4())
        timestamp = now_iso()

        header: SessionHeader = {
            "type": "session",
            "version": CURRENT_SESSION_VERSION,
            "id": self._session_id,
            "timestamp": timestamp,
            "cwd": self._cwd,
            "parentSession": parent_session,
        }

        self._file_entries = [header]
        self._by_id.clear()
        self._labels_by_id.clear()
        self._leaf_id = None
        self._flushed = False

        if self._persist:
            file_timestamp = timestamp.replace(":", "-").replace(".", "-")
            self._session_file = self._session_dir / f"{file_timestamp}_{self._session_id}.jsonl"
            return str(self._session_file)

        return None

    def _migrate_if_needed(self) -> bool:
        """Run migrations if needed. Returns True if migrated."""
        header = next((e for e in self._file_entries if e.get("type") == "session"), None)
        version = header.get("version", 1) if header else 1

        if version >= CURRENT_SESSION_VERSION:
            return False

        # Run migrations (simplified - just update version)
        if header:
            header["version"] = CURRENT_SESSION_VERSION

        return True

    def _build_index(self) -> None:
        """Build the ID index from entries."""
        self._by_id.clear()
        self._labels_by_id.clear()
        self._leaf_id = None

        for entry in self._file_entries:
            if entry.get("type") == "session":
                continue
            entry_id = entry.get("id")
            if entry_id:
                self._by_id[entry_id] = entry
                self._leaf_id = entry_id
                if entry.get("type") == "label":
                    target_id = entry.get("targetId")
                    label = entry.get("label")
                    if target_id:
                        if label:
                            self._labels_by_id[target_id] = label
                        else:
                            self._labels_by_id.pop(target_id, None)

    def _rewrite_file(self) -> None:
        """Rewrite the entire session file."""
        if not self._persist or not self._session_file:
            return
        content = "\n".join(json.dumps(e) for e in self._file_entries) + "\n"
        self._session_file.write_text(content, encoding="utf-8")

    def _persist_entry(self, entry: SessionEntry) -> None:
        """Persist a single entry to the session file."""
        if not self._persist or not self._session_file:
            return

        # Only persist after first assistant message
        has_assistant = any(
            e.get("type") == "message" and e.get("message", {}).get("role") == "assistant"
            for e in self._file_entries
        )
        if not has_assistant:
            return

        if not self._flushed:
            # First persist - write all entries
            content = "\n".join(json.dumps(e) for e in self._file_entries) + "\n"
            self._session_file.write_text(content, encoding="utf-8")
            self._flushed = True
        else:
            # Append single entry
            with open(self._session_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

    def _append_entry(self, entry: SessionEntry) -> None:
        """Append an entry and update state."""
        self._file_entries.append(entry)
        entry_id = entry.get("id")
        if entry_id:
            self._by_id[entry_id] = entry
            self._leaf_id = entry_id
        self._persist_entry(entry)

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def cwd(self) -> str:
        return self._cwd

    @property
    def session_dir(self) -> Path:
        return self._session_dir

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def session_file(self) -> Path | None:
        return self._session_file

    @property
    def leaf_id(self) -> str | None:
        return self._leaf_id

    @property
    def is_persisted(self) -> bool:
        return self._persist

    # =========================================================================
    # Append Methods
    # =========================================================================

    def append_message(self, message: AgentMessage) -> str:
        """Append a message. Returns entry ID."""
        # Convert Pydantic model to dict for JSON serialization
        if hasattr(message, "model_dump"):
            msg_dict = message.model_dump(mode="json", exclude_none=True)
        elif hasattr(message, "dict"):
            msg_dict = message.dict(exclude_none=True)
        else:
            msg_dict = message  # Already a dict

        entry: SessionMessageEntry = {
            "type": "message",
            "id": generate_id(set(self._by_id.keys())),
            "parentId": self._leaf_id,
            "timestamp": now_iso(),
            "message": msg_dict,
        }
        self._append_entry(entry)
        return entry["id"]

    def append_thinking_level_change(self, thinking_level: str) -> str:
        """Append a thinking level change. Returns entry ID."""
        entry: ThinkingLevelChangeEntry = {
            "type": "thinking_level_change",
            "id": generate_id(set(self._by_id.keys())),
            "parentId": self._leaf_id,
            "timestamp": now_iso(),
            "thinkingLevel": thinking_level,
        }
        self._append_entry(entry)
        return entry["id"]

    def append_model_change(self, provider: str, model_id: str) -> str:
        """Append a model change. Returns entry ID."""
        entry: ModelChangeEntry = {
            "type": "model_change",
            "id": generate_id(set(self._by_id.keys())),
            "parentId": self._leaf_id,
            "timestamp": now_iso(),
            "provider": provider,
            "modelId": model_id,
        }
        self._append_entry(entry)
        return entry["id"]

    def append_compaction(
        self,
        summary: str,
        first_kept_entry_id: str,
        tokens_before: int,
        details: Any = None,
        from_hook: bool = False,
    ) -> str:
        """Append a compaction summary. Returns entry ID."""
        entry: CompactionEntry = {
            "type": "compaction",
            "id": generate_id(set(self._by_id.keys())),
            "parentId": self._leaf_id,
            "timestamp": now_iso(),
            "summary": summary,
            "firstKeptEntryId": first_kept_entry_id,
            "tokensBefore": tokens_before,
            "details": details,
            "fromHook": from_hook if from_hook else None,
        }
        self._append_entry(entry)
        return entry["id"]

    def append_custom_entry(self, custom_type: str, data: Any = None) -> str:
        """Append a custom entry for extensions. Returns entry ID."""
        entry: CustomEntry = {
            "type": "custom",
            "id": generate_id(set(self._by_id.keys())),
            "parentId": self._leaf_id,
            "timestamp": now_iso(),
            "customType": custom_type,
            "data": data,
        }
        self._append_entry(entry)
        return entry["id"]

    def append_custom_message(
        self,
        custom_type: str,
        content: str | list[dict],
        display: bool,
        details: Any = None,
    ) -> str:
        """Append a custom message entry for LLM context. Returns entry ID."""
        entry: CustomMessageEntry = {
            "type": "custom_message",
            "id": generate_id(set(self._by_id.keys())),
            "parentId": self._leaf_id,
            "timestamp": now_iso(),
            "customType": custom_type,
            "content": content,
            "display": display,
            "details": details,
        }
        self._append_entry(entry)
        return entry["id"]

    def append_session_info(self, name: str) -> str:
        """Append session info (e.g., display name). Returns entry ID."""
        entry: SessionInfoEntry = {
            "type": "session_info",
            "id": generate_id(set(self._by_id.keys())),
            "parentId": self._leaf_id,
            "timestamp": now_iso(),
            "name": name.strip() if name else None,
        }
        self._append_entry(entry)
        return entry["id"]

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_entry(self, entry_id: str) -> SessionEntry | None:
        """Get an entry by ID."""
        return self._by_id.get(entry_id)

    def get_leaf_entry(self) -> SessionEntry | None:
        """Get the current leaf entry."""
        return self._by_id.get(self._leaf_id) if self._leaf_id else None

    def get_entries(self) -> list[SessionEntry]:
        """Get all session entries (excluding header)."""
        return [e for e in self._file_entries if e.get("type") != "session"]

    def get_header(self) -> SessionHeader | None:
        """Get the session header."""
        return next((e for e in self._file_entries if e.get("type") == "session"), None)

    def get_label(self, entry_id: str) -> str | None:
        """Get the label for an entry, if any."""
        return self._labels_by_id.get(entry_id)

    def get_session_name(self) -> str | None:
        """Get the session display name, if set."""
        entries = self.get_entries()
        for entry in reversed(entries):
            if entry.get("type") == "session_info" and entry.get("name"):
                return entry.get("name")
        return None

    def get_children(self, parent_id: str) -> list[SessionEntry]:
        """Get all direct children of an entry."""
        return [e for e in self._by_id.values() if e.get("parentId") == parent_id]

    def build_session_context(self, leaf_id: str | None = None) -> SessionContext:
        """Build the session context for LLM from entries."""
        entries = self.get_entries()
        return build_session_context(entries, leaf_id or self._leaf_id, self._by_id)

    # =========================================================================
    # Branching
    # =========================================================================

    def set_leaf(self, entry_id: str | None) -> None:
        """Move the leaf pointer to a different entry (for branching)."""
        if entry_id is None:
            self._leaf_id = None
        elif entry_id in self._by_id:
            self._leaf_id = entry_id
        else:
            raise ValueError(f"Entry {entry_id} not found")

    def get_branch(self, leaf_id: str | None = None) -> list[SessionEntry]:
        """Get the path from root to the specified leaf (or current leaf)."""
        target = leaf_id or self._leaf_id
        if not target:
            return []

        path: list[SessionEntry] = []
        current = self._by_id.get(target)
        while current:
            path.insert(0, current)
            parent_id = current.get("parentId")
            current = self._by_id.get(parent_id) if parent_id else None

        return path

    # =========================================================================
    # Session Listing
    # =========================================================================

    @staticmethod
    def list_sessions(session_dir: str | Path) -> list[SessionInfo]:
        """List all sessions in a directory."""
        session_dir = Path(session_dir)
        if not session_dir.exists():
            return []

        sessions: list[SessionInfo] = []
        for file_path in session_dir.glob("*.jsonl"):
            if not is_valid_session_file(file_path):
                continue

            try:
                info = SessionManager._build_session_info(file_path)
                if info:
                    sessions.append(info)
            except Exception:
                pass

        # Sort by modified date, most recent first
        sessions.sort(key=lambda s: s.modified, reverse=True)
        return sessions

    @staticmethod
    def _build_session_info(file_path: Path) -> SessionInfo | None:
        """Build session info from a session file."""
        try:
            entries = load_entries_from_file(file_path)
            if not entries:
                return None

            header = entries[0]
            if header.get("type") != "session":
                return None

            stats = file_path.stat()
            message_count = 0
            first_message = ""
            all_messages: list[str] = []
            name = None

            for entry in entries:
                # Extract session name
                if entry.get("type") == "session_info" and entry.get("name"):
                    name = entry.get("name")

                if entry.get("type") != "message":
                    continue
                message_count += 1

                message = entry.get("message", {})
                role = message.get("role")
                if role not in ("user", "assistant"):
                    continue

                # Extract text content
                content = message.get("content", "")
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = " ".join(
                        block.get("text", "")
                        for block in content
                        if block.get("type") == "text"
                    )
                else:
                    text = ""

                if text:
                    all_messages.append(text)
                    if not first_message and role == "user":
                        first_message = text

            return SessionInfo(
                path=str(file_path),
                id=header.get("id", ""),
                cwd=header.get("cwd", ""),
                name=name,
                parent_session_path=header.get("parentSession"),
                created=datetime.fromisoformat(header.get("timestamp", "").rstrip("Z")),
                modified=datetime.fromtimestamp(stats.st_mtime),
                message_count=message_count,
                first_message=first_message or "(no messages)",
                all_messages_text=" ".join(all_messages),
            )
        except Exception:
            return None
