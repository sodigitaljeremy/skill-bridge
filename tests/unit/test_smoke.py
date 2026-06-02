"""Smoke test — vérifie que le package est importable et expose sa version."""

import pytest

from skill_bridge import __version__


@pytest.mark.unit
def test_package_exposes_version() -> None:
    assert isinstance(__version__, str)
    assert __version__.count(".") >= 2
