# pipy-ai

Streaming LLM library with rich types, models.dev integration, and LiteLLM backend.

## Installation

```bash
pip install pipy-ai
```

## Quick Start

```python
from pipy_ai import quick

# One-liner
result = quick("What is 2+2?")
print(result.text)  # "4"
```

## Standard Usage

```python
from pipy_ai import complete, ctx, user

result = complete("anthropic/claude-sonnet-4-5", ctx(
    user("Write a haiku about Python."),
    system="You are a poet."
))
print(result.text)
```

## Streaming

```python
from pipy_ai import stream, Context, UserMessage

context = Context(
    system_prompt="You are helpful.",
    messages=[UserMessage(content="Write a short story.")]
)

for event in stream("anthropic/claude-sonnet-4-5", context):
    if event.type == "text_delta":
        print(event.delta, end="", flush=True)
print()
```

## Async Variants

```python
import asyncio
from pipy_ai import acomplete, astream

async def main():
    result = await acomplete("anthropic/claude-sonnet-4-5", context)
    
    async for event in astream("anthropic/claude-sonnet-4-5", context):
        if event.type == "text_delta":
            print(event.delta, end="")

asyncio.run(main())
```

## Model Discovery

```python
from pipy_ai import get_models, get_model, estimate_cost

# Find all reasoning models
reasoning_models = get_models(capability="reasoning")
print(f"Found {len(reasoning_models)} reasoning models")

# Get model details
model = get_model("anthropic/claude-sonnet-4-5")
print(f"{model.name}: ${model.cost.input}/1M input tokens")

# Estimate cost before request
cost = estimate_cost("anthropic/claude-opus-4", input_tokens=50000, output_tokens=8000)
print(f"Estimated cost: ${cost:.2f}")
```

## CLI

```bash
# Sync models from models.dev
pipy sync

# List models
pipy models --capability reasoning
pipy models --provider anthropic

# Show model info
pipy info anthropic/claude-sonnet-4-5

# Estimate cost
pipy cost anthropic/claude-sonnet-4-5 --input 10000 --output 2000
```

## Development

```bash
# Clone and install
git clone https://github.com/witt3rd/pipy-ai
cd pipy-ai
uv sync --extra dev

# Run tests
uv run pytest tests/ -v

# Run integration tests (requires API keys)
uv run pytest tests/test_integration.py -v --run-integration

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type check
uv run mypy src/pipy_ai --ignore-missing-imports

# Set up pre-commit hooks (optional)
uv run pre-commit install
uv run pre-commit install --hook-type pre-push
```

## Acknowledgments

This library is a Python port inspired by the excellent TypeScript work of **Mario Zechner** ([@badlogic](https://github.com/badlogic)):

- **[pi-mono](https://github.com/mariozechner/pi)** - The original monorepo containing `@mariozechner/pi-ai`
- **[pi](https://github.com/mariozechner/pi)** - Mario's AI coding assistant built on these foundations

The architecture, type system, and streaming patterns in pipy-ai closely follow Mario's elegant design. Thank you Mario for the inspiration and for open-sourcing your work! 🙏

## License

MIT
