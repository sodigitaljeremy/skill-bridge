# Pourquoi SkillBridge

## Le problème de fond

Les **traces d'apprentissage** sont produites en masse par les applications éducatives :
quel exercice a été tenté, à quelle heure, avec quel score, sur combien de temps. Mais
elles sont aujourd'hui :

1. **Cloisonnées par organisation** : chaque éditeur garde ses données.
2. **Éparpillées par format** : xAPI, SCORM, IMS Caliper, cmi5, sans compter les
   formats propriétaires.
3. **Peu exploitées** : à l'échelle d'un seul éditeur, on a rarement assez de signal
   pour une recommandation personnalisée fine, ou pour un analytics population.

C'est exactement le problème qu'attaque Prometheus-X avec le **DASES** : un dataspace
décentralisé qui permet la **circulation souveraine et consentie** des traces, tout
en garantissant la conformité RGPD / AI Act et l'interopérabilité sémantique.

## Le rôle de SkillBridge

Dans cette architecture, un **Data & AI provider** est un service qui :

- **consomme** des traces (potentiellement multi-source) via le PDC ;
- **produit** une valeur dérivée — profils, segmentations, recommandations,
  modèles entraînés ;
- **expose** cette valeur via une API ré-consommable par les éditeurs ou apprenants.

SkillBridge est une démonstration **complète et de bout en bout** de ce rôle.

## Le scénario fil rouge

La persona **Léa**, élève de CM1, utilise une application de mathématiques. Le scénario
suit la trace de Léa depuis l'événement brut (un clic, un exercice tenté) jusqu'à la
recommandation pédagogique reçue. Toutes les étapes sont visibles dans la vitrine :

1. **Émission** : un CSV propriétaire "Mathia".
2. **Normalisation** : par le LRC réel (Prometheus-X), en statements xAPI.
3. **Enrichissement** : par les compétences de notre référentiel maison numératie,
   joinables vers ESCO ([ADR 001](../../tech/adrs/001-referentiel-maison-et-mapping-esco.md)).
4. **Profilage** : score moyen + taux de succès par domaine de compétence, observé
   uniquement depuis les traces.
5. **Segmentation** : KMeans + silhouette empirique trouve 4 profils pédagogiques sans
   connaître les archetypes générateurs ([ADR 002](../../tech/adrs/002-archetypes-par-forme.md),
   [ADR 003](../../tech/adrs/003-k-par-silhouette-empirique.md)).
6. **Recommandation** : détection des compétences faibles, filtrage par grade et
   maîtrise ([ADR 007](../../tech/adrs/007-mastered-vs-attempted.md)), scoring transparent
   avec explication.
7. **Exposition** : API HTTP avec OpenAPI 3 + vitrine Streamlit consommatrice.

## Pourquoi ces choix techniques

Les décisions structurantes sont tracées en ADRs lisibles
([liste complète](../../tech/adrs/index.md)). Lecture rapide recommandée :

- **[ADR 002](../../tech/adrs/002-archetypes-par-forme.md)** explique pourquoi les
  archetypes ont été redesignés par forme — c'est le pivot qui rend le clustering
  démontrable.
- **[ADR 005](../../tech/adrs/005-profil-dases-null.md)** documente une **limite
  assumée** : la détection de profil DASES ne match pas nos verbes scolaires. Pourquoi
  c'est honnête de l'afficher.
- **[ADR 007](../../tech/adrs/007-mastered-vs-attempted.md)** raconte comment une
  correction de fond (vs un patch) a évité d'introduire un défaut de produit (Léa qui
  ne recevait plus de recos).

## Pourquoi cette doc

Cette documentation **ne sur-vend pas** la démo. Les limites sont documentées au même
titre que les forces : profil DASES `null`, LRC inactif côté amont, 95 % du dataset en
xapi-direct (seul un échantillon transite par le LRC), projection PCA qui n'explique
que ~57 % de la variance.

Un projet honnête se reconnaît à ce qu'il documente **ce qu'il ne fait pas (encore)**
au même titre que ce qu'il fait.
