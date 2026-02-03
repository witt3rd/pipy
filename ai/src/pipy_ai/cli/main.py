"""pipy CLI - Model registry and config management."""

import argparse
import sys

from ..registry import (
    estimate_cost,
    get_model,
    get_models,
    sync_models,
)


def cmd_sync(args):
    """Sync models from models.dev."""
    data = sync_models()
    total = sum(len(p.get("models", {})) for p in data.values())
    print(f"Synced {total} models from {len(data)} providers")


def cmd_models(args):
    """List models with filters."""
    models = get_models(
        provider=args.provider,
        capability=args.capability,
        modality=args.modality,
        min_context=args.min_context,
    )
    for m in sorted(models, key=lambda x: x.qualified_name):
        print(m.qualified_name)
    print(f"\n{len(models)} models found")


def cmd_info(args):
    """Show model details."""
    model = get_model(args.model)
    if not model:
        print(f"Model not found: {args.model}", file=sys.stderr)
        sys.exit(1)

    print(f"Name: {model.name}")
    print(f"ID: {model.id}")
    print(f"Provider: {model.provider}")
    print(f"Family: {model.family}")
    print(f"Context: {model.limits.context:,} tokens")
    print(f"Max Output: {model.limits.output:,} tokens")
    print(f"Cost: ${model.cost.input:.2f}/1M input, ${model.cost.output:.2f}/1M output")

    caps = []
    if model.capabilities.reasoning:
        caps.append("reasoning")
    if model.capabilities.tool_call:
        caps.append("tool_call")
    if model.capabilities.structured_output:
        caps.append("structured_output")
    if model.capabilities.attachment:
        caps.append("attachment")
    print(f"Capabilities: {', '.join(caps) or 'none'}")

    print(f"Input modalities: {', '.join(model.modalities.input)}")
    print(f"Output modalities: {', '.join(model.modalities.output)}")

    if model.knowledge_cutoff:
        print(f"Knowledge Cutoff: {model.knowledge_cutoff}")
    if model.release_date:
        print(f"Released: {model.release_date}")
    if model.status:
        print(f"Status: {model.status}")


def cmd_cost(args):
    """Estimate cost for a request."""
    try:
        cost = estimate_cost(args.model, args.input, args.output, args.cached or 0)
        print(f"Estimated cost: ${cost:.4f}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


def cmd_providers(args):
    """List all providers."""
    from ..registry import get_registry

    providers = get_registry().providers
    for p in sorted(providers):
        count = len(get_models(provider=p))
        print(f"{p}: {count} models")


def main():
    parser = argparse.ArgumentParser(
        prog="pipy",
        description="pipy-ai: LLM model registry CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # sync
    p_sync = subparsers.add_parser("sync", help="Sync models from models.dev")
    p_sync.set_defaults(func=cmd_sync)

    # models
    p_models = subparsers.add_parser("models", help="List models")
    p_models.add_argument("--provider", "-p", help="Filter by provider")
    p_models.add_argument("--capability", "-c", help="Filter by capability")
    p_models.add_argument("--modality", "-m", help="Filter by input modality")
    p_models.add_argument("--min-context", type=int, help="Minimum context window")
    p_models.set_defaults(func=cmd_models)

    # info
    p_info = subparsers.add_parser("info", help="Show model details")
    p_info.add_argument("model", help="Model name")
    p_info.set_defaults(func=cmd_info)

    # cost
    p_cost = subparsers.add_parser("cost", help="Estimate request cost")
    p_cost.add_argument("model", help="Model name")
    p_cost.add_argument("--input", "-i", type=int, required=True, help="Input tokens")
    p_cost.add_argument("--output", "-o", type=int, default=0, help="Output tokens")
    p_cost.add_argument("--cached", type=int, help="Cached tokens")
    p_cost.set_defaults(func=cmd_cost)

    # providers
    p_providers = subparsers.add_parser("providers", help="List all providers")
    p_providers.set_defaults(func=cmd_providers)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
