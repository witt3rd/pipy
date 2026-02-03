"""Settings types and defaults."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class CompactionSettings:
    """Settings for context compaction."""

    enabled: bool = True
    reserve_tokens: int = 16384  # Tokens reserved for prompt + response
    keep_recent_tokens: int = 20000  # Recent tokens to keep


@dataclass
class RetrySettings:
    """Settings for automatic retries."""

    enabled: bool = True
    max_retries: int = 3
    base_delay_ms: int = 2000  # Exponential backoff: 2s, 4s, 8s
    max_delay_ms: int = 60000  # Max server-requested delay


@dataclass
class ImageSettings:
    """Settings for image handling."""

    auto_resize: bool = True  # Resize to 2000x2000 max
    block_images: bool = False  # Block all images from LLM


@dataclass
class TerminalSettings:
    """Settings for terminal behavior."""

    show_images: bool = True  # Only relevant if terminal supports images
    clear_on_shrink: bool = False  # Clear empty rows when content shrinks


@dataclass
class ThinkingBudgets:
    """Token budgets for thinking levels."""

    minimal: int = 1024
    low: int = 4096
    medium: int = 16384
    high: int = 32768


ThinkingLevel = Literal["off", "minimal", "low", "medium", "high", "xhigh"]
SteeringMode = Literal["all", "one-at-a-time"]
FollowUpMode = Literal["all", "one-at-a-time"]
DoubleEscapeAction = Literal["fork", "tree", "none"]


@dataclass
class Settings:
    """Application settings with sensible defaults."""

    # Model defaults
    default_provider: str | None = None
    default_model: str | None = None
    default_thinking_level: ThinkingLevel = "medium"

    # Behavior modes
    steering_mode: SteeringMode = "all"
    follow_up_mode: FollowUpMode = "all"

    # UI
    theme: str | None = None
    hide_thinking_block: bool = False
    quiet_startup: bool = False

    # Shell
    shell_path: str | None = None
    shell_command_prefix: str | None = None

    # Nested settings
    compaction: CompactionSettings = field(default_factory=CompactionSettings)
    retry: RetrySettings = field(default_factory=RetrySettings)
    images: ImageSettings = field(default_factory=ImageSettings)
    terminal: TerminalSettings = field(default_factory=TerminalSettings)
    thinking_budgets: ThinkingBudgets = field(default_factory=ThinkingBudgets)

    # Resource paths (arrays of local paths)
    extensions: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)

    # Skill behavior
    enable_skill_commands: bool = True

    # Model cycling
    enabled_models: list[str] = field(default_factory=list)

    # UI behavior
    double_escape_action: DoubleEscapeAction = "tree"
    autocomplete_max_visible: int = 5
    editor_padding_x: int = 0
    show_hardware_cursor: bool = False


DEFAULT_SETTINGS = Settings()
