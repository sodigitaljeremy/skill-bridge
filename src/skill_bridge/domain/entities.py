"""Entités et value objects du domaine.

`LearningTrace` est modelé sur la forme d'un *statement xAPI* (profils DASES LMS / Assessment).
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from skill_bridge.domain.enums import ResourceType


class Skill(BaseModel):
    """Compétence du référentiel maison, optionnellement mappée vers ESCO."""

    model_config = ConfigDict(frozen=True)

    id: str
    preferred_label: str
    description: str
    domain: str
    esco_uris: list[str] = Field(default_factory=list)


class LearningResource(BaseModel):
    """Ressource éducative taguée avec au moins une compétence."""

    model_config = ConfigDict(frozen=True)

    resource_id: str
    title: str
    type: ResourceType
    grade_level: int = Field(ge=1, le=5)
    estimated_duration_s: int = Field(gt=0)
    skill_ids: list[str] = Field(min_length=1)


class Learner(BaseModel):
    """Apprenant : vecteur d'ability par domaine + archetype latent (label de profil)."""

    model_config = ConfigDict(frozen=True)

    learner_id: UUID
    display_name: str
    mbox_sha1sum: str
    grade_level: int = Field(ge=1, le=5)
    ability: dict[str, float]
    archetype: str | None = None

    @field_validator("ability")
    @classmethod
    def _ability_in_range(cls, v: dict[str, float]) -> dict[str, float]:
        for domain, value in v.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"Ability for domain {domain!r} must be in [0, 1], got {value}")
        return v


# --- xAPI Statement structure (LearningTrace) ---


class Actor(BaseModel):
    model_config = ConfigDict(frozen=True)

    # camelCase imposé par la spec xAPI (§4.1.2)
    objectType: str = "Agent"  # noqa: N815
    mbox_sha1sum: str
    name: str | None = None


class Verb(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    display: dict[str, str]


class ActivityDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: dict[str, str]
    type: str


class Activity(BaseModel):
    model_config = ConfigDict(frozen=True)

    # camelCase imposé par la spec xAPI (§4.1.4)
    objectType: str = "Activity"  # noqa: N815
    id: str
    definition: ActivityDefinition


class Score(BaseModel):
    model_config = ConfigDict(frozen=True)

    scaled: float = Field(ge=0.0, le=1.0)


class Result(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool | None = None
    completion: bool | None = None
    score: Score | None = None
    duration: str | None = None  # ISO 8601 duration (ex: "PT180S")


class Context(BaseModel):
    model_config = ConfigDict(frozen=True)

    registration: UUID | None = None
    extensions: dict[str, Any] = Field(default_factory=dict)


class LearningTrace(BaseModel):
    """Statement xAPI — un événement d'apprentissage observable."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    actor: Actor
    verb: Verb
    object: Activity
    result: Result | None = None
    timestamp: datetime
    context: Context | None = None
    version: str = "1.0.3"


# --- Lot 2 : profilage, clustering, recommandation ---


class LearnerProfile(BaseModel):
    """Profil de maîtrise *observé* d'un apprenant (dérivé des traces uniquement).

    Ne lit jamais ``Learner.ability`` (vérité latente). Utilisé comme features de
    clustering et input du moteur de recommandation.
    """

    model_config = ConfigDict(frozen=True)

    learner_id: UUID
    mbox_sha1sum: str
    grade_level: int = Field(ge=1, le=5)
    mean_score_per_domain: dict[str, float]
    success_rate_per_domain: dict[str, float]
    mean_score_per_skill: dict[str, float]
    attempted_resource_ids: list[str]
    n_traces: int = Field(ge=0)


class ClusterAssignment(BaseModel):
    """Affectation d'un apprenant à un cluster, avec distance au centroïde."""

    model_config = ConfigDict(frozen=True)

    learner_id: UUID
    cluster_id: int
    cluster_label: str
    distance_to_centroid: float


class Recommendation(BaseModel):
    """Recommandation explicable : score décomposé + phrase humaine."""

    model_config = ConfigDict(frozen=True)

    resource_id: str
    title: str
    score: float = Field(ge=0.0, le=1.0)
    weak_skills_targeted: list[str]
    grade_distance: int = Field(ge=0)
    semantic_similarity: float = Field(ge=-1.0, le=1.0)
    cluster_success_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    explanation: str
