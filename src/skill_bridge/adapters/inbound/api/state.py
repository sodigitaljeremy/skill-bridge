"""Etat préchargé de l'API — exposé via ``app.state.preloaded``.

Idée : on calcule TOUT au boot (profilage, clustering, embeddings, top-10 reco par
apprenant) et chaque requête HTTP n'est plus qu'un lookup en mémoire. Garantit la
cohérence des clusters affichés et évite le coût ST par requête.
"""

from dataclasses import dataclass
from uuid import UUID

from skill_bridge.application.clustering import ClusteringResult
from skill_bridge.application.enrichment import EnrichedTrace
from skill_bridge.domain.entities import (
    Learner,
    LearnerProfile,
    LearningResource,
    Recommendation,
    Skill,
)


@dataclass(frozen=True)
class PreloadedState:
    skills: list[Skill]
    resources: list[LearningResource]
    learners: list[Learner]
    enriched_traces: list[EnrichedTrace]
    profiles: list[LearnerProfile]
    clustering: ClusteringResult
    recommendations_by_learner: dict[UUID, list[Recommendation]]

    @property
    def domains(self) -> list[str]:
        return sorted({s.domain for s in self.skills})
