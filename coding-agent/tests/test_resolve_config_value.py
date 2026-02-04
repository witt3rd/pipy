"""Tests for resolve_config_value module."""

import os

from pipy_coding_agent.settings.resolve_config_value import (
    clear_config_value_cache,
    resolve_config_value,
    resolve_headers,
)


class TestResolveConfigValue:
    """Test resolve_config_value function."""

    def setup_method(self):
        clear_config_value_cache()

    def test_literal_value(self):
        """Non-env-var, non-command strings are returned as-is."""
        result = resolve_config_value("sk-1234567890")
        assert result == "sk-1234567890"

    def test_env_var_lookup(self):
        """If config matches an env var name, return env var value."""
        os.environ["TEST_PIPY_API_KEY"] = "secret-key"
        try:
            result = resolve_config_value("TEST_PIPY_API_KEY")
            assert result == "secret-key"
        finally:
            del os.environ["TEST_PIPY_API_KEY"]

    def test_shell_command(self):
        """Config starting with ! executes shell command."""
        result = resolve_config_value("!echo hello-from-shell")
        assert result == "hello-from-shell"

    def test_shell_command_cached(self):
        """Shell command results are cached."""
        result1 = resolve_config_value("!echo cached-test")
        result2 = resolve_config_value("!echo cached-test")
        assert result1 == result2 == "cached-test"

    def test_shell_command_failure(self):
        """Failed shell commands return None."""
        result = resolve_config_value("!nonexistent-command-xyz-12345")
        assert result is None

    def test_clear_cache(self):
        """Cache can be cleared."""
        resolve_config_value("!echo cache-clear-test")
        clear_config_value_cache()
        # Should not error after clearing
        result = resolve_config_value("!echo cache-clear-test")
        assert result == "cache-clear-test"


class TestResolveHeaders:
    """Test resolve_headers function."""

    def test_none_headers(self):
        assert resolve_headers(None) is None

    def test_empty_headers(self):
        assert resolve_headers({}) is None

    def test_literal_headers(self):
        result = resolve_headers({"Authorization": "Bearer token123"})
        assert result == {"Authorization": "Bearer token123"}

    def test_env_var_headers(self):
        os.environ["TEST_PIPY_HEADER"] = "header-value"
        try:
            result = resolve_headers({"X-Custom": "TEST_PIPY_HEADER"})
            assert result == {"X-Custom": "header-value"}
        finally:
            del os.environ["TEST_PIPY_HEADER"]

    def test_command_headers(self):
        result = resolve_headers({"X-Token": "!echo dynamic-token"})
        assert result == {"X-Token": "dynamic-token"}
