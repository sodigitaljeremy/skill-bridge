"""Loaders JSONL pour les artefacts du Lot 1 : enriched.jsonl et learners.jsonl."""

import json
from datetime import datetime
from pathlib import Path
from uuid import UUID

from skill_bridge.application.enrichment import EnrichedTrace, ResolvedSkill
from skill_bridge.domain.entities import Learner


class FileEnrichedTraceLoader:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load_all(self) -> list[EnrichedTrace]:
        out: list[EnrichedTrace] = []
        with self._path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                payload = json.loads(line)
                skills = [
                    ResolvedSkill(
                        id=s["id"],
                        preferred_label=s["preferred_label"],
                        domain=s["domain"],
                        esco_uris=list(s.get("esco_uris", [])),
                    )
                    for s in payload["skills"]
                ]
                out.append(
                    EnrichedTrace(
                        trace_id=payload["trace_id"],
                        learner_id=payload["learner_id"],
                        resource_id=payload["resource_id"],
                        verb=payload["verb"],
                        success=payload.get("success"),
                        score=payload.get("score"),
                        duration=payload.get("duration"),
                        timestamp=datetime.fromisoformat(payload["timestamp"]),
                        skills=skills,
                    )
                )
        return out


class FileLearnersLoader:
    """Lit ``learners.jsonl`` — vérité-terrain à n'utiliser que pour sanity-check / picking."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load_all(self) -> list[Learner]:
        out: list[Learner] = []
        with self._path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                payload = json.loads(line)
                out.append(
                    Learner(
                        learner_id=UUID(payload["learner_id"]),
                        display_name=payload["display_name"],
                        mbox_sha1sum=payload["mbox_sha1sum"],
                        grade_level=payload["grade_level"],
                        ability=dict(payload["ability"]),
                        archetype=payload.get("archetype"),
                    )
                )
        return out
