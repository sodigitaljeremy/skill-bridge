"""Tests du profilage : moyennes / taux corrects et défaut neutre quand pas d'évidence."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from skill_bridge.application.enrichment import EnrichedTrace, EnrichmentService, ResolvedSkill
from skill_bridge.application.profiling import NEUTRAL_DEFAULT, LearnerProfileBuilder
from skill_bridge.application.trace_generation import ScenarioConfig, TraceGenerationService
from skill_bridge.domain.entities import Learner


def _learner(mbox: str = "abc123", grade: int = 3) -> Learner:
    return Learner(
        learner_id=uuid4(),
        display_name="Test",
        mbox_sha1sum=mbox,
        grade_level=grade,
        ability={"calcul_de_base": 0.5},
    )


def _trace(
    mbox: str,
    score: float | None,
    verb: str,
    domain: str = "calcul_de_base",
    resource_id: str = "EX001",
    skill_ids: tuple[str, ...] = ("addition_entiers",),
) -> EnrichedTrace:
    return EnrichedTrace(
        trace_id=str(uuid4()),
        learner_id=mbox,
        resource_id=resource_id,
        verb=verb,
        success=(verb == "passed") if score is not None else True,
        score=score,
        duration="PT60S",
        timestamp=datetime.now(UTC),
        skills=[
            ResolvedSkill(
                id=sid,
                preferred_label=sid,
                domain=domain,
                esco_uris=[],
            )
            for sid in skill_ids
        ],
    )


@pytest.mark.unit
def test_mean_score_and_success_rate_per_domain(sample_skills) -> None:
    learner = _learner()
    traces = [
        _trace(learner.mbox_sha1sum, 0.9, "passed"),
        _trace(learner.mbox_sha1sum, 0.6, "passed"),
        _trace(learner.mbox_sha1sum, 0.3, "failed"),
    ]
    profile = LearnerProfileBuilder(sample_skills).build_all([learner], traces)[0]

    assert profile.mean_score_per_domain["calcul_de_base"] == pytest.approx(0.6, abs=1e-9)
    assert profile.success_rate_per_domain["calcul_de_base"] == pytest.approx(2 / 3)


@pytest.mark.unit
def test_lessons_are_ignored_in_score_features(sample_skills) -> None:
    learner = _learner()
    traces = [
        _trace(learner.mbox_sha1sum, None, "completed"),  # leçon
        _trace(learner.mbox_sha1sum, 0.8, "passed"),
    ]
    profile = LearnerProfileBuilder(sample_skills).build_all([learner], traces)[0]
    assert profile.mean_score_per_domain["calcul_de_base"] == pytest.approx(0.8)


@pytest.mark.unit
def test_neutral_default_when_no_evidence_in_domain(sample_skills) -> None:
    learner = _learner()
    profile = LearnerProfileBuilder(sample_skills).build_all([learner], [])[0]
    for domain_score in profile.mean_score_per_domain.values():
        assert domain_score == NEUTRAL_DEFAULT
    for rate in profile.success_rate_per_domain.values():
        assert rate == NEUTRAL_DEFAULT


@pytest.mark.unit
def test_no_leakage_from_latent_ability(sample_skills, sample_resources) -> None:
    """Le profilage ne doit JAMAIS dépendre de ``Learner.ability`` — uniquement des traces."""
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    learners, traces = gen.generate(ScenarioConfig(n_learners=5, n_traces_mean=30, seed=42))
    enricher = EnrichmentService(resources=sample_resources, skills=sample_skills)
    enriched = [enricher.enrich(t) for t in traces]

    # Construire les profils avec des Learner identiques sauf une ability bidon.
    fake_learners = [
        Learner(
            learner_id=ln.learner_id,
            display_name=ln.display_name,
            mbox_sha1sum=ln.mbox_sha1sum,
            grade_level=ln.grade_level,
            ability={d: 0.01 for d in ln.ability},  # vérité latente bidon
            archetype=ln.archetype,
        )
        for ln in learners
    ]
    builder = LearnerProfileBuilder(sample_skills)
    real = builder.build_all(learners, enriched)
    fake = builder.build_all(fake_learners, enriched)
    for r, f in zip(real, fake, strict=True):
        assert r.mean_score_per_domain == f.mean_score_per_domain
