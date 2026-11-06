"""Embedding provider wrapper with a deterministic local demo implementation."""

import hashlib
import math
import os
import re

TOKEN_RE = re.compile(r"[a-z0-9_]+", re.IGNORECASE)


def embed_text(text: str, dimensions: int = 384) -> list[float]:
    """Create normalized feature-hash vectors without network access.

    Replace this with an embedding service before production use. Hash embeddings
    make the ingestion artifact reproducible but are not semantic embeddings.
    """
    vector = [0.0] * dimensions
    tokens = TOKEN_RE.findall(text.lower())
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        number = int.from_bytes(digest, "big")
        index = number % dimensions
        sign = 1.0 if (number >> 8) & 1 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def embed_texts(texts: list[str]) -> list[list[float]]:
    provider = os.getenv("EMBEDDING_PROVIDER", "local").lower()
    if provider == "openai":
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install the 'openai' package to use OpenAI embeddings") from exc
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        response = client.embeddings.create(model=model, input=texts)
        return [item.embedding for item in response.data]
    return [embed_text(text) for text in texts]
