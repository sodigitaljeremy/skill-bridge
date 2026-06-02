"""Implémentation ``EmbeddingProvider`` adossée à sentence-transformers.

Modèle par défaut : ``paraphrase-multilingual-MiniLM-L12-v2`` (multilingue, 384-dim,
~470 MB téléchargés au premier appel, ensuite cachés par sentence-transformers).
"""

from collections.abc import Sequence
from pathlib import Path

import numpy as np

DEFAULT_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class SentenceTransformersEmbeddingProvider:
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        cache_folder: Path | None = None,
        device: str = "cpu",
    ) -> None:
        # Import paresseux : ne déclenche le chargement de torch que si on instancie le provider.
        from sentence_transformers import SentenceTransformer

        cache_str = str(cache_folder) if cache_folder is not None else None
        self._model = SentenceTransformer(model_name, cache_folder=cache_str, device=device)
        # Compat ST v5 (get_embedding_dimension) ↔ v4 (get_sentence_embedding_dimension).
        get_dim = getattr(
            self._model, "get_embedding_dimension", None
        ) or self._model.get_sentence_embedding_dimension
        self._dimension = int(get_dim())

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        vectors = self._model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=float)
