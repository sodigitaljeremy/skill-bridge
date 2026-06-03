"""Route /health — sanity check de préchargement."""

from fastapi import APIRouter, Request

from skill_bridge.adapters.inbound.api.schemas import HealthOut
from skill_bridge.adapters.inbound.api.state import PreloadedState

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthOut)
def get_health(request: Request) -> HealthOut:
    state: PreloadedState = request.app.state.preloaded
    return HealthOut(
        status="ok",
        preloaded=True,
        n_learners=len(state.learners),
        n_resources=len(state.resources),
        n_skills=len(state.skills),
        n_clusters=state.clustering.k,
    )
