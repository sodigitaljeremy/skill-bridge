"""Vérifie qu'un statement xAPI produit respecte la forme attendue (profils DASES)."""

import pytest

from skill_bridge.adapters.outbound.xapi_encoder import XApiJsonLinesEncoder
from skill_bridge.application.trace_generation import (
    ScenarioConfig,
    TraceGenerationService,
)


@pytest.mark.unit
def test_statement_has_required_xapi_fields(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    _, traces = gen.generate(ScenarioConfig(n_learners=3, n_traces_mean=10, n_traces_std=0, seed=1))
    statement = XApiJsonLinesEncoder().encode(traces[0])

    assert "id" in statement
    assert statement["actor"]["objectType"] == "Agent"
    assert len(statement["actor"]["mbox_sha1sum"]) == 40
    assert statement["verb"]["id"].startswith("http://adlnet.gov/expapi/verbs/")
    assert statement["object"]["objectType"] == "Activity"
    assert statement["object"]["id"].startswith("http://")
    assert "type" in statement["object"]["definition"]
    assert "timestamp" in statement


@pytest.mark.unit
def test_exercise_and_quiz_traces_carry_score(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    _, traces = gen.generate(
        ScenarioConfig(n_learners=10, n_traces_mean=20, n_traces_std=0, seed=2)
    )
    scored = [t for t in traces if t.result and t.result.score is not None]
    assert scored, "Au moins certains attempts devraient porter un score"
    for trace in scored:
        assert trace.result is not None and trace.result.score is not None
        assert 0.0 <= trace.result.score.scaled <= 1.0


@pytest.mark.unit
def test_lesson_traces_have_no_score(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    _, traces = gen.generate(
        ScenarioConfig(n_learners=10, n_traces_mean=30, n_traces_std=0, seed=3)
    )
    lesson_traces = [t for t in traces if t.object.definition.type.endswith("/lesson")]
    assert lesson_traces, "Le scénario doit contenir des leçons"
    for trace in lesson_traces:
        assert trace.verb.id.endswith("/completed")
        assert trace.result is not None
        assert trace.result.score is None
        assert trace.result.completion is True
