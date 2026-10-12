"""
VectorHire Embedding Provider Abstraction and FastEmbed Engine.
Provides in-process CPU embedding generation using BAAI/bge-small-en-v1.5
with a deterministic mock provider for unit testing.
"""

from abc import ABC, abstractmethod
import hashlib
import math
from typing import List, Optional

from app.core.exceptions import ProviderAPIError


class BaseEmbeddingProvider(ABC):
    """Abstract base class defining the contract for embedding providers."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generates a dense vector embedding for a single text string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates dense vector embeddings for a list of text strings."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Returns the dimensionality of the generated vectors."""
        pass


class FastEmbedProvider(BaseEmbeddingProvider):
    """
    Local in-process embedding provider using FastEmbed and BAAI/bge-small-en-v1.5.
    
    Operational Characteristics:
    - Runs entirely on CPU via ONNX Runtime without PyTorch.
    - Model weights (~67 MB) are cached locally in ~/.cache/fastembed on first initialization.
    - Zero candidate data leaves the local process.
    - Employs a process-level singleton instance to prevent re-initializing the model per candidate.
    """
    _instance: Optional["FastEmbedProvider"] = None
    _model = None

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self._model_name = model_name
        self._dimension = 384
        self._init_model()

    def _init_model(self) -> None:
        """Initializes the FastEmbed TextEmbedding engine if not already loaded."""
        if FastEmbedProvider._model is None:
            try:
                from fastembed import TextEmbedding
                FastEmbedProvider._model = TextEmbedding(
                    model_name=self._model_name,
                    threads=None,  # Use all available CPU cores
                )
            except Exception as e:
                raise ProviderAPIError(
                    f"Failed to initialize local FastEmbed model '{self._model_name}': {str(e)}"
                ) from e

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> List[float]:
        """Embeds a single string into a 384-dimensional normalized vector."""
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty or whitespace-only text.")
        vectors = self.embed_batch([text])
        return vectors[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a batch of strings into unit-normalized vectors.
        Validates output dimensionality and finite float values.
        """
        if not texts:
            return []

        for idx, t in enumerate(texts):
            if not t or not t.strip():
                raise ValueError(f"Batch item at index {idx} is empty or whitespace-only.")

        try:
            # fastembed.embed returns a generator of numpy arrays
            raw_embeddings = list(FastEmbedProvider._model.embed(texts))
        except Exception as e:
            raise ProviderAPIError(f"FastEmbed inference failure: {str(e)}") from e

        results: List[List[float]] = []
        for vec in raw_embeddings:
            vec_list = [float(x) for x in vec]
            
            # Dimension check
            if len(vec_list) != self._dimension:
                raise ProviderAPIError(
                    f"Vector dimension mismatch: expected {self._dimension}, got {len(vec_list)}"
                )

            # Finite float check (detect NaNs or Infs)
            if not all(math.isfinite(x) for x in vec_list):
                raise ProviderAPIError("Embedding contains non-finite values (NaN or Inf).")

            results.append(vec_list)

        return results


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic, unit-normalized mock embedding provider for fast, offline unit testing.
    Generates reproducible 384-dimensional vectors via cryptographic hashing of input text.
    Requires zero network access, zero disk caching, and zero ONNX runtime overhead.
    """
    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _hash_to_vector(self, text: str) -> List[float]:
        """Produces a deterministic pseudo-random unit vector based on input text."""
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty or whitespace-only text.")

        raw_vec: List[float] = []
        # Generate dimension values using successive sha256 chunks
        seed = text.encode("utf-8")
        chunk_idx = 0
        while len(raw_vec) < self._dimension:
            h = hashlib.sha256(seed + str(chunk_idx).encode("utf-8")).digest()
            for b in h:
                if len(raw_vec) < self._dimension:
                    # Map byte to range [-1.0, 1.0]
                    raw_vec.append((b - 128.0) / 128.0)
            chunk_idx += 1

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in raw_vec))
        if norm > 0.0:
            return [x / norm for x in raw_vec]
        return raw_vec

    def embed_text(self, text: str) -> List[float]:
        return self._hash_to_vector(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return [self._hash_to_vector(t) for t in texts]


def get_embedding_provider(provider_type: Optional[str] = None) -> BaseEmbeddingProvider:
    """
    Factory function returning the configured embedding provider.
    - 'fastembed': Local ONNX FastEmbedProvider (production default).
    - 'mock': Deterministic MockEmbeddingProvider (for unit testing).
    """
    from app.core.config import get_settings
    settings = get_settings()

    target = (provider_type or "fastembed").lower()
    if target == "mock":
        return MockEmbeddingProvider(dimension=384)
    elif target == "fastembed":
        return FastEmbedProvider(model_name=settings.EMBEDDING_MODEL)
    else:
        raise ValueError(f"Unsupported embedding provider type: '{target}'")
