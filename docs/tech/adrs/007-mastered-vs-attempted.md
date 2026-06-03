# ADR 007 — Reco filtre sur `mastered_resource_ids`, pas `attempted`

## Status

**Acté** — Lot 5a (2026-06-03).

## Context

Le moteur de recommandation détecte les compétences faibles d'un apprenant, filtre les
ressources candidates par compétence ciblée + grade adapté, score, puis renvoie le
top-N.

Premier filtre (Lot 2) : **« non déjà tentée »**. Logique apparente : "on ne re-propose
pas une ressource déjà faite".

Symptôme constaté pendant les tests d'API (Lot 5a) : **Léa reçoit 0 reco**. Diagnostic :

1. Léa (`calc_specialist`) est faible en géométrie → domaines ciblés = `geometrie_mesures`,
   `unites_temps`.
2. Le catalogue compte 4 ressources principalement en géométrie (EX013, EX014, LE004,
   QZ004), toutes au grade ±1 de Léa.
3. Avec ~58 traces stratifiées sur 6 domaines = ~10 traces en géométrie, Léa a tenté
   **chacune des 4 ressources** au moins une fois (avec replacement).
4. Le filtre "non déjà tentée" → **tous les candidats éliminés** → reco vide.

Réflexion pédagogique : une ressource **échouée** N'A PAS été maîtrisée. Refuser de la
re-recommander, c'est interdire le **re-travail des échecs**, qui est précisément ce
qu'on veut faire dans un domaine faible.

## Decision

Remplacer le filtre par **« non déjà MAÎTRISÉE »** :

- `LearnerProfile` gagne `mastered_resource_ids: list[str]` : ressources avec **au
  moins une trace `verb=passed` (exercice/quiz) ou `verb=completed` (leçon)**.
- `RecommendationService` filtre sur `mastered_resource_ids` au lieu de
  `attempted_resource_ids`.
- Une ressource échouée (tentée mais jamais passée) **reste candidate** pour la reco.

### Choix sémantique

"Un seul succès vaut maîtrise, jamais d'oubli". C'est le modèle de mémoire **le plus
simple**. On ne modélise pas la *spaced repetition*, ni la perte de maîtrise au fil du
temps — niveau 1, pas niveau 2.

### Fallback à 3 phases

Pour le cas (rare) où l'apprenant aurait quand même maîtrisé toutes les ressources
candidates à grade ±1 :

```
Phase 1 (nominal)  : grade ±1, hors maîtrisées
Phase 2 (élargi)   : grade ±2, hors maîtrisées
Phase 3 (recours)  : grade ±1, incluant maîtrisées
```

Sur le dataset complet (100 apprenants, seed 42), Léa reçoit ses recos dès la phase 1.
Test régression : `test_lea_receives_recommendations_on_full_dataset`.

## Consequences

### Positives

- **Re-travail pédagogique des échecs explicite**. C'est le bon comportement attendu
  par un enseignant et par un évaluateur.
- Léa reçoit ses recos sur le dataset complet (validé par test).
- Le test `test_failed_resources_are_eligible_for_recommendation` montre dynamiquement
  qu'au moins une reco vient bien du pool "échouée non maîtrisée".

### Compromis

- **Modèle de mémoire simpliste** : pas de courbe d'oubli. Un apprenant qui a passé
  EX003 il y a 6 mois est toujours considéré comme l'ayant maîtrisé. Acceptable pour
  niveau 1 ; le `timestamp` est dans la trace, on saura raffiner.
- **Le `attempted_resource_ids` reste exposé** dans `LearnerProfile` (utile pour les
  stats / affichage), mais n'est plus consommé par le moteur de reco. Coût mémoire
  négligeable.

### Limites assumées

- Pas de **distinction entre "passed avec score 0.55" et "passed avec score 0.95"**.
  Une maîtrise marginale est traitée comme une maîtrise solide. On pourrait introduire
  un seuil "passed ≥ 0.75 = maîtrisé" si on observe que les apprenants reçoivent trop
  vite des reco vers du nouveau matériel — non observé à ce stade.
- Pour les **leçons**, on considère `completed` comme maîtrise. C'est plus fragile
  (passer une leçon ≠ comprendre la leçon), mais sans signal de score il n'y a pas
  d'autre option.
