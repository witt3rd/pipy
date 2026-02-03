#!/bin/bash
# Run tests for all packages

set -e

echo "=== Testing pipy-ai ==="
uv run --directory ai pytest tests -v --tb=short

echo ""
echo "=== Testing pipy-agent ==="
uv run --directory agent pytest tests -v --tb=short

echo ""
echo "=== Testing pipy-tui ==="
uv run --directory tui pytest tests -v --tb=short

echo ""
echo "=== Testing pipy-coding-agent ==="
uv run --directory coding-agent pytest tests -v --tb=short

echo ""
echo "=== All tests passed! ==="
