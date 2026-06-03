"""Recommandation : cible les domaines faibles, exclut les ressources MAÎTRISÉES.

NB : "maîtrisée" = passée au moins une fois. Une ressource échouée reste recommandable
(re-travail pédagogique). Cf. ADR-007 (à venir) et l'évolution du contrat
``LearnerProfile.mastered_resource_ids``.
"""

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
def test_recommendations_exclude_already_mastered(reco_fixture) -> None:
    """Une ressource déjà passée n'est jamais re-recommandée en phase nominale."""
    _learners, profiles, clustering, enriched, reco = reco_fixture
    lea = next(p for p in profiles if p.learner_id == LEA_LEARNER_ID)
    recos = reco.recommend(
        learner_id=lea.learner_id,
        profiles=profiles,
        assignments=clustering.assignments,
        all_traces=enriched,
        top_n=10,
    )
    mastered = set(lea.mastered_resource_ids)
    for r in recos:
        assert r.resource_id not in mastered, (
            f"{r.resource_id} déjà maîtrisée par Léa — ne devrait pas être recommandée"
        )


@pytest.mark.unit
def test_failed_resources_are_eligible_for_recommendation(reco_fixture) -> None:
    """Une ressource échouée (tentée mais non maîtrisée) DOIT pouvoir être re-proposée."""
    _learners, profiles, clustering, enriched, reco = reco_fixture
    lea = next(p for p in profiles if p.learner_id == LEA_LEARNER_ID)
    failed_only = set(lea.attempted_resource_ids) - set(lea.mastered_resource_ids)
    assert failed_only, "Léa devrait avoir au moins une ressource tentée mais non maîtrisée"

    recos = reco.recommend(
        learner_id=lea.learner_id,
        profiles=profiles,
        assignments=clustering.assignments,
        all_traces=enriched,
        top_n=10,
    )
    reco_ids = {r.resource_id for r in recos}
    # Il faut qu'au moins une reco vienne du pool "échouée non maîtrisée" — c'est le
    # comportement pédagogique visé.
    assert reco_ids & failed_only, (
        "Aucune ressource échouée n'est re-proposée — le nouveau filtre 'mastered' "
        "doit autoriser le re-travail des échecs"
    )


@pytest.mark.unit
def test_lea_receives_recommendations_on_full_dataset(sample_skills, sample_resources) -> None:
    """Régression : sur la config par défaut (100 apprenants, seed=42), Léa doit avoir
    des recos. C'est le cas qui avait échappé au test initial (N=60) — Léa avait alors
    déjà tenté toutes les ressources de géométrie, et l'ancien filtre "non déjà tentée"
    les éliminait toutes."""
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    learners, traces = gen.generate(ScenarioConfig(n_learners=100, seed=42))
    enricher = EnrichmentService(resources=sample_resources, skills=sample_skills)
    enriched = [enricher.enrich(t) for t in traces]
    profiles = LearnerProfileBuilder(sample_skills).build_all(learners, enriched)
    domains = sorted({s.domain for s in sample_skills})
    clustering = ClusteringService(domains=domains, k_min=2, k_max=8, seed=42).fit(profiles)
    reco = RecommendationService(
        resources=sample_resources,
        skills=sample_skills,
        embedder=StubEmbeddingProvider(),
    )
    recos = reco.recommend(
        learner_id=LEA_LEARNER_ID,
        profiles=profiles,
        assignments=clustering.assignments,
        all_traces=enriched,
        top_n=5,
    )
    assert recos, (
        "Léa doit recevoir au moins 1 reco sur le dataset complet (100 apprenants, seed=42)"
    )
    for r in recos:
        assert r.weak_skills_targeted
        assert r.explanation.strip()


@pytest.mark.unit
def test_weights_sum_validation() -> None:
    with pytest.raises(ValueError, match=r"sum to 1\.0"):
        ScoreWeights(skill_overlap=0.6, grade_fit=0.2, semantic_similarity=0.2, cluster_signal=0.2)
