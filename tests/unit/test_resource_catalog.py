"""Cohérence du catalogue de ressources et du référentiel maison."""

import pytest


@pytest.mark.unit
def test_each_resource_has_at_least_one_skill(sample_resources) -> None:
    for resource in sample_resources:
        assert resource.skill_ids, f"{resource.resource_id} n'a aucune compétence"


@pytest.mark.unit
def test_every_resource_skill_id_exists_in_referential(sample_resources, sample_skills) -> None:
    known = {s.id for s in sample_skills}
    for resource in sample_resources:
        for sid in resource.skill_ids:
            assert sid in known, f"Skill {sid!r} de {resource.resource_id!r} absent du référentiel"


@pytest.mark.unit
def test_each_skill_has_a_domain(sample_skills) -> None:
    for skill in sample_skills:
        assert skill.domain, f"Skill {skill.id} sans domaine"


@pytest.mark.unit
def test_every_skill_is_used_by_at_least_one_resource(sample_resources, sample_skills) -> None:
    used = {sid for r in sample_resources for sid in r.skill_ids}
    unused = [s.id for s in sample_skills if s.id not in used]
    assert not unused, f"Compétences sans ressource : {unused}"


@pytest.mark.unit
def test_referential_has_at_least_one_esco_mapping(sample_skills) -> None:
    with_esco = [s for s in sample_skills if s.esco_uris]
    assert with_esco, "Au moins une compétence devrait porter un mapping ESCO"
