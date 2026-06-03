"""Application FastAPI — provider lecture seule pour SkillBridge.

Factory ``create_app()`` compatible ``uvicorn --factory`` :

    uv run uvicorn skill_bridge.adapters.inbound.api.app:create_app --factory --port 8000

Préchargement complet (skills, resources, learners, profils, clustering, embeddings,
top-10 reco par apprenant) au lifespan. Les requêtes ne touchent jamais ST ni KMeans.

L'``embedder`` est injectable pour les tests (``StubEmbeddingProvider``) — sinon défaut
``SentenceTransformersEmbeddingProvider`` (downloads le modèle ST au 1er boot).

La seed et la config de clustering sont alignées sur la démo CLI (seed=42, k=2..8) pour
que les clusters affichés via API soient strictement identiques à ceux de
``scripts/run_lot2_demo.py``.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from skill_bridge.adapters.inbound.api.routes import (
    clusters,
    health,
    learners,
    recommendations,
)
from skill_bridge.adapters.inbound.api.state import PreloadedState
from skill_bridge.adapters.outbound.file_resource_repository import FileResourceRepository
from skill_bridge.adapters.outbound.file_skill_repository import FileSkillRepository
from skill_bridge.adapters.outbound.jsonl_loaders import (
    FileEnrichedTraceLoader,
    FileLearnersLoader,
)
from skill_bridge.application.clustering import ClusteringService
from skill_bridge.application.profiling import LearnerProfileBuilder
from skill_bridge.application.recommendation import RecommendationService
from skill_bridge.domain.ports import EmbeddingProvider

# Paths par défaut (mêmes que les scripts CLI).
REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_SKILLS = REPO_ROOT / "data" / "skills" / "numeracy_primary.json"
DEFAULT_ESCO_MAPPING = REPO_ROOT / "data" / "skills" / "esco_mapping.json"
DEFAULT_RESOURCES = REPO_ROOT / "data" / "seed" / "resources_catalog.json"
DEFAULT_ENRICHED = REPO_ROOT / "data" / "generated" / "enriched.jsonl"
DEFAULT_LEARNERS = REPO_ROOT / "data" / "generated" / "learners.jsonl"

# Cohérence avec scripts/run_lot2_demo.py et tests/unit/test_clustering.py.
DEFAULT_SEED = 42
DEFAULT_K_MIN = 2
DEFAULT_K_MAX = 8
PRECOMPUTED_TOP_N = 10  # /recommend renvoie au plus PRECOMPUTED_TOP_N.


def _build_state(
    embedder: EmbeddingProvider,
    skills_path: Path,
    esco_mapping_path: Path,
    resources_path: Path,
    enriched_path: Path,
    learners_path: Path,
    seed: int,
    k_min: int,
    k_max: int,
) -> PreloadedState:
    skills = FileSkillRepository(skills_path, esco_mapping_path).load_all()
    resources = FileResourceRepository(resources_path).load_all()
    learners = FileLearnersLoader(learners_path).load_all()
    enriched_traces = FileEnrichedTraceLoader(enriched_path).load_all()

    profiles = LearnerProfileBuilder(skills).build_all(learners, enriched_traces)
    domains = sorted({s.domain for s in skills})
    clustering = ClusteringService(domains=domains, k_min=k_min, k_max=k_max, seed=seed).fit(
        profiles
    )

    reco_service = RecommendationService(resources=resources, skills=skills, embedder=embedder)
    recommendations_by_learner = {
        profile.learner_id: reco_service.recommend(
            learner_id=profile.learner_id,
            profiles=profiles,
            assignments=clustering.assignments,
            all_traces=enriched_traces,
            top_n=PRECOMPUTED_TOP_N,
        )
        for profile in profiles
    }

    return PreloadedState(
        skills=skills,
        resources=resources,
        learners=learners,
        enriched_traces=enriched_traces,
        profiles=profiles,
        clustering=clustering,
        recommendations_by_learner=recommendations_by_learner,
    )


def create_app(
    embedder: EmbeddingProvider | None = None,
    skills_path: Path = DEFAULT_SKILLS,
    esco_mapping_path: Path = DEFAULT_ESCO_MAPPING,
    resources_path: Path = DEFAULT_RESOURCES,
    enriched_path: Path = DEFAULT_ENRICHED,
    learners_path: Path = DEFAULT_LEARNERS,
    seed: int = DEFAULT_SEED,
    k_min: int = DEFAULT_K_MIN,
    k_max: int = DEFAULT_K_MAX,
) -> FastAPI:
    """Factory. ``embedder=None`` => ``SentenceTransformersEmbeddingProvider`` (download ST)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        actual_embedder = embedder
        if actual_embedder is None:
            # Import paresseux : on n'instancie sentence-transformers qu'ici, jamais à l'import.
            from skill_bridge.adapters.outbound.sentence_transformers_provider import (
                SentenceTransformersEmbeddingProvider,
            )

            actual_embedder = SentenceTransformersEmbeddingProvider()

        app.state.preloaded = _build_state(
            embedder=actual_embedder,
            skills_path=skills_path,
            esco_mapping_path=esco_mapping_path,
            resources_path=resources_path,
            enriched_path=enriched_path,
            learners_path=learners_path,
            seed=seed,
            k_min=k_min,
            k_max=k_max,
        )
        yield

    app = FastAPI(
        title="SkillBridge API",
        version="0.1.0",
        summary="Data & AI provider pour le dataspace éducation & compétences",
        description=(
            "API lecture seule du provider SkillBridge — profils de maîtrise, "
            "clustering empirique et recommandations explicables. "
            "Tous les calculs sont préchargés au démarrage ; les requêtes sont des "
            "lookups en mémoire (cohérence + perf)."
        ),
        lifespan=lifespan,
    )

    app.include_router(health.router)
    app.include_router(learners.router)
    app.include_router(clusters.router)
    app.include_router(recommendations.router)

    return app
