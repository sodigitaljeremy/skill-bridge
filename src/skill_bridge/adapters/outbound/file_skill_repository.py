"""Charge le référentiel de compétences (numeracy primaire) depuis JSON local.

Joint un mapping ESCO optionnel : chaque ``Skill`` produit porte les URIs ESCO
correspondantes (liste vide si pas de mapping).
"""

import json
from pathlib import Path

from skill_bridge.domain.entities import Skill


class FileSkillRepository:
    def __init__(self, skills_path: Path, mapping_path: Path | None = None) -> None:
        self._skills_path = skills_path
        self._mapping_path = mapping_path

    def load_all(self) -> list[Skill]:
        raw = json.loads(self._skills_path.read_text(encoding="utf-8"))
        mappings: dict[str, list[str]] = {}
        if self._mapping_path is not None and self._mapping_path.exists():
            raw_mapping = json.loads(self._mapping_path.read_text(encoding="utf-8"))
            mappings = raw_mapping.get("mappings", {})

        return [
            Skill(
                id=s["id"],
                preferred_label=s["preferred_label"],
                description=s["description"],
                domain=s["domain"],
                esco_uris=mappings.get(s["id"], []),
            )
            for s in raw["skills"]
        ]
