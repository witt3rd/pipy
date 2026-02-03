"""Model registry with models.dev integration."""

from ..types import Cost, Usage
from .registry import ModelRegistry, get_registry, reload_registry
from .schema import Model, ModelCapabilities, ModelCost, ModelLimits, ModelModalities
from .sync import ensure_models_cache, load_models_cache, sync_models


def get_model(name: str) -> Model | None:
    """Get model by name with smart matching.

    Args:
        name: Full name "anthropic/claude-sonnet-4-5" or short "claude-sonnet-4-5"

    Example:
        model = get_model("anthropic/claude-sonnet-4-5")
        print(f"Context: {model.limits.context}, Cost: ${model.cost.input}/1M")
    """
    return get_registry().get(name)


def get_models(
    provider: str | None = None,
    capability: str | None = None,
    modality: str | None = None,
    min_context: int | None = None,
    max_cost_input: float | None = None,
) -> list[Model]:
    """Query models with filters.

    Args:
        provider: Filter by provider (e.g., "anthropic")
        capability: Filter by capability ("reasoning", "tool_call", "structured_output")
        modality: Filter by input modality ("image", "audio", "video", "pdf")
        min_context: Minimum context window size
        max_cost_input: Maximum input cost per 1M tokens

    Examples:
        # All reasoning models
        get_models(capability="reasoning")

        # Anthropic models that accept images
        get_models(provider="anthropic", modality="image")

        # Cheap models with 100k+ context
        get_models(min_context=100000, max_cost_input=1.0)
    """
    registry = get_registry()
    models = registry.list_all()

    if provider:
        models = [m for m in models if m.provider == provider]
    if capability:
        models = [m for m in models if getattr(m.capabilities, capability, False)]
    if modality:
        models = [m for m in models if modality in m.modalities.input]
    if min_context:
        models = [m for m in models if m.limits.context >= min_context]
    if max_cost_input:
        models = [m for m in models if m.cost.input <= max_cost_input]

    return models


def calculate_cost(model: str | Model, usage: Usage) -> Cost:
    """Calculate actual cost from usage after a request.

    Args:
        model: Model name or Model object
        usage: Usage from response

    Returns:
        Cost breakdown (input, output, cache_read, cache_write, total)

    Example:
        result = complete(model, context)
        cost = calculate_cost(model, result.usage)
        print(f"Request cost: ${cost.total:.4f}")
    """
    if isinstance(model, str):
        m = get_model(model)
        if not m:
            raise ValueError(f"Unknown model: {model}")
    else:
        m = model

    input_cost = (m.cost.input / 1_000_000) * usage.input
    output_cost = (m.cost.output / 1_000_000) * usage.output
    cache_read_cost = (m.cost.cache_read / 1_000_000) * usage.cache_read
    cache_write_cost = (m.cost.cache_write / 1_000_000) * usage.cache_write

    return Cost(
        input=input_cost,
        output=output_cost,
        cache_read=cache_read_cost,
        cache_write=cache_write_cost,
        total=input_cost + output_cost + cache_read_cost + cache_write_cost,
    )


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int = 0,
    cached_tokens: int = 0,
) -> float:
    """Estimate cost before making a request.

    Args:
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cached_tokens: Number of cached input tokens

    Returns:
        Estimated cost in dollars

    Example:
        est = estimate_cost("anthropic/claude-opus-4", 50000, 8000)
        if est > 1.0:
            print(f"Warning: estimated cost ${est:.2f}")
    """
    m = get_model(model)
    if not m:
        raise ValueError(f"Unknown model: {model}")

    input_cost = (input_tokens / 1_000_000) * m.cost.input
    output_cost = (output_tokens / 1_000_000) * m.cost.output
    cache_savings = (cached_tokens / 1_000_000) * (m.cost.input - m.cost.cache_read)

    return input_cost + output_cost - cache_savings


__all__ = [
    # Registry
    "get_registry",
    "reload_registry",
    "ModelRegistry",
    # Lookup
    "get_model",
    "get_models",
    # Cost
    "calculate_cost",
    "estimate_cost",
    # Sync
    "sync_models",
    "load_models_cache",
    "ensure_models_cache",
    # Schema
    "Model",
    "ModelCost",
    "ModelLimits",
    "ModelCapabilities",
    "ModelModalities",
]
