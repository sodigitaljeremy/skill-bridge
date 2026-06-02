"""Charge le catalogue de ressources éducatives depuis JSON local."""

import json
from pathlib import Path

from skill_bridge.domain.entities import LearningResource
from skill_bridge.domain.enums import ResourceType


class FileResourceRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load_all(self) -> list[LearningResource]:
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        return [
            LearningResource(
                resource_id=r["resource_id"],
                title=r["title"],
                type=ResourceType(r["type"]),
                grade_level=r["grade_level"],
                estimated_duration_s=r["estimated_duration_s"],
                skill_ids=r["skill_ids"],
            )
            for r in raw["resources"]
        ]
