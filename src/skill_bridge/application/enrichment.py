"""Enrichissement d'une trace par les compétences (et mappings ESCO) de sa ressource."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from skill_bridge.domain.entities import LearningResource, LearningTrace, Skill

ACTIVITY_BASE_URI: Final[str] = "http://skillbridge.local/resource/"


@dataclass(frozen=True)
class ResolvedSkill:
    id: str
    preferred_label: str
    domain: str
    esco_uris: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "preferred_label": self.preferred_label,
            "domain": self.domain,
            "esco_uris": list(self.esco_uris),
        }


@dataclass(frozen=True)
class EnrichedTrace:
    trace_id: str
    learner_id: str  # mbox_sha1sum (pseudonyme)
    resource_id: str
    verb: str
    success: bool | None
    score: float | None
    duration: str | None
    timestamp: datetime
    skills: list[ResolvedSkill]

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "learner_id": self.learner_id,
            "resource_id": self.resource_id,
            "verb": self.verb,
            "success": self.success,
            "score": self.score,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat(),
            "skills": [s.to_dict() for s in self.skills],
        }


class EnrichmentService:
    """Joint chaque trace xAPI aux compétences portées par sa ressource."""

    def __init__(self, resources: list[LearningResource], skills: list[Skill]) -> None:
        self._resource_by_id = {r.resource_id: r for r in resources}
        self._skill_by_id = {s.id: s for s in skills}

    def enrich(self, trace: LearningTrace) -> EnrichedTrace:
        resource_id = self._extract_resource_id(trace.object.id)
        resource = self._resource_by_id.get(resource_id)
        if resource is None:
            raise KeyError(f"Resource not found in catalog: {resource_id!r}")

        skills = [
            ResolvedSkill(
                id=skill.id,
                preferred_label=skill.preferred_label,
                domain=skill.domain,
                esco_uris=list(skill.esco_uris),
            )
            for skill in (self._skill_by_id.get(sid) for sid in resource.skill_ids)
            if skill is not None
        ]

        return EnrichedTrace(
            trace_id=str(trace.id),
            learner_id=trace.actor.mbox_sha1sum,
            resource_id=resource_id,
            verb=self._extract_verb(trace.verb.id),
            success=trace.result.success if trace.result else None,
            score=(trace.result.score.scaled if trace.result and trace.result.score else None),
            duration=trace.result.duration if trace.result else None,
            timestamp=trace.timestamp,
            skills=skills,
        )

    @staticmethod
    def _extract_resource_id(activity_id: str) -> str:
        if activity_id.startswith(ACTIVITY_BASE_URI):
            return activity_id[len(ACTIVITY_BASE_URI) :]
        return activity_id.rsplit("/", 1)[-1]

    @staticmethod
    def _extract_verb(verb_id: str) -> str:
        return verb_id.rsplit("/", 1)[-1]
