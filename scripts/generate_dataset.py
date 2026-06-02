#!/usr/bin/env python3
"""Lot 1 — pipeline : seeds → traces xAPI → traces enrichies (JSONL) + rapport.

Lot 3 — flag optionnel ``--via-lrc URL`` : convertit en plus un échantillon (Léa +
1 apprenant par archétype) via le LRC réel sur cette URL et écrit
``data/generated/traces_via_lrc.jsonl``. Le dataset principal reste en xapi-direct.
"""

import argparse
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path

from skill_bridge.adapters.outbound.csv_trace_encoder import CSV_COLUMNS, CsvTraceEncoder
from skill_bridge.adapters.outbound.csv_writer import write_csv
from skill_bridge.adapters.outbound.dataset_writer import write_jsonl
from skill_bridge.adapters.outbound.file_resource_repository import FileResourceRepository
from skill_bridge.adapters.outbound.file_skill_repository import FileSkillRepository
from skill_bridge.adapters.outbound.lrc_http_converter import LrcConverterError, LrcHttpConverter
from skill_bridge.adapters.outbound.xapi_encoder import XApiJsonLinesEncoder
from skill_bridge.application.enrichment import EnrichmentService
from skill_bridge.application.trace_generation import (
    LEA_LEARNER_ID,
    ScenarioConfig,
    TraceGenerationService,
    compute_domain_coverage,
)
from skill_bridge.domain.entities import Learner, LearningTrace

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SKILLS = REPO_ROOT / "data" / "skills" / "numeracy_primary.json"
DEFAULT_MAPPING = REPO_ROOT / "data" / "skills" / "esco_mapping.json"
DEFAULT_RESOURCES = REPO_ROOT / "data" / "seed" / "resources_catalog.json"
DEFAULT_LRC_MAPPING = REPO_ROOT / "data" / "seed" / "lrc_mapping_mathia.yml"
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
    p.add_argument(
        "--via-lrc",
        type=str,
        default=None,
        metavar="URL",
        help=(
            "Si fourni (ex: http://localhost:8080), convertit aussi un échantillon "
            "(Léa + 1 apprenant par archetype) via /convert_custom du LRC. "
            "Écrit data/generated/traces_via_lrc.jsonl."
        ),
    )
    p.add_argument(
        "--lrc-mapping-path",
        type=Path,
        default=DEFAULT_LRC_MAPPING,
        help="Mapping YAML CSV->xAPI passé au LRC.",
    )
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
    # learners.jsonl = vérité-terrain (archetype, ability, grade). Émis pour le sanity-check
    # du clustering du Lot 2 et le picking d'apprenants démo — NE PAS utiliser comme feature.
    n_learners_written = write_jsonl(
        (_learner_to_groundtruth_dict(learner) for learner in learners),
        args.output_dir / "learners.jsonl",
    )

    _print_report(
        learners,
        traces,
        resources,
        skills,
        n_traces,
        n_enriched,
        n_learners_written,
        args.output_dir,
    )

    if args.via_lrc:
        _run_lrc_sample(
            learners=learners,
            traces=traces,
            output_dir=args.output_dir,
            lrc_url=args.via_lrc,
            mapping_path=args.lrc_mapping_path,
        )


def _run_lrc_sample(
    learners: list[Learner],
    traces: list[LearningTrace],
    output_dir: Path,
    lrc_url: str,
    mapping_path: Path,
) -> None:
    print()
    print(f"=== Échantillon via LRC ({lrc_url}) ===")

    sample_learners = _pick_lrc_sample(learners)
    sample_mboxes = {ln.mbox_sha1sum for ln in sample_learners}
    sample_traces = [t for t in traces if t.actor.mbox_sha1sum in sample_mboxes]
    print(
        f"Apprenants : {len(sample_learners)} (Léa + 1 par archetype distinct). "
        f"Traces à envoyer : {len(sample_traces)}."
    )

    csv_path = output_dir / "sample_mathia.csv"
    encoder = CsvTraceEncoder()
    n_csv = write_csv(
        (encoder.encode(t) for t in sample_traces),
        csv_path,
        CSV_COLUMNS,
    )
    print(f"Écrit {n_csv} lignes dans {csv_path}.")

    converter = LrcHttpConverter(base_url=lrc_url)
    if not converter.ping():
        print(f"⚠️  Le LRC ne répond pas sur {lrc_url}/docs — abandon de l'échantillon.")
        return

    out_path = output_dir / "traces_via_lrc.jsonl"
    try:
        n_out, profile_stats = _stream_lrc_to_jsonl(
            converter.convert(csv_path, mapping_path),
            out_path,
        )
    except LrcConverterError as e:
        print(f"⚠️  LRC a refusé la conversion : {e}")
        return

    print(f"Reçu {n_out} statements xAPI depuis le LRC -> {out_path}.")
    if profile_stats:
        print(
            "Profils DASES détectés : "
            + ", ".join(f"{k}={v}" for k, v in sorted(profile_stats.items()))
        )
    else:
        print("Profils DASES : aucun (meta absent du flux /convert_custom).")


def _pick_lrc_sample(learners: list[Learner]) -> list[Learner]:
    by_archetype: dict[str, Learner] = {}
    lea = next((x for x in learners if x.learner_id == LEA_LEARNER_ID), None)
    if lea is not None and lea.archetype:
        by_archetype[lea.archetype] = lea
    for learner in learners:
        if learner.learner_id == LEA_LEARNER_ID:
            continue
        if learner.archetype and learner.archetype not in by_archetype:
            by_archetype[learner.archetype] = learner
    # Léa d'abord (si présente), puis les autres dans l'ordre des archetypes rencontrés.
    ordered: list[Learner] = []
    if lea is not None:
        ordered.append(lea)
    for learner in by_archetype.values():
        if lea is not None and learner.learner_id == lea.learner_id:
            continue
        ordered.append(learner)
    return ordered


def _stream_lrc_to_jsonl(statements: Iterable[dict], path: Path) -> tuple[int, dict[str, int]]:
    profile_stats: dict[str, int] = defaultdict(int)
    n = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    import json as _json

    with path.open("w", encoding="utf-8") as f:
        for stmt in statements:
            meta = stmt.get("meta") if isinstance(stmt, dict) else None
            if isinstance(meta, dict):
                profile = meta.get("profile")
                if profile:
                    profile_stats[str(profile)] += 1
            f.write(_json.dumps(stmt, ensure_ascii=False))
            f.write("\n")
            n += 1
    return n, dict(profile_stats)


def _learner_to_groundtruth_dict(learner) -> dict:
    return {
        "learner_id": str(learner.learner_id),
        "mbox_sha1sum": learner.mbox_sha1sum,
        "display_name": learner.display_name,
        "grade_level": learner.grade_level,
        "archetype": learner.archetype,
        "ability": dict(learner.ability),
    }


def _print_report(
    learners,
    traces,
    resources,
    skills,
    n_traces,
    n_enriched,
    n_learners_written,
    output_dir,
) -> None:
    print(
        f"OK — {len(learners)} apprenants ({n_learners_written} dans learners.jsonl), "
        f"{n_traces} traces xAPI, {n_enriched} traces enrichies dans {output_dir}/."
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
