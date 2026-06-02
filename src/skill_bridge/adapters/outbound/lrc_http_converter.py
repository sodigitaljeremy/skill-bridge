"""``TraceConverter`` HTTP — client du LRC ``/convert_custom``.

Le LRC répond en JSONL streamé (1 statement xAPI par ligne). On ``yield`` les dicts au
fil de la lecture, sans buffer en mémoire — utile si l'échantillon grossit.

L'en-tête ``Host: lrc.localhost`` est forcé pour passer le routage Traefik du LRC dev.
"""

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import httpx

DEFAULT_HOST_HEADER: str = "lrc.localhost"
DEFAULT_TIMEOUT_SECONDS: float = 60.0


class LrcConverterError(RuntimeError):
    """Erreur côté LRC (HTTP non-2xx ou réponse mal formée)."""


class LrcHttpConverter:
    def __init__(
        self,
        base_url: str,
        host_header: str = DEFAULT_HOST_HEADER,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._host_header = host_header
        self._timeout = timeout

    def convert(self, data_path: Path, mapping_path: Path) -> Iterable[dict[str, Any]]:
        url = f"{self._base_url}/convert_custom"
        headers = {"Host": self._host_header} if self._host_header else {}
        with (
            data_path.open("rb") as data_f,
            mapping_path.open("rb") as map_f,
        ):
            files = {
                "data_file": (data_path.name, data_f, "text/csv"),
                "mapping_file": (mapping_path.name, map_f, "application/x-yaml"),
            }
            data = {"output_format": "xAPI"}
            try:
                with httpx.stream(
                    "POST",
                    url,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=self._timeout,
                ) as response:
                    if response.status_code >= 400:
                        response.read()
                        raise LrcConverterError(
                            f"LRC returned HTTP {response.status_code}: {response.text}"
                        )
                    for line in response.iter_lines():
                        if not line.strip():
                            continue
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError as e:
                            raise LrcConverterError(f"LRC returned non-JSON line: {line!r}") from e
            except httpx.HTTPError as e:
                raise LrcConverterError(f"LRC HTTP error: {e}") from e

    def ping(self) -> bool:
        """Sanity-check : ``GET /docs`` retourne 200 ?"""
        headers = {"Host": self._host_header} if self._host_header else {}
        try:
            r = httpx.get(
                f"{self._base_url}/docs",
                headers=headers,
                timeout=5.0,
            )
            return r.status_code == 200
        except httpx.HTTPError:
            return False
