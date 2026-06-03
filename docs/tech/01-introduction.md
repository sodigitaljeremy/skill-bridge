# 01 — Introduction et objectifs

## Pourquoi ce projet

**SkillBridge** est une démonstration technique de positionnement
**« Data & AI provider »** dans l'écosystème [Prometheus-X](https://prometheus-x.org/),
réalisée en vue d'une candidature « Développeur confirmé : data, IA et logiciel ».

Le projet matérialise une **tranche verticale** complète : depuis la trace d'apprentissage
brute jusqu'à la recommandation personnalisée, en s'intégrant aux briques réelles du
**DASES** (Data Space for Education & Skills).

## Objectifs démontrés

| Domaine de l'offre | Démontré dans ce repo |
| --- | --- |
| Intégration dataspace | LRC réel intégré (Lot 3) ; PDC à venir (Lot 4) |
| Data & AI provider | Profilage + clustering empirique + reco explicables (Lots 1–2) |
| Building block open-source | Service packagé, documenté, déployable en Docker |

## Critères de succès

1. Le fil rouge fonctionne **bout-en-bout** à partir d'un format brut hétérogène (CSV
   propriétaire « Mathia »), normalisé en xAPI par le LRC réel, profilé, segmenté,
   recommandé, exposé via API HTTP, et consommé par une vitrine.
2. L'algorithmique de clustering retrouve les **archétypes pédagogiques** latents avec
   lesquels le dataset a été généré, à une pureté ≥ 88 % par archetype — sans
   supervision (voir [ADR 002](adrs/002-archetypes-par-forme.md)).
3. Chaque recommandation porte une **explication décomposée** : compétence faible
   ciblée, écart de niveau, similarité sémantique, signal cluster.
4. La documentation reflète l'**état réel** du projet, limites assumées incluses
   (voir [explication](../user/explanation/pourquoi.md)).

## Parties prenantes

| Rôle | Attente principale |
| --- | --- |
| Évaluateur Prof en Poche | Voir un livrable concret au plus près de leur stack DASES |
| Léa (persona) | Reçoit des recommandations pédagogiquement pertinentes |
| Équipe data-science | Peut auditer profiling / clustering / reco depuis les ADRs |
| Équipe ops | Peut redéployer via Docker Compose / Coolify (Lot 5d) |

## Niveau d'ambition

**Niveau 1 garanti** : socle complet livrable. **Niveau 2 visé** : raffinements ciblés
(catalogue PDC réel, profil DASES si DASES propose les templates manquants, déploiement
Coolify).

Le découpage par **lots** et la méthode **BMAD** (cadrage avant code) sont détaillés
dans la [stratégie de solution](03-strategy.md).
