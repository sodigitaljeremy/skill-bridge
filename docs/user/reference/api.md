# Reference — API HTTP

Spec OpenAPI 3 complète : http://localhost:8000/openapi.json
Swagger interactif : http://localhost:8000/docs

Cette page résume les 6 endpoints. Pour les schémas Pydantic détaillés, voir Swagger.

## `GET /health`

Sanity check de préchargement.

```json
{
  "status": "ok",
  "preloaded": true,
  "n_learners": 100,
  "n_resources": 33,
  "n_skills": 18,
  "n_clusters": 4
}
```

## `GET /learners`

Liste des apprenants disponibles. **Ne sert PAS `archetype` ni `ability`** — ce sont
des champs de vérité-terrain de simulation, ils ne fuient pas dans l'API.

```json
[
  {"learner_id": "dbe21d14-…", "display_name": "Léa Martin", "grade_level": 4},
  {"learner_id": "2d5fcc8a-…", "display_name": "Alexandre Traore", "grade_level": 1},
  …
]
```

## `GET /profile/{learner_id}`

Profil de maîtrise **observé** depuis les traces. Pas d'`ability` (vérité latente).

```json
{
  "learner_id": "dbe21d14-…",
  "grade_level": 4,
  "n_traces": 53,
  "mean_score_per_domain": {
    "calcul_de_base": 0.80,
    "geometrie_mesures": 0.40,
    …
  },
  "success_rate_per_domain": {
    "calcul_de_base": 0.88,
    "geometrie_mesures": 0.78,
    …
  }
}
```

**`404`** si `learner_id` inconnu.

## `GET /clusters`

Résultat du clustering (préchargé au boot, identique partout).

```json
{
  "k": 4,
  "silhouette": 0.309,
  "silhouette_by_k": {"2": 0.233, "3": 0.282, "4": 0.309, "5": 0.243, …},
  "clusters": [
    {
      "cluster_id": 0,
      "label": "fort en calcul_de_base, calcul_avance / faible en geometrie_mesures, unites_temps",
      "size": 26,
      "centroid_per_domain": {"calcul_de_base": 0.77, …}
    },
    …
  ]
}
```

!!! note "Présentation des libellés"
    Le champ `label` contient les snake_case originaux. La **vitrine Streamlit
    régénère** des libellés lisibles côté front à partir de `centroid_per_domain` (voir
    `_cluster_label_from_centroid` dans `streamlit_app.py`). La présentation est la
    responsabilité du consommateur.

## `GET /clusters/assignment/{learner_id}`

Affectation d'un apprenant à un cluster.

```json
{
  "learner_id": "dbe21d14-…",
  "cluster_id": 0,
  "cluster_label": "fort en calcul_de_base, calcul_avance / faible en…",
  "distance_to_centroid": 1.23
}
```

**`404`** si `learner_id` inconnu.

## `GET /recommend/{learner_id}?n=5`

Top-N recommandations explicables pour un apprenant. `n` ∈ [1, 10] (top-10 préchargé,
sliced).

```json
[
  {
    "resource_id": "LE004",
    "title": "Découvrir la symétrie",
    "score": 0.894,
    "weak_skills_targeted": ["Symétrie axiale", "Reconnaissance de figures planes"],
    "grade_distance": 1,
    "semantic_similarity": 0.77,
    "cluster_success_rate": 1.0,
    "explanation": "cible 2 compétences faibles (Symétrie axiale, Reconnaissance de figures planes) ; niveau proche ; similarité sémantique 0.77 ; réussie par 100% du cluster."
  },
  …
]
```

Détails du scoring :
- `score = 0.50 · skill_overlap + 0.20 · grade_fit + 0.20 · semantic_similarity + 0.10 · cluster_signal`
- Fallback 3 phases si 0 candidat (cf. [ADR 007](../../tech/adrs/007-mastered-vs-attempted.md)).

**`404`** si `learner_id` inconnu.
