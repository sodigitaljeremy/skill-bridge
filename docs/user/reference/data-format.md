# Reference — Format des données

Les trois artefacts JSONL produits par `make dataset` dans `data/generated/`.

## `traces.jsonl`

Un **statement xAPI** par ligne. Conforme à la spec xAPI 1.0.3, sans alignement DASES
(cf. [ADR 005](../../tech/adrs/005-profil-dases-null.md)).

```json
{
  "id": "uuid-deterministe-via-uuid5",
  "actor": {
    "objectType": "Agent",
    "mbox_sha1sum": "f2db149bf28b32c1e2388f09f252b47a429ff7fe",
    "name": "Léa Martin"
  },
  "verb": {
    "id": "http://adlnet.gov/expapi/verbs/passed",
    "display": {"en-US": "passed"}
  },
  "object": {
    "objectType": "Activity",
    "id": "http://skillbridge.local/resource/EX003",
    "definition": {
      "name": {"fr-FR": "Additions à deux chiffres avec retenue"},
      "type": "http://adlnet.gov/expapi/activities/performance"
    }
  },
  "result": {
    "success": true,
    "completion": true,
    "score": {"scaled": 0.92},
    "duration": "PT240S"
  },
  "timestamp": "2026-03-15T14:30:00+00:00",
  "version": "1.0.3"
}
```

Tableau des verbes utilisés :

| Verbe | Type de ressource | Sens |
| --- | --- | --- |
| `passed` | exercice / quiz | Tentative réussie, score ≥ 0.5 |
| `failed` | exercice / quiz | Tentative échouée, score < 0.5 |
| `completed` | leçon | Leçon parcourue (pas de score) |

## `enriched.jsonl`

Enrichissement d'une trace par les compétences de sa ressource. Format intermédiaire
consommé par l'API.

```json
{
  "trace_id": "…",
  "learner_id": "f2db149b…",
  "resource_id": "EX003",
  "verb": "passed",
  "success": true,
  "score": 0.92,
  "duration": "PT240S",
  "timestamp": "2026-03-15T14:30:00+00:00",
  "skills": [
    {
      "id": "addition_entiers",
      "preferred_label": "Addition d'entiers naturels",
      "domain": "calcul_de_base",
      "esco_uris": ["http://data.europa.eu/esco/skill/2ec70df4-…"]
    }
  ]
}
```

- `learner_id` ici = **`mbox_sha1sum`** (pseudonyme), pas l'UUID. C'est le pivot qu'on
  joint avec les traces.
- `esco_uris` peut être vide si la compétence n'a pas de mapping ESCO actuel
  ([ADR 001](../../tech/adrs/001-referentiel-maison-et-mapping-esco.md)).

## `learners.jsonl`

**Vérité-terrain de simulation** — utilisé uniquement par la vitrine pour valider la
cohérence cluster ↔ archétype. **N'est jamais exposé par l'API.**

```json
{
  "learner_id": "dbe21d14-856a-5279-8bee-af09ed230fb2",
  "mbox_sha1sum": "f2db149bf28b32c1e2388f09f252b47a429ff7fe",
  "display_name": "Léa Martin",
  "grade_level": 4,
  "archetype": "calc_specialist",
  "ability": {
    "calcul_de_base": 0.85,
    "calcul_avance": 0.85,
    "fractions_decimaux": 0.55,
    "geometrie_mesures": 0.45,
    "unites_temps": 0.55,
    "resolution_problemes": 0.55
  }
}
```

Champs sensibles (`archetype`, `ability`) : ils sont la **vérité latente du
générateur**, indisponible en production réelle. Documenté dans la vitrine et dans
[ADR 002](../../tech/adrs/002-archetypes-par-forme.md).

## Artefacts optionnels (`--via-lrc`)

| Fichier | Contenu |
| --- | --- |
| `sample_mathia.csv` | Échantillon CSV propriétaire envoyé au LRC |
| `traces_via_lrc.jsonl` | Statements xAPI retournés par `/convert_custom` |

Voir [How-to — ingérer via le LRC](../how-to/ingest-via-lrc.md).
