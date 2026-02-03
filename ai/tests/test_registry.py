"""Tests for registry module."""

import pytest

from pipy_ai import Usage
from pipy_ai.registry import calculate_cost
from pipy_ai.registry.schema import (
    Model,
    ModelCapabilities,
    ModelCost,
    ModelLimits,
    ModelModalities,
)


class TestModelCost:
    def test_defaults(self):
        cost = ModelCost()
        assert cost.input == 0.0
        assert cost.output == 0.0
        assert cost.cache_read == 0.0
        assert cost.cache_write == 0.0
        assert cost.reasoning == 0.0

    def test_from_dict(self):
        data = {
            "input": 3.0,
            "output": 15.0,
            "cache_read": 0.3,
        }
        cost = ModelCost.from_dict(data)
        assert cost.input == 3.0
        assert cost.output == 15.0
        assert cost.cache_read == 0.3
        assert cost.cache_write == 0.0  # default


class TestModelLimits:
    def test_defaults(self):
        limits = ModelLimits()
        assert limits.context == 0
        assert limits.output == 0

    def test_from_dict(self):
        data = {"context": 200000, "output": 8192}
        limits = ModelLimits.from_dict(data)
        assert limits.context == 200000
        assert limits.output == 8192


class TestModelCapabilities:
    def test_defaults(self):
        caps = ModelCapabilities()
        assert caps.reasoning is False
        assert caps.tool_call is False
        assert caps.structured_output is False
        assert caps.temperature is True

    def test_from_dict(self):
        data = {
            "reasoning": True,
            "tool_call": True,
            "structured_output": True,
        }
        caps = ModelCapabilities.from_dict(data)
        assert caps.reasoning is True
        assert caps.tool_call is True
        assert caps.structured_output is True


class TestModelModalities:
    def test_defaults(self):
        mods = ModelModalities()
        assert mods.input == ["text"]
        assert mods.output == ["text"]

    def test_from_dict(self):
        data = {
            "input": ["text", "image"],
            "output": ["text"],
        }
        mods = ModelModalities.from_dict(data)
        assert "image" in mods.input
        assert mods.accepts("image") is True
        assert mods.accepts("video") is False
        assert mods.produces("text") is True


class TestModel:
    def test_from_dict(self):
        data = {
            "name": "Claude Sonnet 4.5",
            "family": "claude",
            "cost": {"input": 3.0, "output": 15.0},
            "limit": {"context": 200000, "output": 8192},
            "reasoning": True,
            "tool_call": True,
            "modalities": {"input": ["text", "image"], "output": ["text"]},
            "knowledge": "2025-04",
            "release_date": "2025-01-15",
        }
        model = Model.from_dict("anthropic", "claude-sonnet-4-5", data)

        assert model.id == "claude-sonnet-4-5"
        assert model.provider == "anthropic"
        assert model.name == "Claude Sonnet 4.5"
        assert model.qualified_name == "anthropic/claude-sonnet-4-5"
        assert model.cost.input == 3.0
        assert model.limits.context == 200000
        assert model.capabilities.reasoning is True
        assert "image" in model.modalities.input
        assert model.knowledge_cutoff == "2025-04"


class TestCalculateCost:
    def test_calculate_cost(self):
        model = Model(
            id="test-model",
            provider="test",
            name="Test Model",
            cost=ModelCost(input=3.0, output=15.0, cache_read=0.3),
        )
        usage = Usage(
            input=1000000,  # 1M tokens
            output=100000,  # 100K tokens
            cache_read=500000,  # 500K tokens
        )
        cost = calculate_cost(model, usage)

        assert cost.input == 3.0  # 1M * 3.0 / 1M
        assert cost.output == 1.5  # 100K * 15.0 / 1M
        assert cost.cache_read == 0.15  # 500K * 0.3 / 1M
        assert cost.total == pytest.approx(4.65)
