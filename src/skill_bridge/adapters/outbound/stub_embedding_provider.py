"""``EmbeddingProvider`` déterministe et auto-suffisant pour les tests.

Pas de download, pas de modèle. Texte → vecteur via hashing déterministe (md5 sur n-grams
courts). Suffisant pour tester la structure des recos (les tests s'appuient sur le signal
``skill_overlap`` à 0.50, pas sur la qualité sémantique réelle).
"""

import hashlib
from collections.abc import Sequence

import numpy as np


class StubEmbeddingProvider:
    def __init__(self, dimension: int = 32) -> None:
        if dimension < 8:
            raise ValueError("dimension must be >= 8")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        out = np.zeros((len(texts), self._dimension), dtype=float)
        for i, text in enumerate(texts):
            # MD5 (16 octets) répété jusqu'à atteindre la dim, puis normalisé en [-1, 1].
            digest = hashlib.md5(text.encode("utf-8")).digest()
            extended = (digest * ((self._dimension // len(digest)) + 1))[: self._dimension]
            out[i] = np.frombuffer(extended, dtype=np.uint8).astype(float)
            out[i] = (out[i] / 127.5) - 1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return out / norms
