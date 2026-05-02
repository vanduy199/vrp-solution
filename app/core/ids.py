from uuid import uuid4


def generate_id(prefix: str) -> str:
    """Generate a short prefixed id, e.g. ``loc-3f2a1b9c``."""
    return f"{prefix}-{uuid4().hex[:8]}"
