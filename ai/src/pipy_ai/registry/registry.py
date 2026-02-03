"""Runtime model registry."""

import logging
from typing import Any

from .schema import Model
from .sync import ensure_models_cache, load_models_cache

logger = logging.getLogger(__name__)

# Module-level singleton
_registry: "ModelRegistry | None" = None


def get_registry() -> "ModelRegistry":
    """Get or create the global model registry singleton."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry


def reload_registry() -> "ModelRegistry":
    """Force reload of the registry."""
    global _registry
    _registry = ModelRegistry()
    return _registry


class ModelRegistry:
    """Runtime registry for model metadata.

    Loads from models.json (synced from models.dev).
    Auto-syncs if cache is missing or stale.
    """

    def __init__(self, auto_sync: bool = True):
        self._models: dict[str, Model] = {}
        self._auto_sync = auto_sync
        self._load()

    def _load(self) -> None:
        """Load models from disk, auto-sync if needed."""
        if self._auto_sync:
            raw = ensure_models_cache()
        else:
            raw = load_models_cache()
            if raw is None:
                logger.warning("models.json not found - run 'pipy sync'")
                return

        self._parse_models(raw)

    def _parse_models(self, raw: dict[str, Any]) -> None:
        """Parse raw API data into Model objects."""
        for provider_id, provider_data in raw.items():
            models = provider_data.get("models", {})
            for model_id, model_data in models.items():
                model = Model.from_dict(provider_id, model_id, model_data)
                key = f"{provider_id}/{model_id}"
                self._models[key] = model

        logger.debug(f"Loaded {len(self._models)} models")

    def get(self, name: str) -> Model | None:
        """Get a model by qualified name (provider/model_id).

        Args:
            name: Model name like "anthropic/claude-sonnet-4-5"
                  or short form "claude-sonnet-4-5" (searches across providers)

        Returns:
            Model or None if not found.
        """
        # Try exact match first
        if name in self._models:
            return self._models[name]

        # Try short name match (without provider prefix)
        for key, model in self._models.items():
            if model.id == name or key.endswith(f"/{name}"):
                return model

        return None

    def list_all(self) -> list[Model]:
        """List all models."""
        return list(self._models.values())

    def list_by_provider(self, provider: str) -> list[Model]:
        """List models from a specific provider."""
        return [m for m in self._models.values() if m.provider == provider]

    def list_by_capability(self, capability: str) -> list[Model]:
        """List models with a specific capability.

        Args:
            capability: One of "reasoning", "tool_call", "structured_output", "attachment"
        """
        return [m for m in self._models.values() if getattr(m.capabilities, capability, False)]

    def list_with_modality(self, modality: str, direction: str = "input") -> list[Model]:
        """List models supporting a specific modality.

        Args:
            modality: e.g., "image", "audio", "video", "pdf"
            direction: "input" or "output"
        """
        result = []
        for model in self._models.values():
            modalities_list = (
                model.modalities.input if direction == "input" else model.modalities.output
            )
            if modality in modalities_list:
                result.append(model)
        return result

    @property
    def providers(self) -> list[str]:
        """Get all unique provider names."""
        return list(set(m.provider for m in self._models.values()))
