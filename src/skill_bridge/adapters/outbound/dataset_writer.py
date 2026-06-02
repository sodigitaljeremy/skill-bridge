"""Écriture d'enregistrements en JSON Lines (un dict JSON par ligne)."""

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def write_jsonl(records: Iterable[dict[str, Any]], path: Path) -> int:
    """Écrit les ``records`` au format JSON Lines dans ``path``.

    Crée les répertoires parents si besoin. Retourne le nombre de lignes écrites.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, default=str))
            f.write("\n")
            count += 1
    return count
