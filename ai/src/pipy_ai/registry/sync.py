"""Sync model metadata from models.dev."""

import json
import logging
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

MODELS_DEV_URL = "https://models.dev/api.json"
DATA_DIR = Path.home() / ".pipy"
MODELS_JSON = DATA_DIR / "models.json"

# Cache age threshold (7 days in seconds)
CACHE_MAX_AGE = 7 * 24 * 60 * 60


def fetch_models_dev() -> dict[str, Any]:
    """Fetch model data from models.dev API.

    Returns:
        Raw API response as dict.

    Raises:
        URLError: If fetch fails.
    """
    logger.info(f"Fetching from {MODELS_DEV_URL}")
    request = Request(
        MODELS_DEV_URL,
        headers={"User-Agent": "pipy-ai/0.1.0"},
    )
    with urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    logger.info(f"Fetched {len(data)} providers")
    return data


def sync_models(output_path: Path | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Sync models from models.dev to local cache.

    Args:
        output_path: Where to save (default: ~/.pipy/models.json)
        dry_run: If True, fetch but don't save.

    Returns:
        The fetched model data.
    """
    data = fetch_models_dev()

    # Count models
    total_models = sum(len(p.get("models", {})) for p in data.values())
    provider_names = list(data.keys())
    logger.info(f"Found {total_models} models across {len(provider_names)} providers")

    if dry_run:
        logger.info("[DRY RUN] Would save to models.json")
        return data

    # Save to models.json
    save_path = output_path or MODELS_JSON
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved to {save_path}")

    return data


def load_models_cache(cache_path: Path | None = None) -> dict[str, Any] | None:
    """Load cached models.json if it exists.

    Returns:
        Cached data or None if not found.
    """
    path = cache_path or MODELS_JSON
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def is_cache_stale(cache_path: Path | None = None) -> bool:
    """Check if cache is older than CACHE_MAX_AGE."""
    import time

    path = cache_path or MODELS_JSON
    if not path.exists():
        return True

    age = time.time() - path.stat().st_mtime
    return age > CACHE_MAX_AGE


def ensure_models_cache() -> dict[str, Any]:
    """Ensure models.json exists and is fresh, auto-sync if needed.

    Returns:
        Model data (from cache or freshly synced).
    """
    if is_cache_stale():
        logger.info("Models cache is stale or missing, syncing from models.dev...")
        return sync_models()

    data = load_models_cache()
    if data is None:
        return sync_models()

    return data
