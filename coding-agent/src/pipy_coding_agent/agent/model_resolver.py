"""Model resolution - mapping model names to providers and configs."""

import os
from dataclasses import dataclass
from typing import Any


# Common model aliases
MODEL_ALIASES: dict[str, str] = {
    # Claude aliases
    "claude": "anthropic/claude-sonnet-4-20250514",
    "sonnet": "anthropic/claude-sonnet-4-20250514",
    "opus": "anthropic/claude-3-opus-20240229",
    "haiku": "anthropic/claude-3-5-haiku-20241022",
    # GPT aliases
    "gpt4": "openai/gpt-4-turbo",
    "gpt4o": "openai/gpt-4o",
    "o1": "openai/o1",
    "o3": "openai/o3-mini",
    # Gemini aliases
    "gemini": "google/gemini-2.0-flash",
    "gemini-pro": "google/gemini-1.5-pro",
}

# Default context windows (can be overridden by registry)
DEFAULT_CONTEXT_WINDOWS: dict[str, int] = {
    "anthropic/claude-sonnet-4-20250514": 200000,
    "anthropic/claude-3-opus-20240229": 200000,
    "anthropic/claude-3-5-haiku-20241022": 200000,
    "openai/gpt-4-turbo": 128000,
    "openai/gpt-4o": 128000,
    "openai/o1": 200000,
    "openai/o3-mini": 200000,
    "google/gemini-2.0-flash": 1000000,
    "google/gemini-1.5-pro": 2000000,
}


@dataclass
class ResolvedModel:
    """A resolved model configuration."""

    provider: str
    """Provider name (e.g., 'anthropic', 'openai')."""

    model_id: str
    """Full model identifier (e.g., 'anthropic/claude-sonnet-4-20250514')."""

    model_name: str
    """Model name without provider (e.g., 'claude-sonnet-4-20250514')."""

    context_window: int
    """Context window size in tokens."""

    api_key: str | None = None
    """API key for the provider."""

    supports_thinking: bool = False
    """Whether model supports extended thinking."""

    supports_images: bool = True
    """Whether model supports image inputs."""


class ModelResolver:
    """
    Resolves model names to full configurations.

    Handles:
    - Alias expansion (e.g., 'sonnet' -> 'anthropic/claude-sonnet-4-20250514')
    - Provider extraction from model ID
    - API key lookup from environment
    - Context window defaults
    """

    def __init__(
        self,
        aliases: dict[str, str] | None = None,
        context_windows: dict[str, int] | None = None,
        default_provider: str = "anthropic",
    ):
        """
        Initialize model resolver.

        Args:
            aliases: Custom model aliases
            context_windows: Custom context window sizes
            default_provider: Default provider when not specified
        """
        self._aliases = {**MODEL_ALIASES, **(aliases or {})}
        self._context_windows = {**DEFAULT_CONTEXT_WINDOWS, **(context_windows or {})}
        self._default_provider = default_provider

    def resolve(self, model: str) -> ResolvedModel:
        """
        Resolve a model name to full configuration.

        Args:
            model: Model name or alias

        Returns:
            ResolvedModel with full configuration
        """
        # Expand alias
        model_id = self._aliases.get(model.lower(), model)

        # Extract provider and model name
        if "/" in model_id:
            provider, model_name = model_id.split("/", 1)
        else:
            provider = self._default_provider
            model_name = model_id
            model_id = f"{provider}/{model_name}"

        # Get context window
        context_window = self._context_windows.get(model_id, 128000)

        # Get API key from environment
        api_key = self._get_api_key(provider)

        # Check capabilities
        supports_thinking = "claude" in model_name.lower() or "o1" in model_name.lower()

        return ResolvedModel(
            provider=provider,
            model_id=model_id,
            model_name=model_name,
            context_window=context_window,
            api_key=api_key,
            supports_thinking=supports_thinking,
        )

    def _get_api_key(self, provider: str) -> str | None:
        """Get API key for provider from environment."""
        env_vars = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "google": "GOOGLE_API_KEY",
            "groq": "GROQ_API_KEY",
            "together": "TOGETHER_API_KEY",
            "mistral": "MISTRAL_API_KEY",
        }
        env_var = env_vars.get(provider.lower())
        if env_var:
            return os.environ.get(env_var)
        return None

    def list_aliases(self) -> dict[str, str]:
        """Get all model aliases."""
        return self._aliases.copy()


# Convenience function
def resolve_model(model: str) -> ResolvedModel:
    """Resolve a model name using default resolver."""
    return ModelResolver().resolve(model)
