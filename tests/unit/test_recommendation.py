"""Recommandation : cible les domaines faibles, explication non vide, déjà-tenté exclu."""

import pytest

from skill_bridge.adapters.outbound.stub_embedding_provider import StubEmbeddingProvider
from skill_bridge.application.clustering import ClusteringService
from skill_bridge.application.enrichment import EnrichmentService
from skill_bridge.application.profiling import LearnerProfileBuilder
from skill_bridge.application.recommendation import RecommendationService, ScoreWeights
from skill_bridge.application.trace_generation import (
    LEA_LEARNER_ID,
    ScenarioConfig,
    TraceGenerationService,
)


@pytest.fixture(scope="module")
def reco_fixture(sample_skills, sample_resources):
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    learners, traces = gen.generate(ScenarioConfig(n_learners=60, seed=42))
    enricher = EnrichmentService(resources=sample_resources, skills=sample_skills)
    enriched = [enricher.enrich(t) for t in traces]
    profiles = LearnerProfileBuilder(sample_skills).build_all(learners, enriched)
    domains = sorted({s.domain for s in sample_skills})
    clustering = ClusteringService(domains=domains, k_min=2, k_max=6, seed=42).fit(profiles)
    reco = RecommendationService(
        resources=sample_resources,
        skills=sample_skills,
        embedder=StubEmbeddingProvider(),
    )
    return learners, profiles, clustering, enriched, reco


@pytest.mark.unit
def test_recommendations_target_weak_skills(reco_fixture, sample_skills) -> None:
    _learners, profiles, clustering, enriched, reco = reco_fixture
    lea = next(p for p in profiles if p.learner_id == LEA_LEARNER_ID)
    recos = reco.recommend(
        learner_id=lea.learner_id,
        profiles=profiles,
        assignments=clustering.assignments,
        all_traces=enriched,
        top_n=5,
    )
    assert recos, "Léa devrait recevoir des recommandations"
    # Toutes les recos doivent cibler au moins une compétence faible explicite.
    assert all(r.weak_skills_targeted for r in recos)


@pytest.mark.unit
def test_lea_recommendations_emphasize_weak_geometry(reco_fixture, sample_skills) -> None:
    _learners, profiles, clustering, enriched, reco = reco_fixture
    lea = next(p for p in profiles if p.learner_id == LEA_LEARNER_ID)
    recos = reco.recommend(
        learner_id=lea.learner_id,
        profiles=profiles,
        assignments=clustering.assignments,
        all_traces=enriched,
        top_n=5,
    )
    skill_by_label = {s.preferred_label: s for s in sample_skills}
    geo_domain_hits = 0
    for r in recos:
        for label in r.weak_skills_targeted:
            skill = skill_by_label.get(label)
            if skill and skill.domain == "geometrie_mesures":
                geo_domain_hits += 1
                break
    assert geo_domain_hits >= 1, (
        "Léa étant faible en géométrie, au moins une reco devrait cibler ce domaine"
    )


@pytest.mark.unit
def test_recommendations_have_non_empty_explanations(reco_fixture) -> None:
    _learners, profiles, clustering, enriched, reco = reco_fixture
    lea = next(p for p in profiles if p.learner_id == LEA_LEARNER_ID)
    recos = reco.recommend(
        learner_id=lea.learner_id,
        profiles=profiles,
        assignments=clustering.assignments,
        all_traces=enriched,
        top_n=5,
    )
    for r in recos:
        assert r.explanation.strip()
        assert 0.0 <= r.score <= 1.0


@pytest.mark.unit
def test_recommendations_exclude_already_attempted(reco_fixture) -> None:
    _learners, profiles, clustering, enriched, reco = reco_fixture
    lea = next(p for p in profiles if p.learner_id == LEA_LEARNER_ID)
    recos = reco.recommend(
        learner_id=lea.learner_id,
        profiles=profiles,
        assignments=clustering.assignments,
        all_traces=enriched,
        top_n=10,
    )
    attempted = set(lea.attempted_resource_ids)
    for r in recos:
        assert r.resource_id not in attempted


@pytest.mark.unit
def test_weights_sum_validation() -> None:
    with pytest.raises(ValueError, match=r"sum to 1\.0"):
        ScoreWeights(skill_overlap=0.6, grade_fit=0.2, semantic_similarity=0.2, cluster_signal=0.2)
