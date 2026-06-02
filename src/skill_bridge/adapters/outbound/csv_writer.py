"""Écriture CSV (avec en-tête) — pendant de ``dataset_writer.write_jsonl``."""

import csv
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any


def write_csv(
    records: Iterable[dict[str, Any]],
    path: Path,
    columns: Sequence[str],
) -> int:
    """Écrit les ``records`` au format CSV avec en-tête ``columns``.

    Retourne le nombre de lignes écrites (hors en-tête).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(columns))
        writer.writeheader()
        for record in records:
            writer.writerow({col: record.get(col, "") for col in columns})
            count += 1
    return count
