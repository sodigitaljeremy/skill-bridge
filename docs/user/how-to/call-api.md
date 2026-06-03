# Appeler l'API depuis ton code

L'API SkillBridge est en **lecture seule** et publie une spec OpenAPI 3. Tu peux
l'appeler depuis n'importe quel client HTTP — voici les recettes courantes.

## URL de base

- **En ligne (prod)** : `https://api.skillbridge-data.fr` — Swagger interactif sur
  [`/docs`](https://api.skillbridge-data.fr/docs).
- **Local (dev)** : `http://localhost:8000` une fois `make api` (ou `make demo`)
  lancé.

Les exemples ci-dessous utilisent `http://localhost:8000` ; remplace simplement par
`https://api.skillbridge-data.fr` pour viser la prod.

## curl

```bash
# Santé
curl -s http://localhost:8000/health | jq

# Liste des apprenants
curl -s http://localhost:8000/learners | jq '.[0:3]'

# Profil de Léa (UUID stable, déterministe via uuid5)
LEA=dbe21d14-856a-5279-8bee-af09ed230fb2
curl -s http://localhost:8000/profile/$LEA | jq

# Clusters
curl -s http://localhost:8000/clusters | jq '{k, silhouette}'

# Recommandations
curl -s "http://localhost:8000/recommend/$LEA?n=3" | jq '.[] | {resource_id, score, explanation}'
```

## Python (httpx)

```python
import httpx

BASE = "http://localhost:8000"

with httpx.Client(base_url=BASE, timeout=10.0) as client:
    learners = client.get("/learners").raise_for_status().json()
    lea_id = next(l["learner_id"] for l in learners if l["display_name"] == "Léa Martin")

    profile = client.get(f"/profile/{lea_id}").json()
    print("Mean score géo :", profile["mean_score_per_domain"]["geometrie_mesures"])

    recos = client.get(f"/recommend/{lea_id}", params={"n": 5}).json()
    for r in recos:
        print(f"{r['score']:.2f}  {r['title']}  →  {r['explanation']}")
```

## OpenAPI / spec

- Swagger UI interactif : http://localhost:8000/docs
- ReDoc : http://localhost:8000/redoc
- JSON brut : http://localhost:8000/openapi.json

Pour générer un client typé (TypeScript, Java, Go...) à partir de la spec :

```bash
curl http://localhost:8000/openapi.json > openapi.json
npx @openapitools/openapi-generator-cli generate -i openapi.json -g typescript-fetch -o client/
```

## Notes

- Tous les endpoints sont **idempotents** et **lecture seule** (`GET`).
- L'instance prod (`api.skillbridge-data.fr`) est **publique sans auth** — c'est une
  démo. Pour un usage plus protégé, il suffit d'ajouter une basic auth Traefik côté
  Coolify (cf. [Déployer sur Coolify](deploy-coolify.md)).
- Les recos sont **préchargées au boot** (top-10 par apprenant). Passer `n=3` slice les
  3 premières du cache — la résolution est instantanée.
- Référence complète des routes et schémas : [Reference — API HTTP](../reference/api.md).
