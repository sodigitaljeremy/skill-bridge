# Runbook — Learning Records Converter (LRC)

Le LRC est consommé par SkillBridge comme **service externe** (HTTP). Il n'est *pas*
embarqué dans ce repo (différence de licence : MIT côté SkillBridge, GPL-3.0 côté LRC).

## SHA pinné

| Élément | Valeur |
| --- | --- |
| Repo | https://github.com/Prometheus-X-association/learning-records-converter |
| Branche | `main` |
| Commit testé | `163db132d01140994d4f3ef83a8c18c29972b611` (push 2025-08-14) |
| Licence | GPL-3.0 |
| Statut amont | Pas de release publiée ; dernière activité ≈ 10 mois — on **pinne le SHA** |

## Installation locale (une fois)

```bash
cd ~/Desktop
git clone https://github.com/Prometheus-X-association/learning-records-converter.git lrc
cd lrc
git checkout 163db132d01140994d4f3ef83a8c18c29972b611
cp .env.default .env
```

### Conflit port 80 → 8080

Sur cette VM, `apache2` occupe le port 80. Le `traefik` du LRC veut bind 80. On dévie via
`.env` :

```bash
sed -i 's/^APP_EXTERNAL_PORT=80$/APP_EXTERNAL_PORT=8080/' .env
```

## Cycle up / verify / down

```bash
# Démarrer (build au premier lancement, ~5 min ; ensuite ~3 s)
cd ~/Desktop/lrc
docker compose --profile dev up -d

# Vérifier que ça répond (le routage Traefik exige Host: lrc.localhost)
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  -H "Host: lrc.localhost" http://localhost:8080/docs
# attendu : HTTP 200

# Swagger interactif (depuis un navigateur, ajouter lrc.localhost à /etc/hosts d'abord
# OU utiliser un navigateur qui supporte override Host, ce qui est rare)

# Arrêter (laisse les images et le code en place)
docker compose --profile dev down
```

## URL de service pour SkillBridge

Avec la config par défaut ci-dessus :

```
LRC_URL=http://localhost:8080
```

À passer au CLI : `uv run python scripts/generate_dataset.py --via-lrc=http://localhost:8080 ...`.
Les adapters de SkillBridge envoient l'en-tête `Host: lrc.localhost` automatiquement.

## Endpoints utilisés

| Endpoint | Usage SkillBridge |
| --- | --- |
| `POST /convert_custom` | Conversion CSV brut + mapping YAML → JSONL xAPI (chemin nominal) |
| `POST /convert` | Non utilisé en pipeline (testé au spike : mappers natifs trop fragiles pour notre cas) |
| `POST /validate` | Non utilisé |
| `GET /docs` | Sanity check de disponibilité (test d'intégration) |

## Limites connues

- **Pas de release amont** ; le SHA peut bouger sans annonce — on pinne donc strictement.

- **Mappers natifs Matomo/SCORM rugueux** (object par défaut codé en dur côté SCORM,
  reformatage URL douteux côté Matomo). Notre chemin de prod utilise `/convert_custom`
  avec un mapping maison, pas ces mappers.

- **`meta.profile = null` assumé** : enquête réalisée le 2026-06-02 sur les templates
  des profils DASES `lms` et `assessment` (téléchargés à la demande par le LRC depuis
  les dépôts `gaia-x-dases/xapi-lms` et `gaia-x-dases/xapi-assessment`).

  | Profil | Templates dispos | Verbes attendus |
  | --- | --- | --- |
  | `assessment` | `started`, `terminated`, `initialized`, `completed`, `answered-question` | `start`, `terminated`, `initialized`, `completed`, `answered` |
  | `lms` | `accessed-page`, `accessed-file`, `registered-course`, `uploaded-file`, ... | `accessed`, `registered`, `uploaded`, `downloaded`, ... |

  Nos traces utilisent les verbes ADL standard `passed` / `failed` / `completed` sur des
  objets de type `performance` / `lesson` / `assessment`. **Aucune combinaison ne matche
  exactement un template DASES sans déformer la sémantique** :
  - nos `passed`/`failed` sur exercices n'ont aucun template équivalent côté DASES ;
  - le seul match mécanique possible (lesson `completed` → `assessment.completed`)
    exigerait de retyper nos leçons comme `assessment`, ce qui serait factuellement faux.

  → Décision : on **n'injecte pas** de `profile:` dans le mapping YAML ; `meta.profile`
  reste `null` dans la sortie LRC. C'est un état honnête, à reprendre côté DASES quand
  le profil `lms` proposera des templates "exercise-passed" / "exercise-failed".
