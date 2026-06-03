# Décisions d'architecture (ADRs)

Toutes les décisions structurantes du projet sont tracées au format **MADR
minimaliste** : Status / Context / Decision / Consequences.

Une ADR documente le **raisonnement**, pas seulement la conclusion. Les "Consequences"
incluent **les compromis et limites assumées** — pas seulement les avantages.

## Liste

| # | Titre | Lot | État |
| --- | --- | --- | --- |
| [001](001-referentiel-maison-et-mapping-esco.md) | Référentiel maison + mapping ESCO | 1 | ✅ Acté |
| [002](002-archetypes-par-forme.md) | Archétypes par *forme* (pas par magnitude) | 1 / 2 | ✅ Acté |
| [003](003-k-par-silhouette-empirique.md) | `k` par silhouette pur, sans tie-break heuristique | 2 | ✅ Acté |
| [004](004-lrc-runbook-vs-submodule.md) | LRC traité comme service externe, pas submodule | 3 | ✅ Acté |
| [005](005-profil-dases-null.md) | `meta.profile = null` assumé (pas d'injection à la main) | 3 | ✅ Acté |
| [006](006-csv-custom-vs-mappers-natifs.md) | `/convert_custom` avec mapping maison, pas mappers natifs | 3 | ✅ Acté |
| [007](007-mastered-vs-attempted.md) | Reco filtre sur `mastered_resource_ids`, pas `attempted` | 5a | ✅ Acté |

## Convention

- **Status** : Acté · Proposé · Déprécié · Remplacé par ADR-NNN.
- Numérotation séquentielle à 3 chiffres, jamais réutilisée.
- Une décision dépréciée reste dans l'historique avec son statut mis à jour ; on ne
  réécrit pas l'histoire.
