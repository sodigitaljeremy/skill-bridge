# Reference — CLI

Tout passe par `uv run …` ou par le `Makefile` (raccourcis lisibles).

## Makefile — cibles

```bash
make help          # liste toutes les cibles avec leur description
```

| Cible | Effet |
| --- | --- |
| `make sync` | `uv sync --extra dev` |
| `make test` | tests unitaires uniquement |
| `make test-all` | tests unit + integration (LRC + API) |
| `make lint` | `ruff check .` |
| `make fmt` | `ruff format .` |
| `make dataset` | `python scripts/generate_dataset.py --seed 42` |
| `make api` | Lance l'API FastAPI (port 8000) avec `--reload` |
| `make front` | Lance la vitrine Streamlit en headless (port 8501) |
| `make demo` | API en background + Streamlit en foreground (`scripts/run_demo.sh`) |

## Scripts

### `scripts/generate_dataset.py`

Génère le dataset. Voir [How-to — régénérer](../how-to/regenerate-dataset.md) pour les
options détaillées.

```bash
uv run python scripts/generate_dataset.py --help
```

### `scripts/run_lot2_demo.py`

Démo CLI du Lot 2 — affiche le clustering et les recos pour Léa + 2 apprenants
représentatifs. Charge le modèle ST réel (sentence-transformers). Utilisé pour
valider la cohérence avec l'API en local.

```bash
uv run python scripts/run_lot2_demo.py
```

### `scripts/run_demo.sh`

Lance API + Streamlit ensemble. Trap sur `Ctrl-C` pour arrêter proprement les deux
processus. Source des logs API : `/tmp/skill-bridge-api.log`.

## Pytest

```bash
# Tests unitaires seuls (rapides, ~10 s)
uv run pytest -m unit

# Tous (incluant integration : API + LRC si LRC_URL posée)
uv run pytest

# Un fichier précis
uv run pytest tests/unit/test_clustering.py -v

# Tests d'intégration API + LRC
LRC_URL=http://localhost:8080 uv run pytest -m integration
```

Markers définis dans `pyproject.toml` :

- `unit` : isolé, rapide, sans réseau ni Docker.
- `integration` : démarre l'API en TestClient (lifespan complet) ou appelle le LRC
  réel — skip si `LRC_URL` absente.

## Ruff

```bash
uv run ruff check .       # détecte
uv run ruff check . --fix # corrige ce qui peut l'être
uv run ruff format .      # formate
```

Config dans `pyproject.toml` :

- Target Python 3.12, line-length 100.
- Sélections : `E`, `F`, `W`, `I`, `N`, `UP`, `B`, `SIM`, `RUF`.
- `tests/**/*.py` autorise les `assert`.

## Uv

Quelques commandes utiles au-delà de `make sync` :

```bash
uv add <pkg>              # ajoute une dépendance runtime
uv add --dev <pkg>        # ajoute en dev
uv remove <pkg>           # supprime
uv run python -c "…"      # exécute Python avec l'env du projet
uv lock --upgrade         # met à jour le lock
```
