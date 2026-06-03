# ADR 004 — LRC traité comme service externe (runbook), pas comme submodule

## Status

**Acté** — Lot 3 (2026-06-02).

## Context

Le **Learning Records Converter** (LRC) — projet `Prometheus-X-association/learning-records-converter` —
est un service nécessaire à la démonstration d'**interopérabilité** : normaliser un
format brut (CSV "Mathia") en statements xAPI conformes aux profils DASES.

Trois options pour l'intégrer :

1. **Submodule git** : `git submodule add` dans `external/lrc`. Reproductibilité forte
   (SHA capturé dans `.gitmodules`), mais : pollution licence (LRC = GPL-3.0,
   SkillBridge = MIT) et couplage de cycle de vie.
2. **Service externe HTTP** : LRC tourne dans son propre Docker Compose, SkillBridge le
   consomme via un client HTTP. SHA pinné dans un runbook documenté.
3. **Vendoring** : copier le code LRC dans notre repo. **Refusé d'emblée** — pollue
   massivement la licence et complique la maintenance.

État amont du LRC : pas de release publiée, dernier commit observé `163db132` du
**2025-08-14** (~10 mois d'inactivité à la date du spike).

## Decision

**Option 2** : LRC en service externe HTTP. SHA pinné à `163db132d01140994d4f3ef83a8c18c29972b611`
dans `docs/lrc_runbook.md`. Le runbook documente le clone, le checkout du SHA, le
contournement du conflit port 80 (apache2 sur la VM cible → `APP_EXTERNAL_PORT=8080`),
et le cycle up / curl / down.

Communication via `LrcHttpConverter` (httpx multipart vers `/convert_custom`). Stub
déterministe `StubLrcConverter` pour les tests unitaires.

## Consequences

### Positives

- **Pas de pollution licence** : le repo reste MIT propre. La doc rappelle
  explicitement que le LRC consommé est GPL-3.0.
- **Architecture claire** : "service-to-service" est l'archi cible (Coolify + Traefik),
  on la pratique dès le local.
- **Tests rapides** : les tests unitaires utilisent `StubLrcConverter` (pas de réseau,
  pas de Docker), les tests `integration` sont marqués et **skip** si la variable
  `LRC_URL` n'est pas posée.
- **Reproductibilité du build CI** : ne dépend pas du LRC pour passer.

### Compromis

- **Étape manuelle à l'install** : l'opérateur doit cloner le LRC séparément et faire
  un `git checkout 163db132`. Documenté pas-à-pas dans le runbook.
- **Sans CI cross-repo**, si le LRC bouge, on ne le sait pas automatiquement. Atténué
  par l'inactivité observée du projet amont (peu de risque de drift).

### Limites assumées

- Si l'évaluateur veut une démo en un clic, il faut un `docker-compose.yml` haut niveau
  qui démarre les 2 services. À ajouter au **Lot 5d** (déploiement).
- Le SHA pinné peut diverger un jour. On documente la procédure de mise à jour : tester
  le nouveau SHA, ajuster le mapping YAML si l'API LRC change, mettre à jour le runbook.
