#!/usr/bin/env python3
"""Lot 2 — démo : clustering par silhouette + profil + reco explicables.

Entrée : data/generated/enriched.jsonl (+ seeds skills + resources).
learners.jsonl (vérité-terrain) est utilisé UNIQUEMENT pour :
  - le sanity-check archetype↔cluster
  - le picking d'apprenants démo (1 par archétype distinct, dont Léa)
Aucune feature de clustering ne le lit.
"""

import argparse
from collections import Counter
from pathlib import Path

from skill_bridge.adapters.outbound.file_resource_repository import FileResourceRepository
from skill_bridge.adapters.outbound.file_skill_repository import FileSkillRepository
from skill_bridge.adapters.outbound.jsonl_loaders import (
    FileEnrichedTraceLoader,
    FileLearnersLoader,
)
from skill_bridge.adapters.outbound.sentence_transformers_provider import (
    SentenceTransformersEmbeddingProvider,
)
from skill_bridge.application.clustering import ClusteringService
from skill_bridge.application.profiling import LearnerProfileBuilder
from skill_bridge.application.recommendation import RecommendationService

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--enriched", type=Path, default=DATA / "generated" / "enriched.jsonl")
    p.add_argument("--learners", type=Path, default=DATA / "generated" / "learners.jsonl")
    p.add_argument("--skills", type=Path, default=DATA / "skills" / "numeracy_primary.json")
    p.add_argument("--mapping", type=Path, default=DATA / "skills" / "esco_mapping.json")
    p.add_argument("--resources", type=Path, default=DATA / "seed" / "resources_catalog.json")
    p.add_argument("--top-n", type=int, default=5, help="Nombre de recos par apprenant.")
    p.add_argument(
        "--show",
        type=str,
        nargs="*",
        default=None,
        help="display_name d'apprenants à afficher (sinon : Léa + 1 par archetype distinct).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    skills = FileSkillRepository(args.skills, args.mapping).load_all()
    resources = FileResourceRepository(args.resources).load_all()
    learners = FileLearnersLoader(args.learners).load_all()
    enriched = FileEnrichedTraceLoader(args.enriched).load_all()
    print(
        f"Chargé : {len(skills)} skills, {len(resources)} ressources, "
        f"{len(learners)} apprenants, {len(enriched)} traces enrichies."
    )

    # --- profilage ---
    profiles = LearnerProfileBuilder(skills).build_all(learners, enriched)
    domains = sorted({s.domain for s in skills})
    print(f"\n== Profilage ({len(profiles)} apprenants) ==")
    n = len(domains)
    print(f"Features : {2 * n} dim. (mean_score sur {n} + success_rate sur {n})")

    # --- clustering ---
    print("\n== Sélection de k par silhouette ==")
    clustering = ClusteringService(domains=domains, k_min=2, k_max=8, seed=42).fit(profiles)
    for k, score in clustering.silhouette_by_k.items():
        marker = " ★ best" if k == clustering.k else ""
        print(f"  k={k} → silhouette={score:.3f}{marker}")

    print(f"\n== Clusters (k={clustering.k}, silhouette={clustering.silhouette:.3f}) ==")
    for cid in sorted(clustering.cluster_labels):
        size = clustering.cluster_sizes[cid]
        label = clustering.cluster_labels[cid]
        centroid = clustering.centroids_per_domain[cid]
        print(f"  C{cid} ({size:>3} apprenants) — « {label} »")
        for domain in domains:
            print(f"      {domain:<24} {centroid[domain]:.2f}")

    # --- sanity-check archétype ↔ cluster ---
    archetype_by_mbox = {x.mbox_sha1sum: x.archetype for x in learners if x.archetype}
    cluster_by_mbox = {
        p.mbox_sha1sum: a.cluster_id for p, a in zip(profiles, clustering.assignments, strict=True)
    }
    cluster_archetype_counts: dict[int, Counter[str]] = {
        cid: Counter() for cid in clustering.cluster_labels
    }
    for mbox, archetype in archetype_by_mbox.items():
        cid = cluster_by_mbox.get(mbox)
        if cid is not None:
            cluster_archetype_counts[cid][archetype] += 1

    print("\n== Sanity (archétypes par cluster) ==")
    for cid, counts in sorted(cluster_archetype_counts.items()):
        if not counts:
            continue
        total = sum(counts.values())
        dominant, dominant_n = counts.most_common(1)[0]
        print(
            f"  C{cid} : dominant={dominant} "
            f"({dominant_n}/{total} = {100 * dominant_n / total:.0f}%) "
            f"| détail : {dict(counts)}"
        )

    # --- recommandations ---
    print("\n== Recommandations ==")
    embedder = SentenceTransformersEmbeddingProvider()
    print(f"(embeddings : dim {embedder.dimension})")
    reco = RecommendationService(resources=resources, skills=skills, embedder=embedder)

    if args.show:
        targets = [p for p in profiles if _learner_name(p.learner_id, learners) in args.show]
    else:
        targets = _pick_demo_learners(profiles, learners, archetype_by_mbox)

    for profile in targets:
        name = _learner_name(profile.learner_id, learners)
        assignment = next(a for a in clustering.assignments if a.learner_id == profile.learner_id)
        archetype = archetype_by_mbox.get(profile.mbox_sha1sum, "?")
        print(
            f"\n--- {name} — cluster C{assignment.cluster_id} "
            f"« {assignment.cluster_label} » (archetype réel: {archetype}) ---"
        )
        print("Profil de maîtrise observé (mean_score / success_rate par domaine) :")
        for domain in domains:
            ms = profile.mean_score_per_domain[domain]
            sr = profile.success_rate_per_domain[domain]
            flag = " ✓ fort" if ms >= 0.70 else " ✗ faible" if ms < 0.55 else ""
            print(f"   {domain:<24} {ms:.2f} / {sr:.2f}{flag}")

        recos = reco.recommend(
            learner_id=profile.learner_id,
            profiles=profiles,
            assignments=clustering.assignments,
            all_traces=enriched,
            top_n=args.top_n,
        )
        print(f"\nTop-{args.top_n} recommandations :")
        for i, r in enumerate(recos, 1):
            print(f"  {i}. {r.resource_id} « {r.title} »   score {r.score:.3f}")
            print(f"     → {r.explanation}")


def _learner_name(learner_id, learners) -> str:
    for x in learners:
        if x.learner_id == learner_id:
            return x.display_name
    return str(learner_id)


def _pick_demo_learners(profiles, learners, archetype_by_mbox):
    """Léa + 1 apprenant par archétype distinct (idéalement représentatif)."""
    mbox_to_profile = {p.mbox_sha1sum: p for p in profiles}
    seen_archetypes: set[str] = set()
    picked: list = []
    # Léa d'abord
    for x in learners:
        if x.display_name == "Léa Martin":
            picked.append(mbox_to_profile[x.mbox_sha1sum])
            if x.archetype:
                seen_archetypes.add(x.archetype)
            break
    # Un autre apprenant par archétype non encore vu
    for x in learners:
        if x.display_name == "Léa Martin":
            continue
        archetype = archetype_by_mbox.get(x.mbox_sha1sum)
        if archetype and archetype not in seen_archetypes:
            picked.append(mbox_to_profile[x.mbox_sha1sum])
            seen_archetypes.add(archetype)
        if len(picked) >= 3:
            break
    return picked


if __name__ == "__main__":
    main()
