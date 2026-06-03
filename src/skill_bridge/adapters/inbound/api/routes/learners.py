"""Routes /learners et /profile/{learner_id}."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from skill_bridge.adapters.inbound.api.schemas import LearnerOut, ProfileOut
from skill_bridge.adapters.inbound.api.state import PreloadedState

router = APIRouter(tags=["learners"])


@router.get("/learners", response_model=list[LearnerOut])
def list_learners(request: Request) -> list[LearnerOut]:
    state: PreloadedState = request.app.state.preloaded
    return [
        LearnerOut(
            learner_id=learner.learner_id,
            display_name=learner.display_name,
            grade_level=learner.grade_level,
        )
        for learner in state.learners
    ]


@router.get("/profile/{learner_id}", response_model=ProfileOut)
def get_profile(learner_id: UUID, request: Request) -> ProfileOut:
    state: PreloadedState = request.app.state.preloaded
    profile = next((p for p in state.profiles if p.learner_id == learner_id), None)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Unknown learner_id {learner_id}")
    return ProfileOut(
        learner_id=profile.learner_id,
        grade_level=profile.grade_level,
        n_traces=profile.n_traces,
        mean_score_per_domain=dict(profile.mean_score_per_domain),
        success_rate_per_domain=dict(profile.success_rate_per_domain),
    )
