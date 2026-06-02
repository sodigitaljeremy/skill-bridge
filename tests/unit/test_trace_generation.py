"""Génération : déterminisme, volume, présence de Léa, distribution des verbes."""

import pytest

from skill_bridge.application.trace_generation import (
    LEA_LEARNER_ID,
    ScenarioConfig,
    TraceGenerationService,
)


@pytest.mark.unit
def test_generation_is_deterministic_with_same_seed(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    config = ScenarioConfig(n_learners=5, n_traces_mean=12, n_traces_std=2, seed=42)
    learners_a, traces_a = gen.generate(config)
    learners_b, traces_b = gen.generate(config)

    assert [x.learner_id for x in learners_a] == [x.learner_id for x in learners_b]
    assert len(traces_a) == len(traces_b)
    assert [t.object.id for t in traces_a] == [t.object.id for t in traces_b]
    assert [t.verb.id for t in traces_a] == [t.verb.id for t in traces_b]
    assert [t.id for t in traces_a] == [t.id for t in traces_b]


@pytest.mark.unit
def test_lea_is_present_with_expected_profile(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    learners, _ = gen.generate(ScenarioConfig(n_learners=10, seed=7))
    lea = next((x for x in learners if x.learner_id == LEA_LEARNER_ID), None)
    assert lea is not None, "Léa doit toujours figurer dans les apprenants"
    assert lea.display_name == "Léa Martin"
    assert lea.ability["calcul_de_base"] > lea.ability["geometrie_mesures"], (
        "Léa : forte en calcul, faible en géométrie (profil persona)"
    )


@pytest.mark.unit
def test_volume_matches_config(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    config = ScenarioConfig(n_learners=20, n_traces_mean=40, n_traces_std=0, seed=3)
    learners, traces = gen.generate(config)
    assert len(learners) == 20
    assert len(traces) == 20 * 40  # std=0 -> exactement mean par apprenant


@pytest.mark.unit
def test_ability_vector_covers_all_domains(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    learners, _ = gen.generate(ScenarioConfig(n_learners=5, seed=11))
    expected_domains = {s.domain for s in sample_skills}
    for learner in learners:
        assert set(learner.ability) == expected_domains, (
            f"Vecteur d'ability incomplet pour {learner.display_name}"
        )
        for value in learner.ability.values():
            assert 0.3 <= value <= 0.95


@pytest.mark.unit
def test_lessons_use_completed_verb(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    _, traces = gen.generate(ScenarioConfig(n_learners=20, n_traces_mean=30, seed=9))
    lesson_traces = [t for t in traces if t.object.definition.type.endswith("/lesson")]
    assert lesson_traces, "Le scénario doit produire des traces de leçon"
    for trace in lesson_traces:
        assert trace.verb.id.endswith("/completed")


@pytest.mark.unit
def test_traces_are_chronologically_ordered_per_learner(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    _, traces = gen.generate(ScenarioConfig(n_learners=3, n_traces_mean=20, seed=13))
    by_learner: dict[str, list] = {}
    for trace in traces:
        by_learner.setdefault(trace.actor.mbox_sha1sum, []).append(trace.timestamp)
    for timestamps in by_learner.values():
        assert timestamps == sorted(timestamps)
