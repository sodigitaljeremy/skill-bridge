# Prise en main — du clone à la vitrine en 5 minutes

Ce tutoriel guide pas à pas le passage d'un repo cloné à la **vitrine Streamlit qui
tourne en local**. Aucun choix à faire — suis les commandes, tu verras le résultat.

## Pré-requis

- Python **3.12** disponible.
- [`uv`](https://docs.astral.sh/uv/) installé (gestionnaire d'environnement Python).
- ~3 GB d'espace disque libre (pour torch + sentence-transformers + cache modèle).

## Étape 1 — Cloner et synchroniser

```bash
git clone https://github.com/sodigitaljeremy/skill-bridge.git
cd skill-bridge
make sync
```

`make sync` installe **toutes** les dépendances de prod et de dev (incluant
`fastapi`, `streamlit`, `scikit-learn`, `sentence-transformers`, `torch` CPU, et la
chaîne mkdocs). Premier lancement : compte ~3 minutes.

## Étape 2 — Générer le dataset

```bash
make dataset
```

Crée `data/generated/` avec :

| Fichier | Contenu | Usage |
| --- | --- | --- |
| `traces.jsonl` | 5800 statements xAPI | Source pour `enriched.jsonl` |
| `enriched.jsonl` | 5800 traces enrichies par compétences | Entrée de l'API |
| `learners.jsonl` | 100 apprenants + vérité-terrain (archetype, ability) | Vitrine (validation cluster ↔ archétype) |

Sortie console attendue :

```
OK — 100 apprenants (100 dans learners.jsonl), 5800 traces xAPI, 5800 traces enrichies...

=== Stats ===
Verbes : completed=1135, failed=2013, passed=2652
Archetypes : calc_specialist=26, geo_specialist=23, reasoning_specialist=22, struggling=29

Domaine                    Total   Min   Méd   Max
--------------------------------------------------
calcul_avance                978     5    10    17
...
```

## Étape 3 — Lancer la démo

```bash
make demo
```

Ceci :

1. Démarre l'API FastAPI sur `http://localhost:8000`. Au premier lancement,
   l'API télécharge le modèle `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
   (~470 MB) — compter ~30 s. Logs dans `/tmp/skill-bridge-api.log`.
2. Attend que `/health` réponde 200.
3. Démarre la vitrine Streamlit sur `http://localhost:8501` en mode headless (pas de
   prompt email, pas d'ouverture auto du navigateur).

**Ouvre http://localhost:8501** dans ton navigateur.

## Étape 4 — Explorer

Trois écrans dans la nav latérale :

- **Vue d'ensemble** : pitch, fil rouge, encart interopérabilité (CSV brut → xAPI via
  LRC), mapping ESCO.
- **Apprenant** : Léa par défaut. Profil de maîtrise par domaine, cluster assigné,
  top-5 recommandations expliquées.
- **Clustering** : sélection de `k` par silhouette, 4 clusters découverts, **heatmap
  des centroïdes** (visu principale), projection PCA 2D (illustrative), et table
  cluster ↔ archétype avec pureté observée.

L'API Swagger est joignable sur http://localhost:8000/docs.

## Étape 5 — Arrêter

`Ctrl+C` dans le terminal `make demo` arrête proprement les deux processus.

## Et après ?

- [How-to — régénérer le dataset](../how-to/regenerate-dataset.md) pour changer la seed,
  le nombre d'apprenants, etc.
- [How-to — ingérer via le LRC](../how-to/ingest-via-lrc.md) pour démontrer le chemin
  d'interopérabilité réel.
- [Reference — API HTTP](../reference/api.md) pour appeler l'API depuis ton propre code.
