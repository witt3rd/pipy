"""Extension system for pipy-coding-agent."""

from .loader import (
    Extension,
    ExtensionManifest,
    ExtensionLoader,
    load_extension,
    load_extensions_from_dir,
)
from .hooks import (
    ExtensionHooks,
    HookType,
)

__all__ = [
    # Loader
    "Extension",
    "ExtensionManifest",
    "ExtensionLoader",
    "load_extension",
    "load_extensions_from_dir",
    # Hooks
    "ExtensionHooks",
    "HookType",
]
