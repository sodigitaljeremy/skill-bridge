"""CsvTraceEncoder : produit une ligne par trace, colonnes attendues."""

import pytest

from skill_bridge.adapters.outbound.csv_trace_encoder import CSV_COLUMNS, CsvTraceEncoder
from skill_bridge.application.trace_generation import ScenarioConfig, TraceGenerationService


@pytest.mark.unit
def test_csv_columns_match_expected_schema() -> None:
    assert CSV_COLUMNS == (
        "learner_name",
        "resource_id",
        "resource_title",
        "verb",
        "score_scaled",
        "timestamp",
    )


@pytest.mark.unit
def test_encoder_emits_all_columns(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    _, traces = gen.generate(ScenarioConfig(n_learners=3, n_traces_mean=8, n_traces_std=0, seed=1))
    encoder = CsvTraceEncoder()
    for trace in traces:
        row = encoder.encode(trace)
        assert set(row) == set(CSV_COLUMNS)


@pytest.mark.unit
def test_lesson_trace_has_empty_score(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    _, traces = gen.generate(ScenarioConfig(n_learners=5, n_traces_mean=30, n_traces_std=0, seed=2))
    encoder = CsvTraceEncoder()
    lessons = [t for t in traces if t.object.definition.type.endswith("/lesson")]
    assert lessons, "Le scénario doit contenir des leçons"
    for trace in lessons:
        assert encoder.encode(trace)["score_scaled"] == ""


@pytest.mark.unit
def test_passed_trace_has_numeric_score(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    _, traces = gen.generate(
        ScenarioConfig(n_learners=10, n_traces_mean=30, n_traces_std=0, seed=3)
    )
    encoder = CsvTraceEncoder()
    scored = [t for t in traces if t.result and t.result.score is not None]
    assert scored
    for trace in scored:
        row = encoder.encode(trace)
        assert isinstance(row["score_scaled"], float)
        assert 0.0 <= row["score_scaled"] <= 1.0
        assert row["verb"] in {"passed", "failed"}
