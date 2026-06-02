"""Clustering : silhouette choisit un k cohérent, et les clusters retrouvent les archétypes."""

from collections import Counter

import pytest

from skill_bridge.application.clustering import ClusteringService
from skill_bridge.application.enrichment import EnrichmentService
from skill_bridge.application.profiling import LearnerProfileBuilder
from skill_bridge.application.trace_generation import (
    ARCHETYPES,
    ScenarioConfig,
    TraceGenerationService,
)


@pytest.fixture(scope="module")
def clustering_fixture(sample_skills, sample_resources):
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    learners, traces = gen.generate(ScenarioConfig(n_learners=120, seed=42))
    enricher = EnrichmentService(resources=sample_resources, skills=sample_skills)
    enriched = [enricher.enrich(t) for t in traces]
    profiles = LearnerProfileBuilder(sample_skills).build_all(learners, enriched)
    domains = sorted({s.domain for s in sample_skills})
    result = ClusteringService(domains=domains, k_min=2, k_max=8, seed=42).fit(profiles)
    return sample_skills, learners, profiles, result


@pytest.mark.unit
def test_silhouette_picks_k_in_expected_band(clustering_fixture) -> None:
    _skills, _learners, _profiles, result = clustering_fixture
    # 4 archetypes latents, mais silhouette pure peut regrouper les "high archetypes"
    # (strong_calc_weak_geo / balanced_strong / strong_reasoning) en un seul cluster vs
    # struggling — d'où la bande [2, 5]. Le sanity-check archétype↔cluster (test suivant)
    # vérifie que la structure reste informative quel que soit k.
    assert 2 <= result.k <= 5, (
        f"k={result.k} hors bande sensée (silhouette : {result.silhouette_by_k})"
    )
    assert result.silhouette > 0.20
    # Sanity sur l'algo : le k retenu doit bien être l'argmax des silhouettes calculées.
    assert result.silhouette == max(result.silhouette_by_k.values())


@pytest.mark.unit
def test_each_archetype_has_a_dominant_cluster(clustering_fixture) -> None:
    _skills, learners, profiles, result = clustering_fixture
    archetype_by_mbox = {ln.mbox_sha1sum: ln.archetype for ln in learners if ln.archetype}
    cluster_by_mbox = {
        p.mbox_sha1sum: a.cluster_id for p, a in zip(profiles, result.assignments, strict=True)
    }

    # pour chaque archetype, quel cluster est majoritaire et avec quelle concentration ?
    archetype_to_clusters: dict[str, Counter[int]] = {a: Counter() for a in ARCHETYPES}
    for mbox, archetype in archetype_by_mbox.items():
        archetype_to_clusters[archetype][cluster_by_mbox[mbox]] += 1

    for archetype, counts in archetype_to_clusters.items():
        assert counts, f"{archetype} sans apprenant ?"
        dominant, n = counts.most_common(1)[0]
        purity = n / sum(counts.values())
        assert purity >= 0.60, (
            f"{archetype} dispersé : cluster majoritaire={dominant} purity={purity:.0%}"
        )


@pytest.mark.unit
def test_cluster_labels_mention_geometry_for_lea_archetype(clustering_fixture) -> None:
    """Le centroïde du cluster majoritaire de Léa doit refléter géométrie faible."""
    _skills, learners, profiles, result = clustering_fixture
    archetype_by_mbox = {ln.mbox_sha1sum: ln.archetype for ln in learners if ln.archetype}
    cluster_by_mbox = {
        p.mbox_sha1sum: a.cluster_id for p, a in zip(profiles, result.assignments, strict=True)
    }
    counts: Counter[int] = Counter(
        cluster_by_mbox[mbox]
        for mbox, archetype in archetype_by_mbox.items()
        if archetype == "strong_calc_weak_geo"
    )
    dominant_cluster, _ = counts.most_common(1)[0]
    centroid = result.centroids_per_domain[dominant_cluster]
    assert centroid["geometrie_mesures"] < centroid["calcul_de_base"], (
        f"Centroïde C{dominant_cluster} pas cohérent avec 'fort calcul / faible géométrie' : "
        f"{centroid}"
    )
