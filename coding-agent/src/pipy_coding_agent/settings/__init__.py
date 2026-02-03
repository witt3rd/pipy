"""Settings management with global/project hierarchy."""

from .manager import (
    CONFIG_DIR_NAME,
    SettingsManager,
    deep_merge,
    get_default_agent_dir,
)
from .types import (
    CompactionSettings,
    DEFAULT_SETTINGS,
    DoubleEscapeAction,
    FollowUpMode,
    ImageSettings,
    RetrySettings,
    Settings,
    SteeringMode,
    TerminalSettings,
    ThinkingBudgets,
    ThinkingLevel,
)

__all__ = [
    # Manager
    "SettingsManager",
    "get_default_agent_dir",
    "CONFIG_DIR_NAME",
    "deep_merge",
    # Types
    "Settings",
    "DEFAULT_SETTINGS",
    "CompactionSettings",
    "RetrySettings",
    "ImageSettings",
    "TerminalSettings",
    "ThinkingBudgets",
    "ThinkingLevel",
    "SteeringMode",
    "FollowUpMode",
    "DoubleEscapeAction",
]
