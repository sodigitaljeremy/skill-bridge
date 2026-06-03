# ADR 002 — Archétypes pédagogiques par *forme*, pas par *magnitude*

## Status

**Acté** — Lot 1, refactor post-Lot 2 (2026-06-02).

## Context

Le dataset synthétique doit générer des **profils d'apprenants différenciés** pour que
le clustering ait du sens et que la démo soit interprétable.

Premier design (Lot 1 v0) : 4 archétypes avec **moyennes globales différentes**
(`strong_calc_weak_geo` ≈ 0.70, `balanced_strong` ≈ 0.77, `strong_reasoning` ≈ 0.61,
`struggling` ≈ 0.43). σ = 0.10.

Résultat empirique au Lot 2 : la **silhouette piquait sur k=2**, fusionnant les 3
"forts" archetypes en un seul cluster vs `struggling`. `strong_reasoning` (moyenne basse
malgré son pic à 0.92 sur résolution de problèmes) se mélangeait à `struggling`.

Diagnostic : **KMeans en distance euclidienne capte d'abord la magnitude globale**.
Quand les archétypes diffèrent surtout par leur niveau moyen, le clustering compresse
les hauts ensembles, même si leurs *formes* sont distinctes.

Tentation immédiate : ajouter un **tie-break heuristique** ("si silhouette[k=4] est dans
5% de silhouette[k=2], préférer k=4"). Rejetée : c'est de la triche, c'est repérable, et
c'est l'aveu qu'on contourne un problème de design (cf. [ADR 003](003-k-par-silhouette-empirique.md)).

## Decision

Redesigner les archétypes pour qu'ils diffèrent par **forme** plutôt que par magnitude.
Trois spécialistes à **moyenne globale comparable** (~0.63) + un profil en difficulté
générale.

```
calc_specialist      : pics à 0.85 sur calcul_de_base, calcul_avance ; valleys 0.45-0.55
geo_specialist       : pics à 0.85 sur geometrie_mesures, unites_temps ; valleys idem
reasoning_specialist : pics à 0.85 sur fractions_decimaux, resolution_problemes ; valleys idem
struggling           : 0.42 sur tous les domaines (bas partout)
```

σ = 0.10 conservé. Léa = `calc_specialist`.

## Consequences

### Positives

- **Silhouette pique naturellement à k=4** (score 0.309 vs 0.282 à k=3, 0.243 à k=5).
- **Pureté archetype ↔ cluster** observée empiriquement : 88-100 % par archetype
  (`calc_specialist` 100 %, `geo_specialist` 100 %, `reasoning_specialist` 89 %,
  `struggling` 97 %).
- Le récit est direct : *« le système a découvert 4 profils pédagogiques sans connaître
  les vrais et les retrouve à 95-100 % »*.
- Aucune triche algorithmique : pas de tie-break, pas de manipulation du score.

### Compromis

- σ = 0.10 reste un **paramètre arbitraire** : trop bas → clustering trivial ; trop haut
  → archetypes flous. On a vérifié empiriquement que 0.10 donne 88-100 % de pureté ; à
  0.05 on monterait à 98+%, à 0.20 on perdrait des points.
- Si on ajoutait un **5ᵉ archetype** à magnitude similaire, le risque de re-fusion
  partielle réapparaîtrait — il faudrait des centroïdes encore plus orthogonaux.

### Limites assumées

- Les 4 archetypes sont **stylisés**. Un vrai dataset Mathia aurait des profils plus
  graduels, sans 4 modes nets. C'est le prix d'une démo *interprétable* — assumé.
- Le profil `struggling` reste discriminé par sa magnitude, pas par sa forme. C'est
  voulu : pédagogiquement, "faible partout" est une catégorie pertinente.
