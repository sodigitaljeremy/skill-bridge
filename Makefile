.PHONY: help sync test test-all lint fmt api front demo dataset

help:  ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

sync:  ## Installe / synchronise les dépendances (uv sync --extra dev)
	uv sync --extra dev

test:  ## Tests unitaires uniquement
	uv run pytest -m unit

test-all:  ## Tous les tests (unit + integration ; LRC_URL requis pour les tests LRC)
	uv run pytest

lint:  ## Ruff check
	uv run ruff check .

fmt:  ## Ruff format
	uv run ruff format .

dataset:  ## Regénère le dataset (data/generated/) avec la seed par défaut
	uv run python scripts/generate_dataset.py --seed 42

api:  ## Lance l'API FastAPI sur http://localhost:8000 (Swagger: /docs)
	uv run uvicorn skill_bridge.adapters.inbound.api.app:create_app --factory --reload --port 8000

front:  ## Lance la vitrine Streamlit sur http://localhost:8501 (l'API doit déjà tourner)
	uv run streamlit run src/skill_bridge/adapters/inbound/streamlit_app.py --server.port=8501

demo:  ## Lance API + Streamlit ensemble (Ctrl-C pour tout arrêter)
	bash scripts/run_demo.sh
