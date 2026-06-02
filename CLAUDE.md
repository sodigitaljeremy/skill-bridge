# CLAUDE.md — SkillBridge

Mémoire projet pour Claude Code. À lire en début de session.

---

## 1. Contexte

**SkillBridge** est un *Data & AI provider* pour le **DASES** (Data Space for Education &
Skills, écosystème **Prometheus-X**). Le projet est une **démonstration technique** servant
de preuve de compétence dans le cadre d'une candidature « Développeur confirmé : data, IA et
logiciel » chez **Prof en Poche** (Pau).

Le cadrage complet — intention, scénario, périmètre par niveaux, architecture, lots — vit
dans [`docs/cadrage-dases-provider-v0.md`](docs/cadrage-dases-provider-v0.md). Le lire **en
premier** quand on touche au projet.

### Fil rouge

Persona Léa (élève maths primaire, façon Mathia) :

```
App éducative → LRC (xAPI) → PLRS → PDC (échange consenti)
              → Service Data & IA SkillBridge → recommandations
```

## 2. Méthode de travail

- **Cadrage avant code (méthode BMAD).** On valide la cible avant d'écrire la première ligne.
- **Travail par lots** (voir section 11 du cadrage). On termine et fait valider un lot avant
  d'attaquer le suivant.
- **Niveau 1 garanti d'abord** : tout l'effort va d'abord au socle. Niveau 2 vient en bonus,
  une fois le niveau 1 livrable et déployé.
- **Docs as code.** Chaque décision structurante mérite une trace (ADR ou note dans `docs/`).
- **Déploiement souverain** : Docker, Coolify, VPS Hetzner.

## 3. Stack & conventions

### Stack actée

| Couche | Choix |
| --- | --- |
| Langage | Python 3.12 |
| Gestion d'env / deps | `uv` |
| Lint / format | `ruff` |
| Tests | `pytest` (markers : `unit`, `integration`) |
| Service IA | FastAPI, `sentence-transformers` (multilingue local), `scikit-learn` |
| Front de démo | Streamlit |
| Briques externes | PDC + LRC Prometheus-X, intégrés via **Docker** (jamais copiés dans le repo) |
| Infra | Docker Compose, Coolify, Hetzner |

### Conventions de code

- **Architecture hexagonale légère** sous `src/skill_bridge/` :
  `domain/` (entités, ports) → `application/` (cas d'usage) → `adapters/inbound|outbound/`.
- Le **domain** ne dépend ni du framework, ni des adapters.
- Layout `src/` ; le package importé est `skill_bridge`.
- Tests dans `tests/unit/` et `tests/integration/` ; `pythonpath = ["src"]` dans `pyproject.toml`.
- Tout passe par `uv run` (`uv run pytest`, `uv run ruff check .`, `uv run ruff format .`).
- Type hints partout en signature publique.

## 4. Décisions tranchées (à ce stade)

- **Nom du projet :** SkillBridge (repo `skill-bridge`).
- **Référentiel de compétences :** ESCO primaire ; ROME en mapping secondaire, plus tard.
- **Niveau d'ambition :** niveau 1 garanti d'abord, niveau 2 visé en bonus.
- **Front de démo :** Streamlit. Pas d'Angular/Ionic au niveau 1.
- **Embeddings :** `sentence-transformers` multilingue, local (pas d'API externe).
- **Organisation du code :** repo unique pour notre code. PDC et LRC consommés via Docker.

Encore à trancher : délai cible du sprint (cf. section 13 du cadrage).

## 5. Règle de collaboration (Jeremy ↔ Claude ↔ Claude Code)

- **Jeremy** décide et valide. Rien de structurant ne part en code sans son OK.
- **Claude** (stratégie / architecture / sparring) cadre, challenge, propose.
- **Claude Code** (toi) **implémente** : structure, code, tests, configs, docs techniques.
- Boucle de travail : **proposer → faire valider → implémenter → présenter pour validation**.
- **Niveau 1 d'abord.** Ne jamais entamer du niveau 2 ou 3 tant que le niveau 1 du lot courant
  n'est pas validé par Jeremy.
- À la fin de chaque lot ou changement structurant : présenter ce qui a été fait et **s'arrêter
  pour validation** avant la suite.
- En cas de doute sur le périmètre ou un trade-off : **demander**, ne pas inventer.

## 6. Commandes courantes

```bash
uv sync --extra dev          # installer / synchroniser
uv run pytest                # lancer les tests
uv run pytest -m unit        # tests unitaires uniquement
uv run ruff check .          # lint
uv run ruff format .         # formater
```
