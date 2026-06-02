"""Stub LRC : roundtrip CSV (issu de CsvTraceEncoder) -> statements xAPI minimaux."""

from pathlib import Path

import pytest

from skill_bridge.adapters.outbound.csv_trace_encoder import CSV_COLUMNS, CsvTraceEncoder
from skill_bridge.adapters.outbound.csv_writer import write_csv
from skill_bridge.adapters.outbound.stub_lrc_converter import StubLrcConverter
from skill_bridge.application.trace_generation import ScenarioConfig, TraceGenerationService


@pytest.fixture
def sample_csv(tmp_path: Path, sample_skills, sample_resources) -> Path:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    _, traces = gen.generate(ScenarioConfig(n_learners=2, n_traces_mean=12, n_traces_std=0, seed=7))
    csv_path = tmp_path / "sample.csv"
    encoder = CsvTraceEncoder()
    write_csv((encoder.encode(t) for t in traces), csv_path, CSV_COLUMNS)
    return csv_path


@pytest.mark.unit
def test_stub_yields_xapi_minimal_shape(tmp_path: Path, sample_csv: Path) -> None:
    mapping = tmp_path / "mapping.yml"
    mapping.write_text("ignored", encoding="utf-8")
    stub = StubLrcConverter()
    statements = list(stub.convert(sample_csv, mapping))

    assert statements
    for stmt in statements:
        assert stmt["actor"]["account"]["homePage"].startswith("https://")
        assert stmt["object"]["id"].startswith("https://mathia.example.com/resource/")
        assert stmt["verb"]["id"].startswith("http://adlnet.gov/expapi/verbs/")
        assert "timestamp" in stmt


@pytest.mark.unit
def test_stub_passes_scored_attempts_through(tmp_path: Path, sample_csv: Path) -> None:
    mapping = tmp_path / "m.yml"
    mapping.write_text("ignored", encoding="utf-8")
    stub = StubLrcConverter()
    statements = list(stub.convert(sample_csv, mapping))

    scored = [s for s in statements if "result" in s]
    assert scored, "Au moins une trace scorée attendue"
    for s in scored:
        assert 0.0 <= s["result"]["score"]["scaled"] <= 1.0


@pytest.mark.unit
def test_stub_lesson_traces_have_no_score(tmp_path: Path, sample_csv: Path) -> None:
    mapping = tmp_path / "m.yml"
    mapping.write_text("ignored", encoding="utf-8")
    stub = StubLrcConverter()
    statements = list(stub.convert(sample_csv, mapping))
    # Les leçons ont verb=completed et pas de result.score
    lessons = [s for s in statements if s["verb"]["id"].endswith("/completed")]
    assert lessons
    for s in lessons:
        assert "result" not in s or "score" not in s.get("result", {})
