"""Tests for API module."""

from pipy_ai import (
    AssistantMessage,
    Context,
    UserMessage,
    ctx,
    user,
)


class TestContextBuilders:
    def test_user_creates_user_message(self):
        msg = user("Hello world")
        assert isinstance(msg, UserMessage)
        assert msg.content == "Hello world"
        assert msg.role == "user"
        assert msg.timestamp > 0

    def test_ctx_creates_context(self):
        context = ctx(user("Hello"))
        assert isinstance(context, Context)
        assert len(context.messages) == 1
        assert context.messages[0].content == "Hello"

    def test_ctx_with_system_prompt(self):
        context = ctx(
            user("Hello"),
            system="You are helpful.",
        )
        assert context.system_prompt == "You are helpful."
        assert len(context.messages) == 1

    def test_ctx_with_multiple_messages(self):
        msg1 = user("First message")
        msg2 = AssistantMessage(content=[])
        msg3 = user("Second message")

        context = ctx(msg1, msg2, msg3)
        assert len(context.messages) == 3


class TestContextModel:
    def test_context_serialization(self):
        context = Context(
            system_prompt="Be helpful",
            messages=[UserMessage(content="Hi", timestamp=12345)],
        )
        # Pydantic model can be serialized
        data = context.model_dump()
        assert data["system_prompt"] == "Be helpful"
        assert len(data["messages"]) == 1

    def test_context_validation(self):
        # Should accept valid data
        context = Context(
            messages=[
                {"role": "user", "content": "Hello", "timestamp": 0},
            ]
        )
        assert len(context.messages) == 1
