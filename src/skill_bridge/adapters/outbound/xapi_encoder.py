"""Encodeur xAPI : sérialise une ``LearningTrace`` en dict JSON-conforme."""

from typing import Any

from skill_bridge.domain.entities import LearningTrace


class XApiJsonLinesEncoder:
    """Format ``xapi-jsonl`` : un statement xAPI par ligne JSON."""

    format_name = "xapi-jsonl"

    def encode(self, trace: LearningTrace) -> dict[str, Any]:
        return trace.model_dump(mode="json", exclude_none=True)
