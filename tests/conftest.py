"""Fixtures partagées : chargement des seeds depuis ``data/``."""

from pathlib import Path

import pytest

from skill_bridge.adapters.outbound.file_resource_repository import FileResourceRepository
from skill_bridge.adapters.outbound.file_skill_repository import FileSkillRepository
from skill_bridge.domain.entities import LearningResource, Skill

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


@pytest.fixture(scope="session")
def sample_skills() -> list[Skill]:
    return FileSkillRepository(
        DATA_DIR / "skills" / "numeracy_primary.json",
        DATA_DIR / "skills" / "esco_mapping.json",
    ).load_all()


@pytest.fixture(scope="session")
def sample_resources() -> list[LearningResource]:
    return FileResourceRepository(DATA_DIR / "seed" / "resources_catalog.json").load_all()
