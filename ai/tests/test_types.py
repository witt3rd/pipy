"""Tests for types module."""

from pipy_ai import (
    AssistantMessage,
    CacheRetention,
    Context,
    Cost,
    ImageContent,
    SimpleStreamOptions,
    StopReason,
    StreamOptions,
    TextContent,
    ThinkingContent,
    ThinkingLevel,
    Tool,
    ToolCall,
    ToolResultMessage,
    Usage,
    UserMessage,
)


class TestEnums:
    def test_thinking_level_values(self):
        assert ThinkingLevel.MINIMAL == "minimal"
        assert ThinkingLevel.LOW == "low"
        assert ThinkingLevel.MEDIUM == "medium"
        assert ThinkingLevel.HIGH == "high"
        assert ThinkingLevel.XHIGH == "xhigh"

    def test_cache_retention_values(self):
        assert CacheRetention.NONE == "none"
        assert CacheRetention.SHORT == "short"
        assert CacheRetention.LONG == "long"

    def test_stop_reason_values(self):
        assert StopReason.STOP == "stop"
        assert StopReason.LENGTH == "length"
        assert StopReason.TOOL_USE == "toolUse"
        assert StopReason.SENSITIVE == "sensitive"
        assert StopReason.ERROR == "error"
        assert StopReason.ABORTED == "aborted"


class TestContentTypes:
    def test_text_content_defaults(self):
        tc = TextContent()
        assert tc.type == "text"
        assert tc.text == ""
        assert tc.text_signature is None

    def test_text_content_with_values(self):
        tc = TextContent(text="Hello world", text_signature="sig123")
        assert tc.text == "Hello world"
        assert tc.text_signature == "sig123"

    def test_thinking_content_defaults(self):
        tc = ThinkingContent()
        assert tc.type == "thinking"
        assert tc.thinking == ""

    def test_image_content_defaults(self):
        ic = ImageContent()
        assert ic.type == "image"
        assert ic.data == ""
        assert ic.mime_type == "image/png"

    def test_tool_call_defaults(self):
        tc = ToolCall()
        assert tc.type == "toolCall"
        assert tc.id == ""
        assert tc.name == ""
        assert tc.arguments == {}

    def test_tool_call_with_arguments(self):
        tc = ToolCall(
            id="call_123",
            name="get_weather",
            arguments={"location": "Tokyo"},
        )
        assert tc.id == "call_123"
        assert tc.name == "get_weather"
        assert tc.arguments == {"location": "Tokyo"}


class TestMessages:
    def test_user_message_string_content(self):
        msg = UserMessage(content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_user_message_list_content(self):
        msg = UserMessage(
            content=[
                TextContent(text="Check this image"),
                ImageContent(data="base64data", mime_type="image/jpeg"),
            ]
        )
        assert msg.role == "user"
        assert len(msg.content) == 2
        assert isinstance(msg.content[0], TextContent)
        assert isinstance(msg.content[1], ImageContent)

    def test_assistant_message_text_property(self):
        msg = AssistantMessage(
            content=[
                TextContent(text="Hello"),
                TextContent(text="World"),
            ]
        )
        assert msg.text == "Hello\nWorld"

    def test_assistant_message_thinking_property(self):
        msg = AssistantMessage(
            content=[
                ThinkingContent(thinking="Let me think..."),
                TextContent(text="The answer is 42"),
            ]
        )
        assert msg.thinking_text == "Let me think..."
        assert msg.text == "The answer is 42"

    def test_assistant_message_tool_calls_property(self):
        tc1 = ToolCall(id="1", name="func1")
        tc2 = ToolCall(id="2", name="func2")
        msg = AssistantMessage(
            content=[
                TextContent(text="I'll help"),
                tc1,
                tc2,
            ]
        )
        assert len(msg.tool_calls) == 2
        assert msg.tool_calls[0].name == "func1"
        assert msg.tool_calls[1].name == "func2"

    def test_tool_result_message(self):
        msg = ToolResultMessage(
            tool_call_id="call_123",
            tool_name="get_weather",
            content=[TextContent(text="Sunny, 22°C")],
        )
        assert msg.role == "toolResult"
        assert msg.tool_call_id == "call_123"
        assert msg.is_error is False


class TestUsageAndCost:
    def test_cost_defaults(self):
        cost = Cost()
        assert cost.input == 0.0
        assert cost.output == 0.0
        assert cost.total == 0.0

    def test_usage_defaults(self):
        usage = Usage()
        assert usage.input == 0
        assert usage.output == 0
        assert usage.total_tokens == 0
        assert isinstance(usage.cost, Cost)


class TestTool:
    def test_tool_creation(self):
        tool = Tool(
            name="get_weather",
            description="Get weather for a location",
            parameters={
                "type": "object",
                "properties": {
                    "location": {"type": "string"},
                },
                "required": ["location"],
            },
        )
        assert tool.name == "get_weather"
        assert "location" in tool.parameters["properties"]


class TestContext:
    def test_context_defaults(self):
        ctx = Context()
        assert ctx.system_prompt is None
        assert ctx.messages == []
        assert ctx.tools is None

    def test_context_with_messages(self):
        ctx = Context(
            system_prompt="You are helpful.",
            messages=[
                UserMessage(content="Hello"),
                AssistantMessage(content=[TextContent(text="Hi!")]),
            ],
        )
        assert ctx.system_prompt == "You are helpful."
        assert len(ctx.messages) == 2


class TestOptions:
    def test_stream_options_defaults(self):
        opts = StreamOptions()
        assert opts.temperature is None
        assert opts.max_tokens is None
        assert opts.cache_retention == CacheRetention.SHORT

    def test_simple_stream_options_reasoning(self):
        opts = SimpleStreamOptions(reasoning=ThinkingLevel.HIGH)
        assert opts.reasoning == ThinkingLevel.HIGH
