# ADR 006 — `/convert_custom` avec mapping maison, pas mappers natifs

## Status

**Acté** — Lot 3 (2026-06-02).

## Context

Le LRC expose deux endpoints de conversion :

- `POST /convert` : prend un statement et un `input_format` ∈
  {`xapi`, `imscaliper1_2`, `imscaliper1_1`, `scorm_2004`, `matomo`}. Le LRC applique
  un **mapper natif** (YAML interne) pour produire un xAPI.
- `POST /convert_custom` : prend un fichier de données + un mapping YAML fourni par
  l'appelant. Streame du JSONL xAPI en sortie.

Le spike du Lot 3 a testé les deux voies.

**Mappers natifs** : la validation Pydantic en entrée est très stricte (un Matomo sans
`visitIp` est refusé). Plus problématique, plusieurs mappers natifs produisent du xAPI
**douteux** :

- SCORM 2004 produit un `object` par défaut codé en dur (`https://example.com/activity/test`),
  ignorant le contexte applicatif réel.
- Matomo prépend `http://` à `siteName` sans vérification, créant des IRIs invalides
  (`http://Mathia Demo` → rejeté par la validation xAPI en sortie).

`/convert_custom` est, en revanche, **stable et flexible** : on contrôle tout le
mapping, et la sortie est conforme tant qu'on la construit correctement.

## Decision

Chemin de **production** de SkillBridge = `/convert_custom` + mapping YAML maison
`data/seed/lrc_mapping_mathia.yml`. Format brut = CSV "Mathia" propriétaire avec 6
colonnes (`learner_name`, `resource_id`, `resource_title`, `verb`, `score_scaled`,
`timestamp`).

Mappers natifs Matomo / SCORM : **mention narrative seulement** ("le LRC supporte aussi
ces formats nativement"), pas dans le chemin critique.

### Bug LRC découvert pendant le spike

Notre mapping initial portait une règle `switch` sur le verbe pour positionner
`result.success` à `true`/`false`. Le LRC à ce SHA **mal-interprète** `value: true/false`
dans un `switch` : la chaîne `"failed"` arrive comme valeur de `result.success`, et la
validation Pydantic xAPI en sortie casse le stream.

Workaround retenu : **retirer la règle `result.success`** du mapping. Le consommateur
déduit `success` du `verb.id` en aval (`passed` → True, `failed` → False). Documenté
dans le mapping YAML lui-même.

## Consequences

### Positives

- **Contrôle total** sur la sortie xAPI — chaque champ est exactement ce qu'on veut.
- Le mapping YAML est un **asset de démo** : il montre l'expertise sur xAPI / DASES et
  reste réutilisable / inspectable.
- Robustesse à l'évolution amont : si le LRC bouge ses mappers natifs, on n'est pas
  impacté.
- La sortie matche notre catalogue interne (`object.id` pointe vers nos `resource_id`).

### Compromis

- **On porte le mapping**. C'est ~50 lignes YAML, donc faible coût, mais c'est un
  artefact à maintenir si on ajoute des colonnes au CSV.
- Le LRC à ce SHA a **un bug connu** (`value: true/false` dans `switch`). Le workaround
  est documenté ; à retester si on change de SHA.

### Limites assumées

- Notre démo n'exerce pas les mappers natifs Matomo / SCORM / IMS Caliper. Pour les
  prouver "fonctionnellement intégrés", il faudrait un second mapping et un second
  scénario — hors scope niveau 1.
- Le profil DASES n'est pas matché ([ADR 005](005-profil-dases-null.md)). Indépendant
  de cette décision : même les mappers natifs ne le matcheraient pas mieux pour nos
  verbes.
