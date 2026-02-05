"""PKCE (Proof Key for Code Exchange) utilities.

Port of pi-ai/src/utils/oauth/pkce.ts.
"""

import base64
import hashlib
import os


def _base64url_encode(data: bytes) -> str:
    """Encode bytes as base64url string (no padding)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_pkce() -> tuple[str, str]:
    """Generate PKCE code verifier and challenge.

    Returns:
        (verifier, challenge) tuple.
    """
    # Generate random verifier
    verifier_bytes = os.urandom(32)
    verifier = _base64url_encode(verifier_bytes)

    # Compute SHA-256 challenge
    challenge_hash = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = _base64url_encode(challenge_hash)

    return verifier, challenge
