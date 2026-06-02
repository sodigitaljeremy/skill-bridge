"""Ports outbound — interfaces que les adapters implémentent.

Justification de chaque port (règle interne : pas de port sans 2ᵉ impl prévisible) :

- ``SkillRepository`` / ``LearningResourceRepository`` : substituables au Lot 4 par un
  catalogue dataspace (PDC).
- ``TraceEncoder`` : seconde implémentation prévue (CSV brut / Matomo) pour démontrer le LRC
  au Lot 3.
- ``EmbeddingProvider`` : 2ᵉ impl déjà en place (``StubEmbeddingProvider`` côté tests, sans
  download de modèle) ; 3ᵉ impl plausible plus tard via une API distante.
"""

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

import numpy as np

from skill_bridge.domain.entities import LearningResource, LearningTrace, Skill


@runtime_checkable
class SkillRepository(Protocol):
    def load_all(self) -> list[Skill]: ...


@runtime_checkable
class LearningResourceRepository(Protocol):
    def load_all(self) -> list[LearningResource]: ...


@runtime_checkable
class TraceEncoder(Protocol):
    @property
    def format_name(self) -> str: ...

    def encode(self, trace: LearningTrace) -> dict[str, Any]: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Encode du texte en vecteur dense L2-normalisé."""

    @property
    def dimension(self) -> int: ...

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        """Retourne un tableau de forme ``(len(texts), dimension)`` (rows L2-normalisés)."""
        ...
