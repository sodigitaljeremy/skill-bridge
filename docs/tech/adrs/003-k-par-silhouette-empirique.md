# ADR 003 — `k` choisi par silhouette pure, sans tie-break heuristique

## Status

**Acté** — Lot 2 (2026-06-02).

## Context

KMeans exige de fixer `k` (nombre de clusters) avant de fitter. Les approches courantes :

- **k codé en dur** par connaissance métier (ex : "on sait qu'il y a 4 archetypes").
- **Elbow method** (inflexion de l'inertie).
- **Silhouette** (cohésion intra-cluster vs séparation inter-cluster, score ∈ [-1, 1]).
- **Gap statistic**, **information criteria**, etc.

Au design, on connaît 4 archetypes générés. Si on codait `k=4` en dur, on tricherait :
le test "le système retrouve les archetypes" perdrait sa valeur d'inférence.

Au premier essai d'archetypes (cf. [ADR 002](002-archetypes-par-forme.md)), la silhouette
piquait à k=2, qui n'est pas la valeur souhaitée. La tentation était d'ajouter une
**heuristique de tie-break** : "si silhouette[k+1] ≥ 95 % de silhouette[best], préférer
k+1".

## Decision

**Pas de tie-break heuristique.** `k` est l'**argmax pur** de silhouette sur la bande
`k ∈ [k_min, k_max]` (défaut `[2, 8]`).

```python
for k in range(k_min, k_max + 1):
    score[k] = silhouette_score(X_scaled, KMeans(k).fit(X_scaled).labels_)
best_k = argmax(score)  # ← rien d'autre
```

Si la silhouette pure ne donne pas le `k` attendu, le problème est dans le **dataset**
(pas assez de séparation par forme), pas dans l'algo. C'est ce qui a conduit à
[ADR 002](002-archetypes-par-forme.md).

## Consequences

### Positives

- **Honnêteté algorithmique** : pas de "magie" cachée dans la sélection de k. Un
  évaluateur peut auditer la silhouette retournée par `/clusters` et vérifier que
  `k == argmax(silhouette_by_k)`.
- **Reproductibilité** : seed 42 + bande [2, 8] fixée → mêmes résultats partout (CLI,
  API, tests).
- **Pédagogiquement défendable** : si on travaille un jour avec des datasets réels, on
  saura que la valeur de `k` reflète la structure des données, pas un biais d'analyste.

### Compromis

- **Sensibilité au design du dataset**. C'est l'apport principal d'[ADR 002](002-archetypes-par-forme.md) :
  pour que la silhouette pure soit informative, le dataset doit avoir des centroïdes
  d'archetypes suffisamment orthogonaux.
- En production réelle (vrai dataset, pas synthétique), la silhouette peut être faible
  partout — le score retenu (0.309 ici) est correct mais pas spectaculaire en valeur
  absolue. C'est une métrique relative, lue ensemble avec la pureté terrain.

### Limites assumées

- KMeans euclidien sur features standardisées privilégie des clusters **sphériques de
  tailles comparables**. Si la vraie structure était hiérarchique ou non convexe, on
  changerait d'algorithme (DBSCAN, Gaussian Mixture, hiérarchique) — c'est hors scope au
  niveau 1.
- Le test correspondant accepte `k ∈ [3, 5]` (pas strictement = 4) pour absorber la
  variance d'initialisation entre seeds. Documenté dans
  `tests/unit/test_clustering.py`.
