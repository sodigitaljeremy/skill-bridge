"""Clustering KMeans avec sélection empirique de k par silhouette.

Features uniquement numériques (``mean_score_per_domain`` + ``success_rate_per_domain``),
standardisées. Aucune dépendance aux embeddings.

Le nom de chaque cluster est dérivé du centroïde inverse-scalé, en français lisible.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from skill_bridge.domain.entities import ClusterAssignment, LearnerProfile

STRONG_THRESHOLD: Final[float] = 0.70
WEAK_THRESHOLD: Final[float] = 0.55


@dataclass(frozen=True)
class ClusteringResult:
    k: int
    silhouette: float
    silhouette_by_k: dict[int, float]
    assignments: list[ClusterAssignment]
    centroids_per_domain: dict[int, dict[str, float]]  # cluster_id -> domain -> mean_score
    cluster_labels: dict[int, str]
    cluster_sizes: dict[int, int]


class ClusteringService:
    def __init__(
        self,
        domains: Sequence[str],
        k_min: int = 2,
        k_max: int = 8,
        seed: int = 42,
    ) -> None:
        if k_min < 2:
            raise ValueError("k_min must be >= 2")
        if k_max <= k_min:
            raise ValueError("k_max must be > k_min")
        self._domains = list(domains)
        self._k_min = k_min
        self._k_max = k_max
        self._seed = seed

    def fit(self, profiles: list[LearnerProfile]) -> ClusteringResult:
        if len(profiles) < self._k_max + 1:
            raise ValueError(
                f"Need at least {self._k_max + 1} profiles for k_max={self._k_max}, "
                f"got {len(profiles)}"
            )

        features = self._build_feature_matrix(profiles)
        scaler = StandardScaler()
        scaled = scaler.fit_transform(features)

        silhouette_by_k: dict[int, float] = {}
        best_k = self._k_min
        best_score = -1.0
        best_model: KMeans | None = None

        for k in range(self._k_min, self._k_max + 1):
            model = KMeans(n_clusters=k, n_init=10, random_state=self._seed).fit(scaled)
            score = float(silhouette_score(scaled, model.labels_))
            silhouette_by_k[k] = score
            if score > best_score:
                best_score = score
                best_k = k
                best_model = model

        assert best_model is not None  # garanti par la boucle
        labels = best_model.labels_
        # Distance L2 standardisée au centroïde assigné, pour chaque apprenant.
        distances = np.linalg.norm(scaled - best_model.cluster_centers_[labels], axis=1)

        # Centroïdes en espace original (mean_score uniquement) → nom lisible.
        centers_original = scaler.inverse_transform(best_model.cluster_centers_)
        n_domains = len(self._domains)
        centroids_per_domain: dict[int, dict[str, float]] = {}
        cluster_labels: dict[int, str] = {}
        for cluster_id in range(best_k):
            mean_scores = centers_original[cluster_id, :n_domains]
            domain_to_score = dict(zip(self._domains, mean_scores.tolist(), strict=True))
            centroids_per_domain[cluster_id] = domain_to_score
            cluster_labels[cluster_id] = self._label_from_centroid(domain_to_score)

        assignments = [
            ClusterAssignment(
                learner_id=profile.learner_id,
                cluster_id=int(cluster_id),
                cluster_label=cluster_labels[int(cluster_id)],
                distance_to_centroid=float(distance),
            )
            for profile, cluster_id, distance in zip(profiles, labels, distances, strict=True)
        ]

        cluster_sizes = {cid: int((labels == cid).sum()) for cid in range(best_k)}

        return ClusteringResult(
            k=best_k,
            silhouette=best_score,
            silhouette_by_k=silhouette_by_k,
            assignments=assignments,
            centroids_per_domain=centroids_per_domain,
            cluster_labels=cluster_labels,
            cluster_sizes=cluster_sizes,
        )

    def _build_feature_matrix(self, profiles: list[LearnerProfile]) -> np.ndarray:
        rows = []
        for profile in profiles:
            row = [profile.mean_score_per_domain[d] for d in self._domains]
            row.extend(profile.success_rate_per_domain[d] for d in self._domains)
            rows.append(row)
        return np.array(rows, dtype=float)

    @staticmethod
    def _label_from_centroid(domain_to_score: dict[str, float]) -> str:
        strong = sorted(
            (d for d, s in domain_to_score.items() if s >= STRONG_THRESHOLD),
            key=lambda d: -domain_to_score[d],
        )
        weak = sorted(
            (d for d, s in domain_to_score.items() if s <= WEAK_THRESHOLD),
            key=lambda d: domain_to_score[d],
        )
        if not strong and not weak:
            return "équilibré moyen"
        if not weak and len(strong) >= 4:
            return "équilibré fort"
        if not strong and len(weak) >= 4:
            return "en difficulté générale"
        parts: list[str] = []
        if strong:
            parts.append("fort en " + ", ".join(strong[:2]))
        if weak:
            parts.append("faible en " + ", ".join(weak[:2]))
        return " / ".join(parts)
