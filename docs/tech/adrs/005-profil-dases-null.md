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

Nos statements utilisent les verbes ADL standard `passed`, `failed`, `completed`, sur
des objets type `performance` (exercice), `lesson` (leçon) ou `assessment` (quiz). Le
mapping YAML pose `object.definition.type = "http://adlnet.gov/expapi/activities/interaction"`.

**Aucune combinaison** de nos verbes + types ne matche un template DASES sans
déformation sémantique :

- `passed` / `failed` n'existent pas dans `lms` ni `assessment`.
- `completed` matcherait `assessment.completed`, mais cela demanderait de re-typer nos
  **leçons** comme `assessment` — ce serait factuellement faux.

Tentation : injecter un `profile:` dans le mapping pour forcer le match.

## Decision

**On n'injecte pas de `profile:` dans le mapping YAML.** `meta.profile` reste `null`
dans la sortie LRC. Cet état est documenté dans la vitrine ("limite assumée"), dans le
runbook LRC (`docs/lrc_runbook.md`), et ici.

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

- **À revisiter si DASES évolue**. Si un futur profil `assessment` ajoute un template
  `exercise-passed` / `exercise-failed`, on pourra mapper nos statements dessus. La
  structure de notre mapping YAML facilitera cet ajout (1 ligne `profile:` à
  positionner conditionnellement).
- **Pas testé avec le profil `forum`** : le scénario maths primaire ne génère pas
  d'événements sociaux.
