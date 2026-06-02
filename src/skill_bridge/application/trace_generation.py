"""Génération du scénario maths primaire : apprenants + traces xAPI.

Reproductible via une seed unique (numpy + Faker). Chaque apprenant porte un vecteur d'ability
indexé par domaine de compétence ; le taux de succès d'une trace dépend de l'ability de
l'apprenant dans le domaine dominant de la ressource.
"""

import hashlib
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Final
from uuid import NAMESPACE_URL, UUID, uuid5

import numpy as np
from faker import Faker

from skill_bridge.domain.entities import (
    Activity,
    ActivityDefinition,
    Actor,
    Learner,
    LearningResource,
    LearningTrace,
    Result,
    Score,
    Skill,
    Verb,
)
from skill_bridge.domain.enums import (
    ACTIVITY_TYPE_URIS,
    VERB_URIS,
    LearningVerb,
    ResourceType,
)

ACTIVITY_BASE_URI: Final[str] = "http://skillbridge.local/resource/"
NAMESPACE_SKILLBRIDGE: Final[UUID] = uuid5(NAMESPACE_URL, "https://skillbridge.local/")
LEA_LEARNER_ID: Final[UUID] = uuid5(NAMESPACE_SKILLBRIDGE, "learner/lea-martin")

DEFAULT_LEA_ABILITY: Final[dict[str, float]] = {
    "calcul_de_base": 0.88,
    "calcul_avance": 0.85,
    "fractions_decimaux": 0.78,
    "geometrie_mesures": 0.42,
    "unites_temps": 0.55,
    "resolution_problemes": 0.80,
}


@dataclass(frozen=True)
class ScenarioConfig:
    n_learners: int = 50
    n_traces_mean: int = 50
    n_traces_std: int = 15
    n_traces_min: int = 10
    n_traces_max: int = 150
    time_window_days: int = 90
    end_date: datetime | None = None
    seed: int = 42
    lea_ability: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_LEA_ABILITY))


def _mbox_sha1(email: str) -> str:
    return hashlib.sha1(f"mailto:{email}".encode()).hexdigest()


def _iso8601_duration(seconds: int) -> str:
    return f"PT{seconds}S"


def _slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return normalized.lower().replace(" ", ".").replace("'", "")


class TraceGenerationService:
    """Produit la population d'apprenants et leurs statements xAPI."""

    def __init__(self, skills: list[Skill], resources: list[LearningResource]) -> None:
        if not skills:
            raise ValueError("skills must not be empty")
        if not resources:
            raise ValueError("resources must not be empty")
        self._skills = skills
        self._resources = resources
        self._domain_by_skill_id = {s.id: s.domain for s in skills}
        self._domains = sorted({s.domain for s in skills})

        missing = [
            sid for r in resources for sid in r.skill_ids if sid not in self._domain_by_skill_id
        ]
        if missing:
            raise ValueError(f"Resources reference unknown skill_ids: {sorted(set(missing))}")

    # ----- public API -----

    def generate(self, config: ScenarioConfig) -> tuple[list[Learner], list[LearningTrace]]:
        rng = np.random.default_rng(config.seed)
        faker = Faker("fr_FR")
        faker.seed_instance(config.seed)

        end = config.end_date or datetime.now(UTC).replace(microsecond=0)
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)
        start = end - timedelta(days=config.time_window_days)

        learners = self._generate_learners(rng, faker, config)
        traces: list[LearningTrace] = []
        for learner in learners:
            n_traces = int(
                np.clip(
                    rng.normal(config.n_traces_mean, max(config.n_traces_std, 0)),
                    config.n_traces_min,
                    config.n_traces_max,
                )
            )
            traces.extend(self._generate_traces_for_learner(rng, learner, n_traces, start, end))
        return learners, traces

    # ----- learners -----

    def _generate_learners(
        self, rng: np.random.Generator, faker: Faker, config: ScenarioConfig
    ) -> list[Learner]:
        if config.n_learners < 1:
            return []

        lea_ability = {d: 0.6 for d in self._domains}
        lea_ability.update(config.lea_ability)
        lea = Learner(
            learner_id=LEA_LEARNER_ID,
            display_name="Léa Martin",
            mbox_sha1sum=_mbox_sha1("lea.martin@example.org"),
            grade_level=4,
            ability=lea_ability,
        )
        learners: list[Learner] = [lea]

        for idx in range(config.n_learners - 1):
            display_name = faker.name()
            grade = int(rng.integers(1, 6))
            base = float(rng.normal(0.65, 0.10))
            ability = {
                d: float(np.clip(base + float(rng.normal(0.0, 0.18)), 0.30, 0.95))
                for d in self._domains
            }
            handle = f"{_slugify(display_name)}.{idx}@example.org"
            learner_uuid = uuid5(NAMESPACE_SKILLBRIDGE, f"learner/{idx}/{display_name}")
            learners.append(
                Learner(
                    learner_id=learner_uuid,
                    display_name=display_name,
                    mbox_sha1sum=_mbox_sha1(handle),
                    grade_level=grade,
                    ability=ability,
                )
            )
        return learners

    # ----- traces -----

    def _generate_traces_for_learner(
        self,
        rng: np.random.Generator,
        learner: Learner,
        n_traces: int,
        start: datetime,
        end: datetime,
    ) -> list[LearningTrace]:
        if n_traces <= 0:
            return []
        weights = np.array(
            [self._resource_weight(r, learner) for r in self._resources], dtype=float
        )
        weights = weights / weights.sum()

        total_seconds = max(int((end - start).total_seconds()), 1)
        offsets = np.sort(rng.integers(0, total_seconds, size=n_traces))

        traces: list[LearningTrace] = []
        for i, offset in enumerate(offsets):
            resource_idx = int(rng.choice(len(self._resources), p=weights))
            resource = self._resources[resource_idx]
            timestamp = start + timedelta(seconds=int(offset))
            traces.append(self._build_trace(rng, learner, resource, timestamp, i))
        return traces

    @staticmethod
    def _resource_weight(resource: LearningResource, learner: Learner) -> float:
        diff = abs(resource.grade_level - learner.grade_level)
        return {0: 1.0, 1: 0.5, 2: 0.2}.get(diff, 0.05)

    def _resource_ability(self, learner: Learner, resource: LearningResource) -> float:
        domains = [self._domain_by_skill_id[sid] for sid in resource.skill_ids]
        return sum(learner.ability.get(d, 0.5) for d in domains) / len(domains)

    def _build_trace(
        self,
        rng: np.random.Generator,
        learner: Learner,
        resource: LearningResource,
        timestamp: datetime,
        trace_index: int,
    ) -> LearningTrace:
        ability = self._resource_ability(learner, resource)
        activity = Activity(
            id=f"{ACTIVITY_BASE_URI}{resource.resource_id}",
            definition=ActivityDefinition(
                name={"fr-FR": resource.title},
                type=ACTIVITY_TYPE_URIS[resource.type],
            ),
        )
        actor = Actor(mbox_sha1sum=learner.mbox_sha1sum, name=learner.display_name)

        if resource.type is ResourceType.LESSON:
            verb_enum = LearningVerb.COMPLETED
            duration = self._sample_duration(rng, resource.estimated_duration_s, jitter=0.15)
            result = Result(
                success=True,
                completion=True,
                duration=_iso8601_duration(duration),
            )
        else:
            success = bool(rng.random() < ability)
            if success:
                verb_enum = LearningVerb.PASSED
                raw_score = float(np.clip(rng.normal(ability, 0.08), 0.5, 1.0))
            else:
                verb_enum = LearningVerb.FAILED
                raw_score = float(np.clip(rng.normal(ability * 0.55, 0.10), 0.0, 0.49))
            duration = self._sample_duration(rng, resource.estimated_duration_s, jitter=0.25)
            result = Result(
                success=success,
                completion=True,
                score=Score(scaled=round(raw_score, 3)),
                duration=_iso8601_duration(duration),
            )

        verb = Verb(id=VERB_URIS[verb_enum], display={"en-US": verb_enum.value})
        trace_uuid = uuid5(NAMESPACE_SKILLBRIDGE, f"trace/{learner.learner_id}/{trace_index}")
        return LearningTrace(
            id=trace_uuid,
            actor=actor,
            verb=verb,
            object=activity,
            result=result,
            timestamp=timestamp,
        )

    @staticmethod
    def _sample_duration(rng: np.random.Generator, estimated_s: int, jitter: float) -> int:
        return int(
            np.clip(
                rng.normal(estimated_s, estimated_s * jitter),
                max(estimated_s * 0.3, 5),
                estimated_s * 2.0,
            )
        )
