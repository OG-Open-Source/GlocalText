import re2 as re
import xxhash


def normalize_and_hash(text: str, seed: int) -> str:
    """
    Normalizes a string by replacing f-string-like placeholders with a generic '{}'
    and then computes its xxhash using a specific seed.

    This ensures that strings with different variable names but the same structure
    are treated as identical.

    Args:
        text: The input string.
        seed: The seed for the hash algorithm.

    Returns:
        The hex digest of the xxhash of the normalized string.
    """
    # Normalize f-string content for consistent hashing
    normalized_text = re.sub(r"\{.*?\}", "{}", text)
    return xxhash.xxh64(normalized_text.encode("utf-8"), seed=seed).hexdigest()
