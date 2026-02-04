"""Resolve configuration values that may be shell commands, environment variables, or literals.

Used by auth storage and model resolution. Matches upstream resolve-config-value.ts.
"""

import os
import subprocess

# Cache for shell command results (persists for process lifetime)
_command_result_cache: dict[str, str | None] = {}


def resolve_config_value(config: str) -> str | None:
    """Resolve a config value (API key, header value, etc.) to an actual value.

    - If starts with "!", executes the rest as a shell command and uses stdout (cached)
    - Otherwise checks environment variable first, then treats as literal (not cached)
    """
    if config.startswith("!"):
        return _execute_command(config)

    env_value = os.environ.get(config)
    return env_value or config


def _execute_command(command_config: str) -> str | None:
    """Execute a shell command and cache the result."""
    if command_config in _command_result_cache:
        return _command_result_cache[command_config]

    command = command_config[1:]  # Strip the "!" prefix
    result: str | None = None

    try:
        output = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if output.stdout.strip():
            result = output.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        result = None

    _command_result_cache[command_config] = result
    return result


def resolve_headers(headers: dict[str, str] | None) -> dict[str, str] | None:
    """Resolve all header values using the same resolution logic as API keys."""
    if not headers:
        return None

    resolved: dict[str, str] = {}
    for key, value in headers.items():
        resolved_value = resolve_config_value(value)
        if resolved_value:
            resolved[key] = resolved_value

    return resolved if resolved else None


def clear_config_value_cache() -> None:
    """Clear the config value command cache. Exported for testing."""
    _command_result_cache.clear()
