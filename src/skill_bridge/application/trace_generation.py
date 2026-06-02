"""Génération du scénario maths primaire : apprenants + traces xAPI.

Reproductible via une seed unique (numpy + Faker). Trois mécanismes clés :

1. **Archetypes latents** : chaque apprenant est tiré d'un de quatre profils (fort calcul /
   faible géométrie, équilibré fort, en difficulté, fort en raisonnement), avec un léger
   bruit gaussien. Léa est toujours assignée à ``strong_calc_weak_geo``. Objectif : que le
   clustering du Lot 2 retrouve des groupes nets et interprétables.
2. **Vecteur d'ability par domaine** : la probabilité de succès d'une trace dépend de
   l'ability moyenne de l'apprenant sur les domaines de la ressource.
3. **Échantillonnage stratifié par domaine** : chaque apprenant pratique tous les domaines,
   avec un nombre de traces par domaine équilibré (`n_traces // n_domains` ± remainder).
"""

import hashlib
import unicodedata
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
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

# --- Archetypes latents ---

LEA_ARCHETYPE: Final[str] = "strong_calc_weak_geo"

ARCHETYPES: Final[Mapping[str, Mapping[str, float]]] = {
    "strong_calc_weak_geo": {
        "calcul_de_base": 0.85,
        "calcul_avance": 0.82,
        "fractions_decimaux": 0.75,
        "geometrie_mesures": 0.40,
        "unites_temps": 0.55,
        "resolution_problemes": 0.75,
    },
    "balanced_strong": {
        "calcul_de_base": 0.78,
        "calcul_avance": 0.75,
        "fractions_decimaux": 0.75,
        "geometrie_mesures": 0.78,
        "unites_temps": 0.75,
        "resolution_problemes": 0.78,
    },
    "struggling": {
        "calcul_de_base": 0.48,
        "calcul_avance": 0.40,
        "fractions_decimaux": 0.40,
        "geometrie_mesures": 0.42,
        "unites_temps": 0.45,
        "resolution_problemes": 0.42,
    },
    "strong_reasoning": {
        "calcul_de_base": 0.55,
        "calcul_avance": 0.50,
        "fractions_decimaux": 0.55,
        "geometrie_mesures": 0.62,
        "unites_temps": 0.55,
        "resolution_problemes": 0.92,
    },
}
ARCHETYPE_NOISE_SIGMA: Final[float] = 0.10
ABILITY_FLOOR: Final[float] = 0.30
ABILITY_CEIL: Final[float] = 0.95


@dataclass(frozen=True)
class ScenarioConfig:
    n_learners: int = 100
    n_traces_mean: int = 60
    n_traces_std: int = 15
    n_traces_min: int = 30  # garantit >= 5 traces / domaine après stratification (6 domaines)
    n_traces_max: int = 180
    time_window_days: int = 90
    end_date: datetime | None = None
    seed: int = 42
    lea_archetype: str = LEA_ARCHETYPE


def _mbox_sha1(email: str) -> str:
    return hashlib.sha1(f"mailto:{email}".encode()).hexdigest()


def _iso8601_duration(seconds: int) -> str:
    return f"PT{seconds}S"


def _slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return normalized.lower().replace(" ", ".").replace("'", "")


@dataclass(frozen=True)
class DomainCoverage:
    domain: str
    total: int
    per_learner_min: int
    per_learner_median: int
    per_learner_max: int


def compute_domain_coverage(
    learners: list[Learner],
    traces: list[LearningTrace],
    resources: list[LearningResource],
    skills: list[Skill],
) -> list[DomainCoverage]:
    """Stats par domaine pour une suite de traces : total + (min/médiane/max) par apprenant.

    Le « domaine d'une trace » est le domaine de la première compétence de la ressource —
    soit le domaine dominant tel que rangé dans ``skill_ids`` du catalogue.
    """
    domain_by_skill_id = {s.id: s.domain for s in skills}
    resource_primary_domain = {r.resource_id: domain_by_skill_id[r.skill_ids[0]] for r in resources}

    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    domain_totals: dict[str, int] = defaultdict(int)
    for trace in traces:
        resource_id = trace.object.id.rsplit("/", 1)[-1]
        domain = resource_primary_domain.get(resource_id)
        if domain is None:
            continue
        counts[trace.actor.mbox_sha1sum][domain] += 1
        domain_totals[domain] += 1

    learner_mboxes = [learner.mbox_sha1sum for learner in learners]
    coverages: list[DomainCoverage] = []
    for domain in sorted(domain_totals):
        per_learner = sorted(counts[mbox].get(domain, 0) for mbox in learner_mboxes)
        coverages.append(
            DomainCoverage(
                domain=domain,
                total=domain_totals[domain],
                per_learner_min=per_learner[0] if per_learner else 0,
                per_learner_median=per_learner[len(per_learner) // 2] if per_learner else 0,
                per_learner_max=per_learner[-1] if per_learner else 0,
            )
        )
    return coverages


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

        # Index ressources par domaine primaire (domaine de la première compétence).
        self._resources_by_domain: dict[str, list[LearningResource]] = defaultdict(list)
        for resource in resources:
            primary = self._domain_by_skill_id[resource.skill_ids[0]]
            self._resources_by_domain[primary].append(resource)

        uncovered = [d for d in self._domains if not self._resources_by_domain.get(d)]
        if uncovered:
            raise ValueError(f"No resources for domain(s): {uncovered}")

    # ----- public API -----

    def generate(self, config: ScenarioConfig) -> tuple[list[Learner], list[LearningTrace]]:
        if config.lea_archetype not in ARCHETYPES:
            raise ValueError(
                f"Unknown lea_archetype {config.lea_archetype!r}; available: {sorted(ARCHETYPES)}"
            )

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

        learners: list[Learner] = [self._make_lea(config.lea_archetype)]

        archetype_names = list(ARCHETYPES)
        for idx in range(config.n_learners - 1):
            display_name = faker.name()
            grade = int(rng.integers(1, 6))
            archetype = str(rng.choice(archetype_names))
            ability = self._sample_ability(rng, archetype)
            handle = f"{_slugify(display_name)}.{idx}@example.org"
            learner_uuid = uuid5(NAMESPACE_SKILLBRIDGE, f"learner/{idx}/{display_name}")
            learners.append(
                Learner(
                    learner_id=learner_uuid,
                    display_name=display_name,
                    mbox_sha1sum=_mbox_sha1(handle),
                    grade_level=grade,
                    ability=ability,
                    archetype=archetype,
                )
            )
        return learners

    def _make_lea(self, archetype: str) -> Learner:
        # Léa : centroïde de son archetype sans bruit (persona stable pour la démo).
        centroid = ARCHETYPES[archetype]
        ability = {d: float(centroid.get(d, 0.6)) for d in self._domains}
        return Learner(
            learner_id=LEA_LEARNER_ID,
            display_name="Léa Martin",
            mbox_sha1sum=_mbox_sha1("lea.martin@example.org"),
            grade_level=4,
            ability=ability,
            archetype=archetype,
        )

    def _sample_ability(self, rng: np.random.Generator, archetype: str) -> dict[str, float]:
        centroid = ARCHETYPES[archetype]
        return {
            d: float(
                np.clip(
                    centroid.get(d, 0.6) + float(rng.normal(0.0, ARCHETYPE_NOISE_SIGMA)),
                    ABILITY_FLOOR,
                    ABILITY_CEIL,
                )
            )
            for d in self._domains
        }

    # ----- traces : stratified sampling par domaine -----

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

        domain_counts = self._stratify(rng, n_traces)
        chosen_resources: list[LearningResource] = []
        for domain, count in domain_counts.items():
            if count == 0:
                continue
            resources = self._resources_by_domain[domain]
            weights = np.array([self._resource_weight(r, learner) for r in resources], dtype=float)
            weights = weights / weights.sum()
            indices = rng.choice(len(resources), size=count, p=weights, replace=True)
            chosen_resources.extend(resources[i] for i in indices)

        # Mélange l'ordre temporel des domaines (sinon toutes les traces d'un domaine seraient
        # contiguës), puis attribue des timestamps triés.
        rng.shuffle(chosen_resources)
        total_seconds = max(int((end - start).total_seconds()), 1)
        offsets = np.sort(rng.integers(0, total_seconds, size=len(chosen_resources)))

        traces: list[LearningTrace] = []
        for i, (resource, offset) in enumerate(zip(chosen_resources, offsets, strict=True)):
            timestamp = start + timedelta(seconds=int(offset))
            traces.append(self._build_trace(rng, learner, resource, timestamp, i))
        return traces

    def _stratify(self, rng: np.random.Generator, n_traces: int) -> dict[str, int]:
        n_domains = len(self._domains)
        base = n_traces // n_domains
        remainder = n_traces - base * n_domains
        counts = {d: base for d in self._domains}
        for d in rng.choice(self._domains, size=remainder, replace=True):
            counts[str(d)] += 1
        return counts

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
