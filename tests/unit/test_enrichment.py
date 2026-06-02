"""Enrichissement : chaque trace résout les compétences exactes de sa ressource."""

import pytest

from skill_bridge.application.enrichment import EnrichmentService
from skill_bridge.application.trace_generation import (
    ScenarioConfig,
    TraceGenerationService,
)


@pytest.mark.unit
def test_each_enriched_trace_has_at_least_one_skill(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    _, traces = gen.generate(ScenarioConfig(n_learners=10, n_traces_mean=20, seed=5))
    enricher = EnrichmentService(resources=sample_resources, skills=sample_skills)

    for trace in traces:
        enriched = enricher.enrich(trace)
        assert enriched.skills, f"Trace {enriched.trace_id} sans compétence résolue"


@pytest.mark.unit
def test_enriched_skills_match_resource_skills(sample_skills, sample_resources) -> None:
    resource_by_id = {r.resource_id: r for r in sample_resources}
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    _, traces = gen.generate(ScenarioConfig(n_learners=8, n_traces_mean=15, seed=11))
    enricher = EnrichmentService(resources=sample_resources, skills=sample_skills)

    for trace in traces:
        enriched = enricher.enrich(trace)
        resource = resource_by_id[enriched.resource_id]
        assert {s.id for s in enriched.skills} == set(resource.skill_ids)


@pytest.mark.unit
def test_esco_mapping_propagates_through_enrichment(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    _, traces = gen.generate(ScenarioConfig(n_learners=20, n_traces_mean=30, seed=13))
    enricher = EnrichmentService(resources=sample_resources, skills=sample_skills)

    seen_esco = any(any(s.esco_uris for s in enricher.enrich(t).skills) for t in traces)
    assert seen_esco, "Au moins une trace enrichie doit porter une URI ESCO"


@pytest.mark.unit
def test_enrichment_serialization_roundtrip(sample_skills, sample_resources) -> None:
    gen = TraceGenerationService(skills=sample_skills, resources=sample_resources)
    _, traces = gen.generate(ScenarioConfig(n_learners=2, n_traces_mean=5, seed=17))
    enricher = EnrichmentService(resources=sample_resources, skills=sample_skills)

    payload = enricher.enrich(traces[0]).to_dict()
    assert isinstance(payload["timestamp"], str)
    assert isinstance(payload["skills"], list)
    assert all(isinstance(s["esco_uris"], list) for s in payload["skills"])
