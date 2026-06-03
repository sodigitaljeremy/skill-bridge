# Déployer SkillBridge sur Coolify (VPS Hetzner)

Guide pas-à-pas pour mettre en ligne les trois services SkillBridge sur un VPS Hetzner
géré par [Coolify](https://coolify.io/) :

| Service | Domaine cible | Image | Rôle |
| --- | --- | --- | --- |
| **API** | `api.skillbridge-data.fr` | `Dockerfile.api` | Provider FastAPI |
| **Front** | `app.skillbridge-data.fr` | `Dockerfile.front` | Vitrine Streamlit |
| **Doc** | `docs.skillbridge-data.fr` | `Dockerfile.docs` | Doc MkDocs servie par nginx |

Le **LRC n'est pas déployé en ligne** : l'interopérabilité est démontrée par une
fixture committée (`data/seed/interop_example/`) que la vitrine lit en prod.

## Pré-requis côté Coolify

- Une instance Coolify ≥ 4 sur ton VPS Hetzner (Coolify gère Traefik et Let's Encrypt
  automatiquement).
- Le domaine `skillbridge-data.fr` configuré chez ton registrar avec un enregistrement
  pointant vers l'IP publique du VPS (un `A` sur l'apex + un `CNAME *.skillbridge-data.fr`
  vers l'apex, ou trois `A` séparés — au choix).
- Un projet créé dans Coolify pour SkillBridge (ce sera le conteneur des 3 apps).

## Pré-requis côté repo

Le repo peut être **public** ou **privé** — les artefacts (Dockerfiles, mapping) sont
identiques. La seule différence est la méthode de connexion :

=== "Repo public"

    Connecte le repo via l'URL HTTPS directement dans Coolify (sans clé). Plus simple
    pour une démo ouverte.

=== "Repo privé"

    1. Génère une **deploy key SSH** Coolify : *Sources → New SSH key*.
    2. Ajoute la clé publique dans GitHub : *Repo → Settings → Deploy keys → Add key*
       (read only — la deploy key n'a accès qu'à ce repo).
    3. Dans Coolify : *Sources → New private repository* → URL SSH
       (`git@github.com:sodigitaljeremy/skill-bridge.git`) + la clé fraîchement créée.

## Étape 1 — Créer l'app **API**

1. *Project → New Resource → Application* (Docker build).
2. Source : le repo SkillBridge.
3. Branch : `main`.
4. Dockerfile : `Dockerfile.api`.
5. **Port** exposé : `8000`.
6. **Healthcheck** :
    - URL : `/health`
    - Start period : **30 s** (le temps de l'init lifespan + précompute des 100 recos)
    - Interval : 10 s
7. **Resources** : pas de minimum critique, mais ~1.5 GB de RAM recommandés (torch +
   modèle ST chargés en mémoire + 5800 traces).
8. **Domaine** : `api.skillbridge-data.fr` (Coolify gère le TLS Let's Encrypt
   automatiquement).
9. Pas de variables d'environnement à poser — toutes les valeurs sont calées par défaut
   et le dataset est *baked in* à l'image.

!!! warning "Premier build"
    Le premier `docker build` côté Coolify prend **5-10 minutes** : install des deps
    (torch CPU ≈ 750 MB), téléchargement du modèle sentence-transformers (≈ 470 MB), et
    `make dataset`. Les builds ultérieurs réutilisent les couches.

## Étape 2 — Créer l'app **Front**

1. *Project → New Resource → Application*.
2. Source : même repo.
3. Dockerfile : `Dockerfile.front`.
4. **Port** : `8501`.
5. **Healthcheck** : URL `/_stcore/health`, start period 15 s.
6. **Variable d'environnement** :
   ```
   SKILLBRIDGE_API_URL=http://skillbridge-api:8000
   ```
   (Coolify met les conteneurs sur un même réseau Docker ; on appelle l'API par son
   nom de service interne, **pas** par le domaine public — évite un aller-retour TLS.)
7. **Domaine** : `app.skillbridge-data.fr`.

## Étape 3 — Créer l'app **Doc**

1. *Project → New Resource → Application*.
2. Source : même repo.
3. Dockerfile : `Dockerfile.docs`.
4. **Port** : `80`.
5. **Healthcheck** : URL `/healthz`, interval 30 s.
6. **Pas de variable d'environnement**.
7. **Domaine** : `docs.skillbridge-data.fr`.

## Étape 4 — Vérification

```bash
curl -sf https://api.skillbridge-data.fr/health | jq
# attendu : {"status":"ok","preloaded":true,"n_learners":100,...}

curl -sI https://app.skillbridge-data.fr/ | head -1
# attendu : HTTP/2 200

curl -sI https://docs.skillbridge-data.fr/ | head -1
# attendu : HTTP/2 200
```

Ouvre `https://app.skillbridge-data.fr/` dans un navigateur et vérifie les 3 écrans :

- **Vue d'ensemble** : encart interopérabilité chargé depuis la fixture
  (Léa Martin, EX011, statement xAPI).
- **Apprenant** : Léa par défaut, recos visibles, profil cohérent.
- **Clustering** : silhouette par k, heatmap, projection PCA, et **table de pureté
  cluster ↔ archétype** alimentée par `data/seed/learners_fixture.jsonl`.

## Surveillance et journaux

- Coolify expose les logs en temps réel par service (UI ou `coolify logs <app>`).
- L'API logue son boot via `uvicorn` ; tu dois voir une ligne `Started server process`
  après ~5 s, puis l'app reste prête.
- En cas de Crash de l'API : le précompute des recos ou le chargement du modèle ST sont
  les deux suspects naturels. Vérifie la RAM disponible.

## Redéploiement

- Push sur `main` → Coolify déclenche un rebuild automatique (si webhook activé).
- Sinon, *Application → Deploy* dans l'UI.
- Pour les **fixtures** (interop_example, learners_fixture) : un push standard suffit
  — elles sont dans l'image.
- Pour le **modèle ST** : pas de rebuild forcé sauf si tu changes
  `Dockerfile.api` ou son stage `st-bundle`.

## Limites assumées

- **Pas de scaling horizontal** : la précomputation au `lifespan` fait que chaque
  instance a son propre cache mémoire. Pour > 1 réplique, il faudrait externaliser le
  cache (Redis) ou passer à un mode stateless — hors scope niveau 1.
- **Pas d'auth** : l'API et la vitrine sont publiques. Si tu veux limiter l'accès
  pendant la candidature, ajoute une **basic auth Traefik** dans Coolify (UI → Labels).
- **Pas de monitoring externe** : pas de Sentry, pas de Prometheus exporter. Les logs
  Coolify suffisent à ce stade.
