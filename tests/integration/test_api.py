"""Tests d'intégration de l'API FastAPI.

Marker ``integration`` car ils déclenchent le lifespan complet (chargement seeds +
profilage + clustering + précompute des recos). On utilise ``StubEmbeddingProvider``
pour éviter le download du modèle ST en CI — la stack reste rapide (~1 s).
"""

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from skill_bridge.adapters.inbound.api.app import (
    DEFAULT_ESCO_MAPPING,
    DEFAULT_RESOURCES,
    DEFAULT_SKILLS,
    create_app,
)
from skill_bridge.adapters.outbound.dataset_writer import write_jsonl
from skill_bridge.adapters.outbound.stub_embedding_provider import StubEmbeddingProvider
from skill_bridge.adapters.outbound.xapi_encoder import XApiJsonLinesEncoder
from skill_bridge.application.enrichment import EnrichmentService
from skill_bridge.application.trace_generation import (
    LEA_LEARNER_ID,
    ScenarioConfig,
    TraceGenerationService,
)

N_LEARNERS = 30  # >= k_max + 1 = 9 ; assez petit pour tests rapides


@pytest.fixture(scope="module")
def generated_dataset(tmp_path_factory, sample_skills, sample_resources):
    tmp = tmp_path_factory.mktemp("api_dataset")

    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    learners, traces = gen.generate(ScenarioConfig(n_learners=N_LEARNERS, seed=42))
    encoder = XApiJsonLinesEncoder()
    enricher = EnrichmentService(resources=sample_resources, skills=sample_skills)

    write_jsonl((encoder.encode(t) for t in traces), tmp / "traces.jsonl")
    write_jsonl((enricher.enrich(t).to_dict() for t in traces), tmp / "enriched.jsonl")
    write_jsonl(
        (
            {
                "learner_id": str(ln.learner_id),
                "mbox_sha1sum": ln.mbox_sha1sum,
                "display_name": ln.display_name,
                "grade_level": ln.grade_level,
                "archetype": ln.archetype,
                "ability": dict(ln.ability),
            }
            for ln in learners
        ),
        tmp / "learners.jsonl",
    )

    return {"tmp": tmp, "learners": learners}


@pytest.fixture(scope="module")
def client(generated_dataset) -> TestClient:
    tmp: Path = generated_dataset["tmp"]
    app = create_app(
        embedder=StubEmbeddingProvider(),
        skills_path=DEFAULT_SKILLS,
        esco_mapping_path=DEFAULT_ESCO_MAPPING,
        resources_path=DEFAULT_RESOURCES,
        enriched_path=tmp / "enriched.jsonl",
        learners_path=tmp / "learners.jsonl",
        seed=42,
    )
    with TestClient(app) as c:
        yield c


@pytest.mark.integration
def test_health_returns_ok(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["preloaded"] is True
    assert body["n_learners"] == N_LEARNERS
    assert body["n_skills"] == 18
    assert body["n_resources"] == 33
    assert body["n_clusters"] >= 2


@pytest.mark.integration
def test_learners_returns_list_without_archetype(client: TestClient) -> None:
    r = client.get("/learners")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == N_LEARNERS
    for entry in body:
        assert set(entry) == {"learner_id", "display_name", "grade_level"}
        # garde-fou : aucun champ "archetype" / "ability" ne doit fuiter
        assert "archetype" not in entry
        assert "ability" not in entry
    assert any(entry["display_name"] == "Léa Martin" for entry in body)


@pytest.mark.integration
def test_profile_for_lea(client: TestClient) -> None:
    r = client.get(f"/profile/{LEA_LEARNER_ID}")
    assert r.status_code == 200
    body = r.json()
    assert UUID(body["learner_id"]) == LEA_LEARNER_ID
    assert body["grade_level"] == 4
    assert body["n_traces"] > 0
    # Léa = calc_specialist : forte en calcul, faible en géo
    assert (
        body["mean_score_per_domain"]["calcul_de_base"]
        > body["mean_score_per_domain"]["geometrie_mesures"]
    )


@pytest.mark.integration
def test_profile_unknown_returns_404(client: TestClient) -> None:
    r = client.get(f"/profile/{uuid4()}")
    assert r.status_code == 404


@pytest.mark.integration
def test_clusters_payload_shape(client: TestClient) -> None:
    r = client.get("/clusters")
    assert r.status_code == 200
    body = r.json()
    # silhouette_by_k couvre toute la bande k_min..k_max
    assert set(int(k) for k in body["silhouette_by_k"]) == set(range(2, 9))
    # k retenu est l'argmax
    assert body["silhouette"] == pytest.approx(max(body["silhouette_by_k"].values()))
    # somme des tailles == nb apprenants
    assert sum(c["size"] for c in body["clusters"]) == N_LEARNERS
    # chaque centroïde couvre les 6 domaines
    for cluster in body["clusters"]:
        assert len(cluster["centroid_per_domain"]) == 6
        assert cluster["label"]


@pytest.mark.integration
def test_cluster_assignment_for_lea(client: TestClient) -> None:
    r = client.get(f"/clusters/assignment/{LEA_LEARNER_ID}")
    assert r.status_code == 200
    body = r.json()
    assert UUID(body["learner_id"]) == LEA_LEARNER_ID
    assert body["cluster_id"] >= 0
    assert body["cluster_label"]


@pytest.mark.integration
def test_recommend_returns_explanations(client: TestClient) -> None:
    r = client.get(f"/recommend/{LEA_LEARNER_ID}?n=5")
    assert r.status_code == 200
    body = r.json()
    assert 1 <= len(body) <= 5
    for reco in body:
        assert reco["explanation"].strip()
        assert reco["weak_skills_targeted"]
        assert 0.0 <= reco["score"] <= 1.0


@pytest.mark.integration
def test_recommend_respects_n_param(client: TestClient) -> None:
    r3 = client.get(f"/recommend/{LEA_LEARNER_ID}?n=3").json()
    r5 = client.get(f"/recommend/{LEA_LEARNER_ID}?n=5").json()
    assert len(r3) <= 3
    assert len(r5) >= len(r3)
    # même prefix : c'est bien un slice du top-10 préchargé
    assert [r["resource_id"] for r in r3] == [r["resource_id"] for r in r5[: len(r3)]]


@pytest.mark.integration
def test_recommend_unknown_returns_404(client: TestClient) -> None:
    r = client.get(f"/recommend/{uuid4()}")
    assert r.status_code == 404


@pytest.mark.integration
def test_openapi_schema_is_served(client: TestClient) -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    body = r.json()
    assert body["info"]["title"] == "SkillBridge API"
    assert "/health" in body["paths"]
    assert "/learners" in body["paths"]
    assert "/clusters" in body["paths"]
    assert "/recommend/{learner_id}" in body["paths"]
