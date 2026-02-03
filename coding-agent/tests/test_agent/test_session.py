"""Tests for agent session."""

import pytest
import tempfile
from pathlib import Path

from pipy_coding_agent.agent import (
    AgentSession,
    AgentSessionConfig,
    PromptOptions,
)


class TestAgentSessionConfig:
    def test_default_values(self):
        """Test default configuration values."""
        config = AgentSessionConfig()

        assert config.model == "sonnet"
        assert config.thinking_level == "medium"
        assert config.auto_compact is True
        assert config.persist_session is True

    def test_custom_values(self):
        """Test custom configuration."""
        config = AgentSessionConfig(
            model="opus",
            thinking_level="high",
            auto_compact=False,
        )

        assert config.model == "opus"
        assert config.thinking_level == "high"
        assert config.auto_compact is False


class TestAgentSession:
    def test_create_session(self):
        """Test creating an agent session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AgentSessionConfig(
                cwd=tmpdir,
                persist_session=False,
            )

            session = AgentSession(config)

            assert session.cwd == Path(tmpdir)
            assert session.model.provider == "anthropic"

    def test_model_property(self):
        """Test model property."""
        config = AgentSessionConfig(
            model="sonnet",
            persist_session=False,
        )

        session = AgentSession(config)

        assert session.model.provider == "anthropic"
        assert "claude" in session.model.model_name.lower()

    def test_set_model(self):
        """Test changing model."""
        config = AgentSessionConfig(
            model="sonnet",
            persist_session=False,
        )
        session = AgentSession(config)

        session.set_model("gpt4o")

        assert session.model.provider == "openai"

    def test_thinking_level(self):
        """Test thinking level property."""
        config = AgentSessionConfig(
            thinking_level="high",
            persist_session=False,
        )
        session = AgentSession(config)

        assert session.thinking_level == "high"

        session.set_thinking_level("low")
        assert session.thinking_level == "low"

    def test_system_prompt_generated(self):
        """Test system prompt is generated."""
        config = AgentSessionConfig(persist_session=False)
        session = AgentSession(config)

        assert len(session.system_prompt) > 0
        assert "coding" in session.system_prompt.lower() or "assistant" in session.system_prompt.lower()

    def test_custom_system_prompt(self):
        """Test custom system prompt."""
        config = AgentSessionConfig(
            system_prompt="You are a test assistant.",
            persist_session=False,
        )
        session = AgentSession(config)

        assert "test assistant" in session.system_prompt

    def test_event_listener(self):
        """Test adding event listener."""
        config = AgentSessionConfig(persist_session=False)
        session = AgentSession(config)

        events = []
        session.on_event(lambda e, d: events.append(e))

        session._emit("test_event", {"data": 1})

        assert "test_event" in events


class TestPromptOptions:
    def test_default_values(self):
        """Test default prompt options."""
        options = PromptOptions()

        assert options.images == []
        assert options.no_tools is False
        assert options.thinking_level is None

    def test_custom_values(self):
        """Test custom prompt options."""
        options = PromptOptions(
            images=["/path/to/image.png"],
            no_tools=True,
            thinking_level="high",
        )

        assert len(options.images) == 1
        assert options.no_tools is True
        assert options.thinking_level == "high"


# Note: Full prompt() tests would require mocking the LLM
# which we'll skip for unit tests
