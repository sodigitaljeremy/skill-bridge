"""Route /clusters — silhouette par k + clusters nommés + assignations."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from skill_bridge.adapters.inbound.api.schemas import (
    AssignedClusterOut,
    ClusteringOut,
    ClusterOut,
)
from skill_bridge.adapters.inbound.api.state import PreloadedState

router = APIRouter(tags=["clusters"])


@router.get("/clusters", response_model=ClusteringOut)
def get_clusters(request: Request) -> ClusteringOut:
    state: PreloadedState = request.app.state.preloaded
    clustering = state.clustering
    return ClusteringOut(
        k=clustering.k,
        silhouette=clustering.silhouette,
        silhouette_by_k=clustering.silhouette_by_k,
        clusters=[
            ClusterOut(
                cluster_id=cid,
                label=clustering.cluster_labels[cid],
                size=clustering.cluster_sizes[cid],
                centroid_per_domain=dict(clustering.centroids_per_domain[cid]),
            )
            for cid in sorted(clustering.cluster_labels)
        ],
    )


@router.get("/clusters/assignment/{learner_id}", response_model=AssignedClusterOut)
def get_assignment(learner_id: UUID, request: Request) -> AssignedClusterOut:
    state: PreloadedState = request.app.state.preloaded
    assignment = next((a for a in state.clustering.assignments if a.learner_id == learner_id), None)
    if assignment is None:
        raise HTTPException(status_code=404, detail=f"Unknown learner_id {learner_id}")
    return AssignedClusterOut(
        learner_id=assignment.learner_id,
        cluster_id=assignment.cluster_id,
        cluster_label=assignment.cluster_label,
        distance_to_centroid=assignment.distance_to_centroid,
    )
