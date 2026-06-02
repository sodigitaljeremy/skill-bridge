"""``TraceEncoder`` qui projette une ``LearningTrace`` en ligne CSV "Mathia".

Cette représentation brute est ce qu'on envoie au LRC via ``/convert_custom``, avec le
mapping YAML versionné dans ``data/seed/lrc_mapping_mathia.yml``. Les colonnes doivent
matcher 1-pour-1 ``input_fields`` du mapping.

Les leçons (sans score) émettent ``score_scaled = ""`` (cellule vide) — le mapping YAML
ignore les vides côté lambda.
"""

from typing import Any

from skill_bridge.domain.entities import LearningTrace

CSV_COLUMNS: tuple[str, ...] = (
    "learner_name",
    "resource_id",
    "resource_title",
    "verb",
    "score_scaled",
    "timestamp",
)


class CsvTraceEncoder:
    """Format ``mathia-csv`` : une ligne CSV par trace, colonnes ``CSV_COLUMNS``."""

    format_name = "mathia-csv"

    def encode(self, trace: LearningTrace) -> dict[str, Any]:
        # Le resource_id est le dernier segment du activity.id
        resource_id = trace.object.id.rsplit("/", 1)[-1]
        # On préfère le libellé fr-FR, sinon le premier disponible.
        title = trace.object.definition.name.get(
            "fr-FR", next(iter(trace.object.definition.name.values()), "")
        )
        verb = trace.verb.id.rsplit("/", 1)[-1]
        score = trace.result.score.scaled if trace.result and trace.result.score is not None else ""
        # Nom d'apprenant : ce que met TraceGenerationService dans actor.name (display name).
        learner_name = trace.actor.name or trace.actor.mbox_sha1sum
        return {
            "learner_name": learner_name,
            "resource_id": resource_id,
            "resource_title": title,
            "verb": verb,
            "score_scaled": score,
            "timestamp": trace.timestamp.isoformat(),
        }
