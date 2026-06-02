"""Ports outbound — interfaces que les adapters implémentent.

Justification de chaque port (règle interne : pas de port sans 2ᵉ impl prévisible) :

- ``SkillRepository`` / ``LearningResourceRepository`` : substituables au Lot 4 par un
  catalogue dataspace (PDC).
- ``TraceEncoder`` : 2 impls — ``XApiJsonLinesEncoder`` (chemin xapi-direct) et
  ``CsvTraceEncoder`` (chemin via-LRC, alimente ``/convert_custom``).
- ``EmbeddingProvider`` : 2ᵉ impl déjà en place (``StubEmbeddingProvider`` côté tests, sans
  download de modèle) ; 3ᵉ impl plausible plus tard via une API distante.
- ``TraceConverter`` (Lot 3) : 2 impls — ``LrcHttpConverter`` (HTTP multipart vers le
  service LRC réel) et ``StubLrcConverter`` (tests unitaires, sans réseau).
"""

from collections.abc import Iterable, Sequence
from pathlib import Path
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


@runtime_checkable
class TraceConverter(Protocol):
    """Convertit un fichier de traces brutes (+ mapping) en statements xAPI normalisés.

    Le contrat correspond à l'endpoint ``/convert_custom`` du LRC : on lui fournit un
    fichier de données et un fichier YAML de mapping ; il retourne un flux de
    statements (1 dict par trace).
    """

    def convert(self, data_path: Path, mapping_path: Path) -> Iterable[dict[str, Any]]: ...
