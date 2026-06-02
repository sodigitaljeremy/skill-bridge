#!/usr/bin/env python3
"""Lot 1 — pipeline : seeds → traces xAPI → traces enrichies (JSONL) + rapport."""

import argparse
from collections import Counter
from pathlib import Path

from skill_bridge.adapters.outbound.dataset_writer import write_jsonl
from skill_bridge.adapters.outbound.file_resource_repository import FileResourceRepository
from skill_bridge.adapters.outbound.file_skill_repository import FileSkillRepository
from skill_bridge.adapters.outbound.xapi_encoder import XApiJsonLinesEncoder
from skill_bridge.application.enrichment import EnrichmentService
from skill_bridge.application.trace_generation import (
    ScenarioConfig,
    TraceGenerationService,
    compute_domain_coverage,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SKILLS = REPO_ROOT / "data" / "skills" / "numeracy_primary.json"
DEFAULT_MAPPING = REPO_ROOT / "data" / "skills" / "esco_mapping.json"
DEFAULT_RESOURCES = REPO_ROOT / "data" / "seed" / "resources_catalog.json"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "generated"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--learners", type=int, default=100, help="Nombre d'apprenants (Léa incluse).")
    p.add_argument(
        "--traces-mean", type=int, default=60, help="Nombre moyen de traces par apprenant."
    )
    p.add_argument("--traces-std", type=int, default=15, help="Écart-type du nb de traces.")
    p.add_argument("--window-days", type=int, default=90, help="Étendue temporelle (jours).")
    p.add_argument("--seed", type=int, default=42, help="Seed RNG pour la reproductibilité.")
    p.add_argument("--skills-path", type=Path, default=DEFAULT_SKILLS)
    p.add_argument("--mapping-path", type=Path, default=DEFAULT_MAPPING)
    p.add_argument("--resources-path", type=Path, default=DEFAULT_RESOURCES)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return p.parse_args()


def main() -> None:
    args = parse_args()

    skills = FileSkillRepository(args.skills_path, args.mapping_path).load_all()
    resources = FileResourceRepository(args.resources_path).load_all()

    config = ScenarioConfig(
        n_learners=args.learners,
        n_traces_mean=args.traces_mean,
        n_traces_std=args.traces_std,
        time_window_days=args.window_days,
        seed=args.seed,
    )

    generator = TraceGenerationService(skills=skills, resources=resources)
    learners, traces = generator.generate(config)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    encoder = XApiJsonLinesEncoder()
    enricher = EnrichmentService(resources=resources, skills=skills)

    n_traces = write_jsonl(
        (encoder.encode(t) for t in traces),
        args.output_dir / "traces.jsonl",
    )
    n_enriched = write_jsonl(
        (enricher.enrich(t).to_dict() for t in traces),
        args.output_dir / "enriched.jsonl",
    )

    _print_report(learners, traces, resources, skills, n_traces, n_enriched, args.output_dir)


def _print_report(
    learners,
    traces,
    resources,
    skills,
    n_traces,
    n_enriched,
    output_dir,
) -> None:
    print(
        f"OK — {len(learners)} apprenants, {n_traces} traces xAPI, "
        f"{n_enriched} traces enrichies dans {output_dir}/."
    )
    print()
    print("=== Stats ===")

    verb_counts = Counter(t.verb.id.rsplit("/", 1)[-1] for t in traces)
    print("Verbes : " + ", ".join(f"{v}={c}" for v, c in sorted(verb_counts.items())))

    archetype_counts = Counter(learner.archetype for learner in learners if learner.archetype)
    print("Archetypes : " + ", ".join(f"{a}={c}" for a, c in sorted(archetype_counts.items())))

    coverages = compute_domain_coverage(learners, traces, resources, skills)
    print()
    print(f"{'Domaine':<24} {'Total':>7} {'Min':>5} {'Méd':>5} {'Max':>5}")
    print("-" * 50)
    for cov in coverages:
        print(
            f"{cov.domain:<24} "
            f"{cov.total:>7} {cov.per_learner_min:>5} "
            f"{cov.per_learner_median:>5} {cov.per_learner_max:>5}"
        )


if __name__ == "__main__":
    main()
