"""Route /recommend/{learner_id} — lookup dans le cache top-10 préchargé."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request

from skill_bridge.adapters.inbound.api.schemas import RecommendationOut
from skill_bridge.adapters.inbound.api.state import PreloadedState

MAX_TOP_N = 10
router = APIRouter(tags=["recommendations"])


@router.get("/recommend/{learner_id}", response_model=list[RecommendationOut])
def get_recommendations(
    learner_id: UUID,
    request: Request,
    n: int = Query(default=5, ge=1, le=MAX_TOP_N),
) -> list[RecommendationOut]:
    state: PreloadedState = request.app.state.preloaded
    cached = state.recommendations_by_learner.get(learner_id)
    if cached is None:
        raise HTTPException(status_code=404, detail=f"Unknown learner_id {learner_id}")
    return [
        RecommendationOut(
            resource_id=r.resource_id,
            title=r.title,
            score=r.score,
            weak_skills_targeted=list(r.weak_skills_targeted),
            grade_distance=r.grade_distance,
            semantic_similarity=r.semantic_similarity,
            cluster_success_rate=r.cluster_success_rate,
            explanation=r.explanation,
        )
        for r in cached[:n]
    ]
