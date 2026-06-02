"""Recommandation explicable.

Pour chaque apprenant : détecte les domaines/compétences faibles, filtre les ressources
candidates (compétences ciblées + grade adapté + non déjà tentée), classe selon une
combinaison transparente de signaux, puis émet une phrase d'explication.

Score paramétrable (défauts conformes au plan validé) :
    0.50 · skill_overlap + 0.20 · grade_fit + 0.20 · semantic_similarity + 0.10 · cluster_signal
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Final
from uuid import UUID

import numpy as np

from skill_bridge.application.enrichment import EnrichedTrace
from skill_bridge.domain.entities import (
    ClusterAssignment,
    LearnerProfile,
    LearningResource,
    Recommendation,
    Skill,
)
from skill_bridge.domain.ports import EmbeddingProvider

WEAKNESS_DOMAIN_THRESHOLD: Final[float] = 0.60
DEFAULT_TOP_N: Final[int] = 5


@dataclass(frozen=True)
class ScoreWeights:
    skill_overlap: float = 0.50
    grade_fit: float = 0.20
    semantic_similarity: float = 0.20
    cluster_signal: float = 0.10

    def __post_init__(self) -> None:
        total = self.skill_overlap + self.grade_fit + self.semantic_similarity + self.cluster_signal
        if not np.isclose(total, 1.0, atol=1e-6):
            raise ValueError(f"ScoreWeights must sum to 1.0, got {total}")


class RecommendationService:
    """Moteur de reco. Encode une fois les ressources, sert N apprenants en lookup."""

    def __init__(
        self,
        resources: list[LearningResource],
        skills: list[Skill],
        embedder: EmbeddingProvider,
        weights: ScoreWeights | None = None,
    ) -> None:
        self._resources = resources
        self._resource_by_id = {r.resource_id: r for r in resources}
        self._skills = skills
        self._skill_by_id = {s.id: s for s in skills}
        self._embedder = embedder
        self._weights = weights or ScoreWeights()
        # Cache d'embeddings pour chaque ressource (concaténation titre + skills).
        self._resource_embeddings = self._embedder.embed(
            [self._resource_text(r) for r in resources]
        )
        self._resource_index = {r.resource_id: i for i, r in enumerate(resources)}

    # ----- public -----

    def recommend_for_profile(
        self,
        profile: LearnerProfile,
        all_traces: list[EnrichedTrace],
        cluster_peers: list[LearnerProfile] | None = None,
        top_n: int = DEFAULT_TOP_N,
    ) -> list[Recommendation]:
        weak_skill_ids = self._weak_skill_ids(profile)
        if not weak_skill_ids:
            return []  # apprenant sans faiblesse marquée, pas de reco prioritaire

        peer_success = (
            self._peer_success_rate_by_resource(cluster_peers, all_traces) if cluster_peers else {}
        )

        weakness_query = self._build_weakness_query(weak_skill_ids)
        query_embedding = self._embedder.embed([weakness_query])[0]

        attempted = set(profile.attempted_resource_ids)
        scored: list[Recommendation] = []
        for resource in self._resources:
            if resource.resource_id in attempted:
                continue
            if abs(resource.grade_level - profile.grade_level) > 1:
                continue
            targeted = [sid for sid in resource.skill_ids if sid in weak_skill_ids]
            if not targeted:
                continue
            scored.append(
                self._score_resource(
                    resource=resource,
                    targeted_skill_ids=targeted,
                    profile=profile,
                    query_embedding=query_embedding,
                    peer_success=peer_success,
                )
            )

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_n]

    def recommend(
        self,
        learner_id: UUID,
        profiles: list[LearnerProfile],
        assignments: list[ClusterAssignment],
        all_traces: list[EnrichedTrace],
        top_n: int = DEFAULT_TOP_N,
    ) -> list[Recommendation]:
        profile = next((p for p in profiles if p.learner_id == learner_id), None)
        if profile is None:
            raise KeyError(f"Unknown learner_id {learner_id}")
        assignment = next((a for a in assignments if a.learner_id == learner_id), None)
        peers: list[LearnerProfile] = []
        if assignment is not None:
            mbox_in_cluster = {
                p.mbox_sha1sum
                for p, a in zip(profiles, assignments, strict=True)
                if a.cluster_id == assignment.cluster_id and p.learner_id != learner_id
            }
            peers = [p for p in profiles if p.mbox_sha1sum in mbox_in_cluster]
        return self.recommend_for_profile(profile, all_traces, peers, top_n)

    # ----- internals -----

    def _weak_skill_ids(self, profile: LearnerProfile) -> set[str]:
        # 1) domaines faibles
        weak_domains = {
            d for d, s in profile.mean_score_per_domain.items() if s < WEAKNESS_DOMAIN_THRESHOLD
        }
        if not weak_domains:
            # rabattement : les 2 domaines au score le plus bas
            ordered = sorted(profile.mean_score_per_domain.items(), key=lambda kv: kv[1])
            weak_domains = {ordered[0][0], ordered[1][0]}
        # 2) skills appartenant à ces domaines, et faibles individuellement
        weak: set[str] = set()
        for skill in self._skills:
            if skill.domain not in weak_domains:
                continue
            if profile.mean_score_per_skill.get(skill.id, 0.5) < WEAKNESS_DOMAIN_THRESHOLD:
                weak.add(skill.id)
        return weak

    def _resource_text(self, resource: LearningResource) -> str:
        labels = [
            self._skill_by_id[sid].preferred_label
            for sid in resource.skill_ids
            if sid in self._skill_by_id
        ]
        return f"{resource.title}. Compétences : {', '.join(labels)}."

    def _build_weakness_query(self, weak_skill_ids: set[str]) -> str:
        snippets = []
        for sid in sorted(weak_skill_ids):
            skill = self._skill_by_id.get(sid)
            if skill is None:
                continue
            snippets.append(f"{skill.preferred_label}. {skill.description}")
        return "Compétences à renforcer : " + " ".join(snippets)

    def _peer_success_rate_by_resource(
        self,
        cluster_peers: list[LearnerProfile],
        all_traces: list[EnrichedTrace],
    ) -> dict[str, float]:
        peer_mbox = {p.mbox_sha1sum for p in cluster_peers}
        attempts: dict[str, int] = defaultdict(int)
        passes: dict[str, int] = defaultdict(int)
        for trace in all_traces:
            if trace.learner_id not in peer_mbox:
                continue
            if trace.success is None:
                continue
            attempts[trace.resource_id] += 1
            if trace.success:
                passes[trace.resource_id] += 1
        return {rid: passes[rid] / n for rid, n in attempts.items() if n > 0}

    def _score_resource(
        self,
        resource: LearningResource,
        targeted_skill_ids: list[str],
        profile: LearnerProfile,
        query_embedding: np.ndarray,
        peer_success: dict[str, float],
    ) -> Recommendation:
        overlap = len(targeted_skill_ids) / len(resource.skill_ids)
        grade_distance = abs(resource.grade_level - profile.grade_level)
        grade_fit = 1.0 if grade_distance == 0 else 0.7
        resource_vec = self._resource_embeddings[self._resource_index[resource.resource_id]]
        semantic = float(np.dot(resource_vec, query_embedding))  # vectors L2-normalisés
        semantic_clamped = max(0.0, min(1.0, (semantic + 1.0) / 2.0))  # [-1,1] → [0,1]
        cluster_rate = peer_success.get(resource.resource_id)
        cluster_signal = cluster_rate if cluster_rate is not None else 0.0

        weights = self._weights
        score = (
            weights.skill_overlap * overlap
            + weights.grade_fit * grade_fit
            + weights.semantic_similarity * semantic_clamped
            + weights.cluster_signal * cluster_signal
        )

        targeted_labels = [
            self._skill_by_id[sid].preferred_label
            for sid in targeted_skill_ids
            if sid in self._skill_by_id
        ]
        explanation = self._explain(
            targeted_labels,
            grade_distance,
            semantic_clamped,
            cluster_rate,
        )
        return Recommendation(
            resource_id=resource.resource_id,
            title=resource.title,
            score=round(float(score), 3),
            weak_skills_targeted=targeted_labels,
            grade_distance=grade_distance,
            semantic_similarity=round(semantic_clamped, 3),
            cluster_success_rate=round(cluster_rate, 3) if cluster_rate is not None else None,
            explanation=explanation,
        )

    @staticmethod
    def _explain(
        targeted_labels: list[str],
        grade_distance: int,
        semantic: float,
        cluster_rate: float | None,
    ) -> str:
        parts = []
        if len(targeted_labels) == 1:
            parts.append(f"cible la compétence faible « {targeted_labels[0]} »")
        else:
            parts.append(
                f"cible {len(targeted_labels)} compétences faibles ("
                + ", ".join(targeted_labels)
                + ")"
            )
        parts.append("niveau exactement adapté" if grade_distance == 0 else "niveau proche")
        parts.append(f"similarité sémantique {semantic:.2f}")
        if cluster_rate is not None:
            parts.append(f"réussie par {round(cluster_rate * 100)}% du cluster")
        return " ; ".join(parts) + "."
