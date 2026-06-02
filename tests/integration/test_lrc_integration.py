"""Test d'intégration contre le LRC réel.

Skip automatique si :
  - la variable d'env ``LRC_URL`` n'est pas posée, OU
  - le service ne répond pas à ``GET /docs``.

Sinon : POST /convert_custom avec un échantillon CSV maison et le mapping versionné,
vérifie la conformité xAPI minimale du flux retourné.
"""

import os
from pathlib import Path

import pytest

from skill_bridge.adapters.outbound.csv_trace_encoder import CSV_COLUMNS, CsvTraceEncoder
from skill_bridge.adapters.outbound.csv_writer import write_csv
from skill_bridge.adapters.outbound.lrc_http_converter import LrcHttpConverter
from skill_bridge.application.trace_generation import ScenarioConfig, TraceGenerationService

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MAPPING_PATH = REPO_ROOT / "data" / "seed" / "lrc_mapping_mathia.yml"


def _lrc_url() -> str | None:
    return os.environ.get("LRC_URL")


@pytest.mark.integration
def test_lrc_responds_to_docs() -> None:
    url = _lrc_url()
    if not url:
        pytest.skip("LRC_URL non défini — démarrer le LRC et exporter LRC_URL pour activer.")
    converter = LrcHttpConverter(base_url=url)
    if not converter.ping():
        pytest.skip(f"LRC à {url} ne répond pas — voir docs/lrc_runbook.md.")


@pytest.mark.integration
def test_lrc_convert_custom_roundtrip(tmp_path: Path, sample_skills, sample_resources) -> None:
    url = _lrc_url()
    if not url:
        pytest.skip("LRC_URL non défini.")
    converter = LrcHttpConverter(base_url=url)
    if not converter.ping():
        pytest.skip(f"LRC à {url} ne répond pas.")

    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    _, traces = gen.generate(
        ScenarioConfig(n_learners=2, n_traces_mean=10, n_traces_std=0, seed=42)
    )

    csv_path = tmp_path / "sample.csv"
    encoder = CsvTraceEncoder()
    write_csv((encoder.encode(t) for t in traces), csv_path, CSV_COLUMNS)

    statements = list(converter.convert(csv_path, MAPPING_PATH))
    assert statements, "Le LRC doit renvoyer au moins un statement"

    for stmt in statements:
        assert "actor" in stmt
        assert "verb" in stmt
        assert stmt["verb"]["id"].startswith("http://adlnet.gov/expapi/verbs/")
        assert "object" in stmt
        assert stmt["object"]["id"].startswith("https://mathia.example.com/resource/")
        assert "timestamp" in stmt
