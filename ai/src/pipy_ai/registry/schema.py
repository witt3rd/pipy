"""Model registry data types from models.dev."""

from typing import Any

from pydantic import BaseModel, Field


class ModelCost(BaseModel):
    """Token pricing (per 1M tokens)."""

    input: float = 0.0
    output: float = 0.0
    cache_read: float = 0.0
    cache_write: float = 0.0
    reasoning: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelCost":
        return cls(
            input=data.get("input", 0.0),
            output=data.get("output", 0.0),
            cache_read=data.get("cache_read", 0.0),
            cache_write=data.get("cache_write", 0.0),
            reasoning=data.get("reasoning", 0.0),
        )


class ModelLimits(BaseModel):
    """Token limits."""

    context: int = 0
    output: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelLimits":
        return cls(
            context=data.get("context", 0),
            output=data.get("output", 0),
        )


class ModelCapabilities(BaseModel):
    """What the model can do."""

    reasoning: bool = False
    tool_call: bool = False
    structured_output: bool = False
    attachment: bool = False
    temperature: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelCapabilities":
        return cls(
            reasoning=data.get("reasoning", False),
            tool_call=data.get("tool_call", False),
            structured_output=data.get("structured_output", False),
            attachment=data.get("attachment", False),
            temperature=data.get("temperature", True),
        )


class ModelModalities(BaseModel):
    """Supported input/output types."""

    input: list[str] = Field(default_factory=lambda: ["text"])
    output: list[str] = Field(default_factory=lambda: ["text"])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelModalities":
        return cls(
            input=data.get("input", ["text"]),
            output=data.get("output", ["text"]),
        )

    def accepts(self, modality: str) -> bool:
        """Check if model accepts this input modality."""
        return modality in self.input

    def produces(self, modality: str) -> bool:
        """Check if model produces this output modality."""
        return modality in self.output


class Model(BaseModel):
    """A single model with all metadata."""

    id: str
    provider: str
    name: str
    family: str = ""

    cost: ModelCost = Field(default_factory=ModelCost)
    limits: ModelLimits = Field(default_factory=ModelLimits)
    capabilities: ModelCapabilities = Field(default_factory=ModelCapabilities)
    modalities: ModelModalities = Field(default_factory=ModelModalities)

    knowledge_cutoff: str = ""
    release_date: str = ""
    last_updated: str = ""
    open_weights: bool = False
    status: str = ""

    @property
    def qualified_name(self) -> str:
        """Full provider/model name for LiteLLM."""
        return f"{self.provider}/{self.id}"

    @classmethod
    def from_dict(cls, provider: str, model_id: str, data: dict[str, Any]) -> "Model":
        """Create Model from models.dev API format."""
        return cls(
            id=model_id,
            provider=provider,
            name=data.get("name", model_id),
            family=data.get("family", ""),
            cost=ModelCost.from_dict(data.get("cost", {})),
            limits=ModelLimits.from_dict(data.get("limit", {})),
            capabilities=ModelCapabilities.from_dict(data),
            modalities=ModelModalities.from_dict(data.get("modalities", {})),
            knowledge_cutoff=data.get("knowledge", ""),
            release_date=data.get("release_date", ""),
            last_updated=data.get("last_updated", ""),
            open_weights=data.get("open_weights", False),
            status=data.get("status", ""),
        )
