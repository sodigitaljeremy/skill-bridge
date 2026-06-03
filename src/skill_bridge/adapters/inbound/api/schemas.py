"""Schémas de réponse Pydantic (OpenAPI auto)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HealthOut(BaseModel):
    status: str
    preloaded: bool
    n_learners: int
    n_resources: int
    n_skills: int
    n_clusters: int


class LearnerOut(BaseModel):
    """Apprenant exposé publiquement — pas d'``ability``, pas d'``archetype``.

    Le champ ``archetype`` est de la **vérité-terrain de simulation**, pas un fait
    observable : on ne le sert jamais via l'API.
    """

    model_config = ConfigDict(frozen=True)

    learner_id: UUID
    display_name: str
    grade_level: int = Field(ge=1, le=5)


class ProfileOut(BaseModel):
    """Profil de maîtrise observé — dérivé des traces, jamais de la vérité latente."""

    model_config = ConfigDict(frozen=True)

    learner_id: UUID
    grade_level: int = Field(ge=1, le=5)
    n_traces: int = Field(ge=0)
    mean_score_per_domain: dict[str, float]
    success_rate_per_domain: dict[str, float]


class ClusterOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    cluster_id: int = Field(ge=0)
    label: str
    size: int = Field(ge=0)
    centroid_per_domain: dict[str, float]


class ClusteringOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    k: int = Field(ge=2)
    silhouette: float
    silhouette_by_k: dict[int, float]
    clusters: list[ClusterOut]


class AssignedClusterOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    learner_id: UUID
    cluster_id: int
    cluster_label: str
    distance_to_centroid: float


class RecommendationOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    resource_id: str
    title: str
    score: float = Field(ge=0.0, le=1.0)
    weak_skills_targeted: list[str]
    grade_distance: int = Field(ge=0)
    semantic_similarity: float
    cluster_success_rate: float | None = None
    explanation: str
