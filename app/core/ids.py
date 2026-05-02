from uuid import uuid4

from ulid import ULID


def generate_id(prefix: str) -> str:
    """Generate a short prefixed id, e.g. ``loc-3f2a1b9c``."""
    return f"{prefix}-{uuid4().hex[:8]}"


def generate_ulid() -> str:
    """Generate a ULID string, e.g. ``01HV2XABCDEF...``."""
    return str(ULID())
