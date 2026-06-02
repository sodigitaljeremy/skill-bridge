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
def test_silhouette_picks_k_matching_archetype_count(clustering_fixture) -> None:
    _skills, _learners, _profiles, result = clustering_fixture
    # Avec 4 archetypes spécialisés par *forme* (moyennes globales comparables), la silhouette
    # doit naturellement piquer autour de k=4 (toléré [3, 5] selon les hasards d'init KMeans).
    assert 3 <= result.k <= 5, (
        f"k={result.k} hors bande attendue (silhouette : {result.silhouette_by_k})"
    )
    assert result.silhouette > 0.25
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
        # Avec archetypes spécialisés par forme (sigma=0.10), pureté observée >= 88%
        # sur seed=42 ; seuil à 0.80 pour absorber la variance d'init KMeans.
        assert purity >= 0.80, (
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
        if archetype == "calc_specialist"
    )
    dominant_cluster, _ = counts.most_common(1)[0]
    centroid = result.centroids_per_domain[dominant_cluster]
    assert centroid["geometrie_mesures"] < centroid["calcul_de_base"], (
        f"Centroïde C{dominant_cluster} pas cohérent avec 'fort calcul / faible géométrie' : "
        f"{centroid}"
    )
