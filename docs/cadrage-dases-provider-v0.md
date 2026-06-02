# Cadrage — Projet intégrateur « DASES-Provider »

> **Nom de travail :** SkillBridge
> **Contexte :** démonstration technique ciblée pour la candidature « Développeur confirmé : data, IA et logiciel » chez Prof en Poche (Pau)
> **Version :** v0 — document de cadrage initial
> **Statut :** cadrage validé — fondation en cours
> **Équipe (trio) :** Jeremy (décideur / validation) · Claude (stratégie, architecture, sparring) · Claude Code (implémentation)
> **Méthode :** cadrage avant code (BMAD), docs as code, déploiement souverain

---

## 1. Intention

Ce projet est une **preuve de compétence** destinée à court-circuiter le filtre CV (Bac+5 et 36 mois d'expérience affichés comme « indispensables ») en démontrant, par un livrable concret et fidèle à leur écosystème, la capacité à tenir le poste.

Le poste couvre trois domaines : intégration des outils du dataspace dans les produits, déploiement de services d'IA (clustering, recommandation), et développement de briques open-source. Le projet vise à **toucher les trois en un seul fil rouge**, en se positionnant exactement dans le rôle que Prof en Poche joue déjà au sein de Prometheus-X : celui de **« Data & AI provider »** du Data Space for Education & Skills (DASES), notamment sur le use case DAPO-X.

## 2. Le domaine métier (rappel)

Les traces d'apprentissage sont éparpillées dans des formats incompatibles (xAPI, SCORM, IMS Caliper, cmi5, propriétaires) et cloisonnées par organisation. Prometheus-X construit un dataspace décentralisé et human-centric (sous Gaia-X, conforme RGPD/AI Act) où la donnée circule de façon souveraine et consentie. Finalités débloquées : portabilité des données de l'apprenant, personnalisation, analytics de compétences, entraînement d'IA sur données mutualisées.

Ce projet matérialise une tranche verticale de cette vision : de la trace brute jusqu'à la recommandation personnalisée.

## 3. Objectifs

### Objectifs de démonstration (mappés à l'offre)

| Domaine de l'offre | Ce que le projet démontre |
| --- | --- |
| Use case leader / intégration dataspace | Déploiement et connexion du PDC et du LRC ; simulation d'un PLRS |
| Data & AI provider | Service exposant un jeu de données via API + clustering + recommandation |
| Building block open-source | Service packagé, documenté, déployé comme brique réutilisable |

### Objectifs personnels

- Démontrer **Python** en première ligne (l'indispensable de l'offre) et amorcer la montée en compétences AI Engineer.
- Combler le gap **MongoDB** en déployant le PDC réel.
- Produire un livrable réutilisable comme actif d'agence (MindAgency) au-delà de cette candidature.

## 4. Scénario fil rouge

**Persona :** « Léa », élève utilisant une application de maths façon Mathia.

1. Léa réalise des exercices ; l'appli génère des **traces brutes** (exercice tenté, réussi/échoué, temps passé).
2. Les traces sont normalisées au format **xAPI** (profil DASES) par le **LRC**.
3. Elles sont déposées dans son **PLRS** (coffre de données personnel — simulé au niveau 1).
4. Léa **consent** à partager ses données (anonymisées) avec un service ; l'échange transite par le **PDC**.
5. Le **Service Data & IA** ingère ces traces, les **enrichit** avec des compétences du référentiel **ESCO/ROME**, **regroupe** les ressources par compétence (clustering) et **recommande** les prochaines ressources adaptées.
6. Les recommandations sont **renvoyées** et affichées.

## 5. Périmètre par niveaux d'ambition

> Le **niveau 1 est le livrable garanti**. On pousse vers le niveau 2 si le temps le permet. Le niveau 3 est hors scope POC (à évoquer en entretien comme « la suite »).

| Élément | Niveau 1 (socle) | Niveau 2 (visé) | Niveau 3 (hors scope) |
| --- | --- | --- | --- |
| LRC (conversion xAPI) | Déployé et utilisé en réel | idem | idem |
| Service Data & IA | Construit (enrichissement + reco + clustering) | idem + affiné | idem |
| PDC (connecteur) | Déployé et présenté, échange **simulé** | Échange **réel** entre 2 connecteurs, catalogue + contrat minimal | Catalogue + Contract + Consent complets |
| PLRS | Simulé (stockage simple) | Simulé enrichi | Intégration réelle (Cozy Cloud) |
| Front de démo | Minimal | Minimal soigné | — |

## 6. Architecture cible

Réutilisation maximale des briques réelles, construction de la pièce manquante.

- **Réutilisé (open-source Prometheus-X) :**
  - `dataspace-connector` (PDC) — TypeScript, MongoDB, Docker, licence MIT. Dépend de composants centraux (Catalogue, Contract, Consent) pour un échange complet.
  - `learning-records-converter` (LRC) — Python/FastAPI, Docker, licence GPL-3.0. Endpoints `/convert`, `/validate`.
- **Construit par nous — le Service Data & IA :**
  - Ingestion de traces xAPI → enrichissement compétences (ESCO/ROME) via embeddings → clustering → recommandation.
  - Exposition via API (FastAPI) compatible avec une logique de « data/AI provider ».
- **Flux :** Application éducative → LRC (xAPI) → PLRS → PDC (échange consenti) → Service Data & IA → recommandations.

## 7. Stack technique (fidèle à eux + indispensables de l'offre)

- **Service IA :** Python 3.12, FastAPI, `sentence-transformers` (embeddings, modèle multilingue local), `scikit-learn` (clustering), modèle sérialisé en `pickle`/`joblib`.
- **Briques réutilisées :** Node.js / TypeScript + MongoDB (PDC) ; Python / FastAPI (LRC).
- **Données & formats :** xAPI (profils DASES), référentiel ESCO/ROME.
- **Infra :** Docker / Docker Compose, déploiement Coolify sur VPS Hetzner (souverain).
- **Front de démo :** Streamlit (rapide, tout-Python, cohérent avec le syllabus AI Engineer) — *option : petit front Angular/Ionic en bonus pour coller à leur stack front, non prioritaire.*
- **Qualité :** tests (pytest), CI/CD, documentation versionnée + ADRs.

## 8. Sources de données

- **Traces d'apprentissage :** jeu de données xAPI **synthétique** généré (scénario maths primaire façon Mathia), couvrant des activités variées (exercices, réussites, échecs, temps).
- **Référentiel de compétences :** **ESCO** (référentiel européen, open data) et/ou **ROME** (France Travail) pour aligner le vocabulaire « skills » de Prometheus-X.
- **Catalogue de ressources :** petit corpus de ressources éducatives à recommander (titre, niveau, compétences associées).

## 9. Livrables

- Repo Git propre (monorepo ou multi-repo à trancher), README clair.
- Service Data & IA déployé avec API documentée (Swagger).
- PDC et LRC déployés (selon niveau atteint).
- Front de démo accessible en ligne.
- Documentation déployée façon AlpiMonitor : objectifs, architecture (C4), ADRs, guide de démarrage.
- Un court écrit « ce que ça démontre » utilisable en entretien.

## 10. Risques & points d'attention

| Risque | Impact | Mitigation |
| --- | --- | --- |
| Dépendances du PDC (Catalogue/Contract/Consent) | Échange réel complexe à monter | Échange simulé au niveau 1 ; minimal au niveau 2 |
| LRC « work in progress » (18 commits, pas de release) | Débogage possible | Tester tôt ; fallback : s'inspirer du format de sortie sans dépendre du service |
| Licence GPL-3.0 du LRC vs MIT du PDC | Contrainte si produit commercial | OK pour un POC ; à tracer dans un ADR si réutilisation produit |
| Gap data/ML personnel (Python data récent) | Courbe d'apprentissage | Rester sur de l'IA appliquée (embeddings + clustering), pas de deep learning lourd |
| Effet tunnel / scope creep | Retard | Niveau 1 livrable d'abord, jalons courts |

## 11. Découpage en lots (jalons)

- **Lot 0 — Spike de faisabilité.** ✅ *(fait)* PDC et LRC validés comme déployables.
- **Lot 1 — Données & enrichissement.** Générer le jeu xAPI synthétique ; intégrer ESCO/ROME ; enrichissement des traces par compétences.
- **Lot 2 — Service IA.** Embeddings + clustering + recommandation ; API FastAPI ; tests.
- **Lot 3 — Interopérabilité.** Déployer le LRC réel ; brancher la conversion en amont du service.
- **Lot 4 — Dataspace.** Déployer le PDC ; échange simulé (niveau 1) puis réel (niveau 2).
- **Lot 5 — Démo & doc.** Front de démo ; documentation déployée ; déploiement final Coolify/Hetzner.

## 12. Critères de réussite (Definition of Done)

- Le fil rouge fonctionne de bout en bout (au moins au niveau 1) et est déployé en ligne.
- L'API du Service Data & IA est documentée et testée.
- La documentation explique clairement le « pourquoi » métier et l'architecture.
- Le projet est présentable en 5 minutes en entretien, avec un lien live.

## 13. Décisions tranchées

- [x] **Nom définitif du projet :** SkillBridge (repo `skill-bridge`)
- [x] **Délai cible :** niveau 1 visé en ~2 semaines (sprint cadré, façon AlpiMonitor)
- [x] **Modèle d'embeddings :** `sentence-transformers` multilingue, exécution locale
- [x] **Référentiel de compétences :** ESCO (primaire) ; mapping ROME en secondaire, plus tard
- [x] **Front de démo :** Streamlit (seul, niveau 1) ; bonus Angular/Ionic non prioritaire
- [x] **Organisation du code :** repo unique pour notre code ; PDC et LRC intégrés via Docker (non copiés dans le repo)
- [x] **Niveau d'ambition :** niveau 1 garanti d'abord, niveau 2 visé en bonus

**Stack Python actée :** Python 3.12 · `uv` (gestion d'env et de deps) · `ruff` (lint/format) · `pytest` (tests).

---

*Document de cadrage v0 — à affiner en trio avant le démarrage du Lot 1.*
