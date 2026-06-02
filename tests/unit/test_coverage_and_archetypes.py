"""Tests des ajustements Lot 1 : couverture stratifiée et séparabilité des archetypes."""

from collections import defaultdict

import numpy as np
import pytest

from skill_bridge.application.trace_generation import (
    ARCHETYPES,
    LEA_ARCHETYPE,
    LEA_LEARNER_ID,
    ScenarioConfig,
    TraceGenerationService,
    compute_domain_coverage,
)

MIN_TRACES_PER_DOMAIN_PER_LEARNER = 5


@pytest.mark.unit
def test_each_learner_has_minimum_traces_per_domain(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    config = ScenarioConfig(n_learners=30, n_traces_mean=60, n_traces_std=0, seed=42)
    learners, traces = gen.generate(config)

    domain_by_skill_id = {s.id: s.domain for s in sample_skills}
    resource_primary = {r.resource_id: domain_by_skill_id[r.skill_ids[0]] for r in sample_resources}
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for trace in traces:
        rid = trace.object.id.rsplit("/", 1)[-1]
        counts[trace.actor.mbox_sha1sum][resource_primary[rid]] += 1

    expected_domains = {s.domain for s in sample_skills}
    failures: list[str] = []
    for learner in learners:
        for domain in expected_domains:
            n = counts[learner.mbox_sha1sum].get(domain, 0)
            if n < MIN_TRACES_PER_DOMAIN_PER_LEARNER:
                failures.append(f"{learner.display_name}/{domain}={n}")
    assert not failures, (
        f"Apprenants sous le seuil de {MIN_TRACES_PER_DOMAIN_PER_LEARNER} "
        f"traces/domaine : {failures[:5]}..."
    )


@pytest.mark.unit
def test_compute_domain_coverage_returns_balanced_stats(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    config = ScenarioConfig(n_learners=20, n_traces_mean=60, n_traces_std=0, seed=7)
    learners, traces = gen.generate(config)

    coverages = compute_domain_coverage(learners, traces, sample_resources, sample_skills)
    assert {c.domain for c in coverages} == {s.domain for s in sample_skills}
    for cov in coverages:
        assert cov.per_learner_min >= MIN_TRACES_PER_DOMAIN_PER_LEARNER, cov
        assert cov.per_learner_median > 0
        assert cov.per_learner_max >= cov.per_learner_median


@pytest.mark.unit
def test_archetypes_are_separable(sample_skills, sample_resources) -> None:
    """Chaque apprenant doit être plus proche du centroïde de SON archetype que des autres."""
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    learners, _ = gen.generate(ScenarioConfig(n_learners=120, seed=42))

    domain_keys = sorted(next(iter(ARCHETYPES.values())).keys())

    def vec(d: dict[str, float]) -> np.ndarray:
        return np.array([d[k] for k in domain_keys])

    centroids = {name: vec(c) for name, c in ARCHETYPES.items()}

    correct = 0
    total = 0
    for learner in learners:
        if learner.archetype is None:
            continue
        total += 1
        lv = vec(learner.ability)
        closest = min(centroids, key=lambda a: float(np.linalg.norm(lv - centroids[a])))
        if closest == learner.archetype:
            correct += 1

    assert total > 0
    accuracy = correct / total
    assert accuracy >= 0.80, (
        f"Archetypes peu séparables : {accuracy:.0%} d'apprenants sont les "
        f"plus proches de leur propre centroïde (cible ≥ 80%)."
    )


@pytest.mark.unit
def test_lea_is_assigned_to_strong_calc_weak_geo(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    learners, _ = gen.generate(ScenarioConfig(n_learners=10, seed=3))
    lea = next(x for x in learners if x.learner_id == LEA_LEARNER_ID)
    assert lea.archetype == LEA_ARCHETYPE
    # Léa : sans bruit, son ability colle au centroïde.
    centroid = ARCHETYPES[LEA_ARCHETYPE]
    for domain, expected in centroid.items():
        assert lea.ability[domain] == pytest.approx(expected, abs=1e-9)


@pytest.mark.unit
def test_archetype_distribution_is_diverse(sample_skills, sample_resources) -> None:
    """Tous les archetypes doivent être représentés au-delà d'un seuil minimal."""
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    learners, _ = gen.generate(ScenarioConfig(n_learners=100, seed=42))
    counts = defaultdict(int)
    for learner in learners:
        if learner.archetype:
            counts[learner.archetype] += 1
    for archetype in ARCHETYPES:
        assert counts[archetype] >= 10, f"{archetype} sous-représenté : {counts[archetype]}"
