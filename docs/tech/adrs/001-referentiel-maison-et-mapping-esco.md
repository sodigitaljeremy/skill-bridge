# ADR 001 — Référentiel maison de compétences + mapping ESCO

## Status

**Acté** — Lot 1 (2026-06-02).

## Context

Le projet doit représenter les **compétences** des apprenants pour profiler, clusteriser
et recommander. Deux options se présentaient :

1. **Utiliser ESCO directement** comme référentiel de compétences.
2. **Construire un référentiel maison** calé sur le scénario, et mapper vers ESCO en
   sortie.

ESCO est conçu pour le **marché du travail**. Sa granularité ne descend **pas** au niveau
d'une compétence scolaire de cycle 2/3 — il n'y a pas de noeud "addition à deux chiffres
avec retenue" ou "lecture de l'heure" dans ESCO. Tester cela sur le portail confirme : la
recherche `numeracy primary` ne ramène que des compétences génériques type `use numeracy
skills`, sans grain pédagogique exploitable.

Or notre scénario maths primaire (persona Léa, app type Mathia) exige cette granularité
fine — sans quoi le profilage par domaine et la reco ciblée n'ont pas de sens.

## Decision

1. **Référentiel maison numératie primaire** versionné dans
   `data/skills/numeracy_primary.json` : 18 compétences, 6 domaines (calcul de base,
   calcul avancé, fractions & décimaux, géométrie & mesures, unités & temps, résolution
   de problèmes). Inspiré des programmes français cycles 2 et 3 (BO).
2. **Mapping vers ESCO** dans `data/skills/esco_mapping.json` : chaque compétence maison
   peut pointer vers 0 à N URIs ESCO pertinentes. La structure est `Skill.esco_uris:
   list[str]`.
3. Les URIs ESCO actuelles sont **illustratives** (forme canonique
   `http://data.europa.eu/esco/skill/<uuid>` mais UUIDs non vérifiés sur le portail —
   documenté dans `data/skills/README.md`).

## Consequences

### Positives

- Granularité fine adaptée au scénario primaire — clustering et reco ont du sens.
- Le **mécanisme d'interopérabilité sémantique** (référentiel maison → référentiel pivot)
  est démontré, qui est précisément la valeur d'un dataspace comme le DASES.
- Le champ `esco_uris` étant porté par chaque trace enrichie, un consommateur
  Prometheus-X peut joindre sur ESCO sans connaître notre référentiel interne.

### Compromis

- **Maintenance** : le référentiel maison doit être tenu à jour si Mathia évolue.
  Atténué par le faible volume (18 compétences) et le seed JSON facile à éditer.
- **URIs ESCO à valider** avant tout usage en production réelle. La vitrine et la doc
  l'indiquent explicitement.

### Limites assumées

- Aucun **lien hiérarchique** entre compétences maison (pas de "préreq", pas de "skill
  tree"). Pour le niveau 1, suffisant. À ajouter si on veut faire de la progression
  recommandée plutôt que du re-travail des faiblesses.
- Le **mapping ROME** (France Travail) est mentionné dans le cadrage mais non implémenté
  — viendra plus tard si nécessaire.
