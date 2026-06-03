# ADR 005 — `meta.profile = null` assumé (pas d'injection manuelle)

## Status

**Acté** — Lot 3 (2026-06-02).

## Context

Le LRC charge à la demande trois profils sémantiques DASES depuis les dépôts
`gaia-x-dases/xapi-{lms,assessment,forum}`. Chaque profil expose un ensemble de
**templates** (verb + activity type + règles de présence) qui décrivent des situations
pédagogiques canoniques.

Quand un statement xAPI matche un template, le LRC enrichit la sortie avec
`meta.profile: "<group>.<template>"` (par exemple `assessment.completed`).

Inspection des templates disponibles au SHA pinné :

- **assessment** (5 templates) : `started`, `terminated`, `initialized`, `completed`,
  `answered-question`. Verbes attendus : `start`, `terminated`, `initialized`,
  `completed`, `answered`.
- **lms** (≥ 5 templates) : `accessed-page`, `accessed-file`, `registered-course`, etc.
  Verbes : `accessed`, `registered`, `uploaded`, `downloaded`...

Notre dataset comporte trois familles de ressources : **exercices**, **quiz** et
**leçons**. Il faut les traiter séparément :

- **Quiz et exercices notés sont sémantiquement des assessments** (objet évalué, score,
  verdict). Ils **sont mappables** sur `assessment.completed` : il suffit de poser
  `object.definition.type = "http://adlnet.gov/expapi/activities/assessment"` et
  d'émettre `verb = completed` avec `result.success` (booléen) + `result.score`. C'est
  la voie sémantiquement propre prévue par DASES.
- **Les leçons** ne sont **pas** des assessments. Aucun template DASES ne les couvre
  proprement à ce SHA.

Pour les quiz/exercices, deux raisons distinctes ferment la voie `assessment.completed`
dans notre démo — ce sont des **choix et un obstacle**, pas une impossibilité
sémantique :

1. **Choix de modélisation** : on émet directement les verbes ADL `passed` / `failed`
   plutôt que `completed`. Pour un verdict d'exercice, c'est **plus expressif** (le
   verbe porte le résultat ; pas besoin de lire `result.success`) et c'est la pratique
   xAPI courante. Conséquence : aucun template `assessment` ne matche, puisque ses
   verbes sont `start` / `terminated` / `completed` / `answered`.
2. **Obstacle technique** : la voie `assessment.completed` propre exige `result.success:
   true/false`. Or le LRC à ce SHA mal-interprète `value: true/false` dans un `switch`
   du mapping (cf. [ADR 006](006-csv-custom-vs-mappers-natifs.md)) — on a dû retirer la
   règle `result.success` du mapping pour que la conversion passe. Tant que ce bug
   n'est pas corrigé, la voie propre **n'est pas opérationnellement disponible** côté
   `/convert_custom`.

Pour les leçons, le constat reste : pas de template DASES dédié à ce SHA.

Tentation : injecter un `profile:` dans le mapping pour forcer le match sur les
quiz/exercices, malgré le mismatch verbe. **Rejetée** : ce serait étiqueter un statement
comme conforme à un template qu'il ne respecte pas — le consommateur en aval (autre
provider, LRS) serait trompé.

## Decision

**On n'injecte pas de `profile:` dans le mapping YAML.** `meta.profile` reste `null`
dans la sortie LRC pour toutes nos traces.

Ce `null` **n'est pas une impossibilité sémantique** : pour les quiz/exercices, la voie
`assessment.completed` est techniquement légitime — elle est juste fermée par notre
choix de modélisation `passed`/`failed` (plus expressif) **et** par le bug LRC sur
`result.success` ([ADR 006](006-csv-custom-vs-mappers-natifs.md)). Pour les leçons,
DASES n'a effectivement pas de template adapté — c'est une remontée utile pour
l'écosystème Prometheus-X.

Cet état est documenté dans la vitrine ("limite assumée"), dans le runbook LRC
(`docs/lrc_runbook.md`), et ici.

## Consequences

### Positives

- **Honnêteté sémantique** : on ne prétend pas qu'un statement est conforme à un
  template DASES quand il ne l'est pas. Un consommateur (autre provider, LRS, IA en
  aval) ne sera pas trompé.
- **Cohérence avec l'esprit DASES** : la valeur d'un profil sémantique vient
  précisément de sa **garantie** de structure. Injecter à la main ferait perdre cette
  garantie.
- **Observation pédagogiquement intéressante** : le DASES n'a pas de templates pour le
  scénario "exercice scolaire avec verdict passed/failed". C'est un retour utile pour
  l'écosystème Prometheus-X.

### Compromis

- L'évaluateur voit `meta.profile: null` dans la sortie LRC de la démo. Atténué par la
  doc qui anticipe et explique pourquoi.
- L'enrichissement automatique du LRC (`Profiler.enrich_trace`) n'est pas exercé. Ce
  n'est pas grave pour notre démo (on enrichit nous-mêmes avec nos compétences ESCO),
  mais c'est une feature LRC non démontrée.

### Limites assumées

- **À revisiter sur deux fronts indépendants** :
    - Si on **re-modélise les quiz/exercices en `assessment.completed`** (`object.type
      = assessment`, `verb = completed`, `result.success` + `result.score`) **ET** que
      le bug LRC sur `result.success` est corrigé en amont, on pourra alors injecter
      `profile: assessment.completed` dans le mapping YAML, et `meta.profile` ne sera
      plus `null` pour cette famille.
    - Si DASES propose un jour un template dédié au verdict `exercise-passed` /
      `exercise-failed` (qui correspondrait mieux à notre choix de modélisation
      actuel), on pourra mapper directement sans renoncer à `passed`/`failed`.
- **Pas testé avec le profil `forum`** : le scénario maths primaire ne génère pas
  d'événements sociaux.
