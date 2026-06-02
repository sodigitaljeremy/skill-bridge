"""``TraceConverter`` déterministe pour les tests unitaires (sans réseau).

Stratégie : on ré-implémente *grossièrement* le mapping CSV→xAPI à l'intérieur du stub
pour produire un flux de la forme exacte attendue par les tests aval. Le stub n'imite
PAS la chaîne LRC réelle (lambdas, switch...), c'est uniquement un fixture stable.
"""

import csv
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Final

ACTIVITY_BASE: Final[str] = "https://mathia.example.com/resource/"
LMS_HOMEPAGE: Final[str] = "https://mathia.example.com"
VERB_URIS: Final[dict[str, str]] = {
    "passed": "http://adlnet.gov/expapi/verbs/passed",
    "failed": "http://adlnet.gov/expapi/verbs/failed",
    "completed": "http://adlnet.gov/expapi/verbs/completed",
    "attempted": "http://adlnet.gov/expapi/verbs/attempted",
}


class StubLrcConverter:
    """Mappe colonne-à-colonne ``CSV_COLUMNS`` (mathia-csv) vers du xAPI minimal."""

    def convert(self, data_path: Path, mapping_path: Path) -> Iterable[dict[str, Any]]:
        del mapping_path  # le stub ignore le mapping — il a sa logique interne fixe
        with data_path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                statement: dict[str, Any] = {
                    "actor": {
                        "account": {
                            "name": row["learner_name"],
                            "homePage": LMS_HOMEPAGE,
                        }
                    },
                    "object": {
                        "id": f"{ACTIVITY_BASE}{row['resource_id']}",
                        "definition": {
                            "name": {"fr-FR": row["resource_title"]},
                        },
                    },
                    "verb": {
                        "id": VERB_URIS.get(row["verb"], row["verb"]),
                        "display": {"en-US": row["verb"]},
                    },
                    "timestamp": row["timestamp"],
                }
                score = row.get("score_scaled", "")
                if score not in ("", None):
                    statement["result"] = {"score": {"scaled": float(score)}}
                yield statement
