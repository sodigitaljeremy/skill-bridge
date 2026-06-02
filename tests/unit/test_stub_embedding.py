"""Sanity tests pour le StubEmbeddingProvider : déterministe et L2-normalisé."""

import numpy as np
import pytest

from skill_bridge.adapters.outbound.stub_embedding_provider import StubEmbeddingProvider


@pytest.mark.unit
def test_same_text_yields_same_vector() -> None:
    p = StubEmbeddingProvider(dimension=16)
    a = p.embed(["bonjour le monde"])
    b = p.embed(["bonjour le monde"])
    assert np.allclose(a, b)


@pytest.mark.unit
def test_vectors_are_l2_normalized() -> None:
    p = StubEmbeddingProvider(dimension=32)
    out = p.embed(["addition entière", "périmètre du rectangle", "résoudre un problème"])
    norms = np.linalg.norm(out, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-9)


@pytest.mark.unit
def test_different_texts_yield_different_vectors() -> None:
    p = StubEmbeddingProvider(dimension=16)
    out = p.embed(["addition", "soustraction"])
    assert not np.allclose(out[0], out[1])
