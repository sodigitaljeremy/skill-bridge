# SkillBridge

> **Data & AI provider pour le dataspace éducation & compétences.**

Démonstration technique réalisée dans l'écosystème [Prometheus-X](https://prometheus-x.org/) /
DASES (Data Space for Education & Skills) : ingestion de traces d'apprentissage au format **xAPI**,
enrichissement par compétences via le référentiel **ESCO**, **clustering** et **recommandation**
de ressources, le tout exposé comme une brique réutilisable et déployable.

## Fil rouge

Application éducative → **LRC** (conversion xAPI) → **PLRS** (coffre apprenant) →
**PDC** (échange consenti) → **Service Data & IA SkillBridge** → recommandations personnalisées.

## Stack

- **Python 3.12** · `uv` · `ruff` · `pytest`
- **Service IA :** FastAPI, `sentence-transformers` (multilingue, local), `scikit-learn`
- **Front de démo :** Streamlit
- **Briques externes intégrées via Docker :** `dataspace-connector` (PDC, Prometheus-X) ·
  `learning-records-converter` (LRC, Prometheus-X)
- **Infra cible :** Docker Compose, déploiement Coolify / Hetzner

## Architecture

Architecture hexagonale légère sous `src/skill_bridge/` :

```
domain/        # entités métier, value objects, ports
application/   # cas d'usage
adapters/
  inbound/     # FastAPI, Streamlit, CLI
  outbound/    # ESCO, embeddings, persistence, PDC, LRC
```

## Documentation

- **Cadrage v0 :** [`docs/cadrage-dases-provider-v0.md`](docs/cadrage-dases-provider-v0.md)
- **Mémoire projet pour Claude Code :** [`CLAUDE.md`](CLAUDE.md)

## Démarrage rapide

```bash
uv sync --extra dev          # installe les deps
uv run pytest                # lance les tests
uv run ruff check .          # lint
uv run ruff format .         # format
```

## Statut

🚧 Fondation posée. Lot 1 (génération de traces xAPI synthétiques + enrichissement ESCO) à venir.
